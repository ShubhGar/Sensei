"""
Teams API routes
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import logging
import time
import asyncio

from app.models.schemas import TeamsSummary, SendTeamsMessageRequest, SendTeamsMessageResponse, TodoItemResponse
from app.integrations.teams_integration import TeamsIntegration
from app.services.ai_service import AIService
from app.database import get_db, TodoItem
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter()
teams_integration = TeamsIntegration()
ai_service = AIService()

# Simple in-memory cache for Teams requests (TTL: 60 seconds - increased for better performance)
_teams_cache = {}
_cache_ttl = 60  # seconds


@router.get("/messages", response_model=TeamsSummary)
async def get_messages(
    max_results: int = Query(50, ge=1, le=100),
    chat_type: str = Query("chats", description="Type: 'chats' or 'channels'"),
    team_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    analyze_mentions: bool = Query(False, description="Analyze @mentions"),
    analyze_activity: bool = Query(False, description="Analyze channel activity"),
    force_refresh: bool = Query(False, description="Force refresh and reset permission cache")
):
    """Get Teams messages with AI analysis"""
    try:
        # If force_refresh is True, reset permission cache and bypass cache
        if force_refresh:
            logger.info("[Teams] Force refresh requested - resetting permission cache and bypassing cache")
            teams_integration.reset_permission_cache()
            # Clear cache for this request
            cache_key = f"teams_{chat_type}_{max_results}_{team_id}_{channel_id}_{analyze_mentions}_{analyze_activity}"
            if cache_key in _teams_cache:
                del _teams_cache[cache_key]
        
        # Check cache first (cache works for all requests except when force_refresh is True)
        cache_key = f"teams_{chat_type}_{max_results}_{team_id}_{channel_id}_{analyze_mentions}_{analyze_activity}"
        if not force_refresh:
            cached = _teams_cache.get(cache_key)
            if cached and (time.time() - cached["timestamp"]) < _cache_ttl:
                logger.info(f"[Teams] Returning cached messages data (age: {time.time() - cached['timestamp']:.1f}s)")
                return TeamsSummary(**cached["data"])
        
        logger.info(f"[Teams] Getting messages - chat_type: {chat_type}, max_results: {max_results}, team_id: {team_id}, channel_id: {channel_id}, force_refresh: {force_refresh}")
        
        result = None
        if chat_type == "chats":
            result = await teams_integration.get_chats(max_results, force_refresh=force_refresh)
        elif chat_type == "channels":
            if not team_id or not channel_id:
                # If team_id/channel_id not provided, use dummy data for a default channel
                logger.info(f"[Teams] Missing team_id/channel_id for channels - using dummy data with default team/channel")
                from app.integrations.dummy_data import generate_dummy_channel_messages
                default_team_id = "dummy-team-engineering"
                default_channel_id = f"{default_team_id}-channel-general"
                messages_list = generate_dummy_channel_messages(default_team_id, default_channel_id, max_results)
                result = {
                    "messages": messages_list,
                    "error": None,
                    "error_type": None,
                    "is_dummy_data": True
                }
            else:
                # get_channel_messages still returns a list, so wrap it
                messages_list = await teams_integration.get_channel_messages(team_id, channel_id, max_results)
                # Check if we got dummy data (indicated by non-empty list when API would have failed)
                is_dummy = len(messages_list) > 0  # If we have messages, likely dummy data was used
                result = {
                    "messages": messages_list,
                    "error": None,
                    "error_type": None,
                    "is_dummy_data": is_dummy if len(messages_list) > 0 else False
                }
        else:
            logger.warning(f"[Teams] Invalid chat_type: {chat_type}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid chat_type '{chat_type}'. Must be 'chats' or 'channels'"
            )
        
        # Extract messages and error info from result
        messages = result.get("messages", [])
        error = result.get("error")
        error_type = result.get("error_type")
        is_dummy_data = result.get("is_dummy_data", False)
        
        # Always enhance messages with priority scoring for sorting
        # Process in parallel with timeout to avoid blocking
        
        async def score_message_priority_with_timeout(message, timeout=2.0):
            """Score Teams message priority with timeout"""
            content = message.get("content", "")
            sender = message.get("sender", "")
            sent_at = message.get("sent_at")
            
            try:
                priority = await asyncio.wait_for(
                    ai_service.score_teams_message_priority(content, sender, sent_at),
                    timeout=timeout
                )
                message["priority_score"] = priority
                # Set default urgency and criticality if not provided
                if "urgency_score" not in priority:
                    priority["urgency_score"] = priority.get("priority_score", 50)
                if "criticality_score" not in priority:
                    priority["criticality_score"] = priority.get("priority_score", 50)
            except asyncio.TimeoutError:
                logger.warning(f"[Teams] Priority scoring timeout for message {message.get('message_id')}")
                message["priority_score"] = {
                    "priority_score": 50,
                    "priority_level": "medium",
                    "urgency_score": 50,
                    "criticality_score": 50,
                    "waiting_for_us": False,
                    "blocked_on_us": False,
                    "factors": []
                }
            except Exception as e:
                logger.warning(f"[Teams] Error scoring priority for message {message.get('message_id')}: {e}")
                message["priority_score"] = {
                    "priority_score": 50,
                    "priority_level": "medium",
                    "urgency_score": 50,
                    "criticality_score": 50,
                    "waiting_for_us": False,
                    "blocked_on_us": False,
                    "factors": []
                }
        
        async def check_needs_jira_with_timeout(message, timeout=2.0):
            """Check if Teams message needs JIRA ticket with timeout"""
            try:
                message_content = message.get("content", "") or ""
                needs_jira = await asyncio.wait_for(
                    ai_service.check_needs_jira("teams", {
                        "sender": message.get("sender", ""),
                        "content": message_content[:2000],  # Limit to avoid token issues
                        "sent_at": message.get("sent_at")
                    }),
                    timeout=timeout
                )
                message["needs_jira"] = needs_jira
                logger.info(f"[Teams] JIRA check for message {message.get('message_id', 'unknown')[:20]}... - needs_jira: {needs_jira}")
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"[Teams] Error checking if message needs JIRA {message.get('message_id')}: {e}")
                # Fallback: do a quick keyword check (but ALWAYS exclude leave requests)
                message_content = message.get("content", "").lower()
                
                # First check for leave request keywords - ALWAYS exclude these
                leave_keywords = ['leave request', 'leave application', 'vacation', 'time off', 'holiday', 
                                'sick leave', 'personal leave', 'annual leave', 'casual leave',
                                'applying for leave', 'requesting leave', 'need leave', 'taking leave',
                                'leave approval', 'leave balance', 'leave days']
                if any(leave_keyword in message_content for leave_keyword in leave_keywords):
                    message["needs_jira"] = False
                    logger.info(f"[Teams] Fallback JIRA check - excluded (leave request) for message {message.get('message_id', 'unknown')[:20]}...")
                else:
                    # Not a leave request, check for bug/task keywords
                    fallback_keywords = ['bug', 'issue', 'problem', 'observed', 'seeing', 'multiple', 'fix', 'defect', 'verification']
                    message["needs_jira"] = any(keyword in message_content for keyword in fallback_keywords)
                    logger.info(f"[Teams] Fallback JIRA check for message {message.get('message_id', 'unknown')[:20]}... - needs_jira: {message['needs_jira']}")
        
        # Process messages in parallel batches (limit to 10 for better coverage)
        # Check JIRA needs for more messages (up to 10) to catch important issues
        messages_to_score = messages[:10]  # Increased from 5 to 10
        if messages_to_score:
            await asyncio.gather(*[score_message_priority_with_timeout(message, timeout=1.5) for message in messages_to_score], return_exceptions=True)
            # Check if messages need JIRA tickets (with longer timeout for better accuracy)
            await asyncio.gather(*[check_needs_jira_with_timeout(message, timeout=2.0) for message in messages_to_score], return_exceptions=True)
        
        # For remaining messages, set default priority scores and needs_jira flag
        for message in messages[10:]:
            if "priority_score" not in message:
                message["priority_score"] = {
                    "priority_score": 50,
                    "priority_level": "medium",
                    "urgency_score": 50,
                    "criticality_score": 50,
                    "waiting_for_us": False,
                    "blocked_on_us": False,
                    "factors": []
                }
            if "needs_jira" not in message:
                message["needs_jira"] = False
        
        # If dummy data is being used, log it
        if is_dummy_data:
            logger.info("[Teams] Using dummy data as fallback (no real data available)")
        
        # If there's an error and no dummy data, return it in the summary
        if error and not is_dummy_data:
            logger.info(f"[Teams] Error or empty result - error_type: {error_type}, error: {error}")
            return TeamsSummary(
                total_messages=0,
                unread=0,
                urgent=0,
                teams_summary=error,
                messages=[],
                error=error,
                error_type=error_type
            )
        
        # If no messages but no error and no dummy data, it's just empty
        if not messages and not is_dummy_data:
            logger.info("[Teams] No messages found - returning empty summary")
            return TeamsSummary(
                total_messages=0,
                unread=0,
                urgent=0,
                teams_summary="No Teams messages found.",
                messages=[],
                error=None,
                error_type="empty"
            )
        
        # Analyze messages if we have them
        summary = await teams_integration.analyze_messages(messages, ai_service)
        summary["error"] = None
        summary["error_type"] = None
        
        # Add mention analysis if requested
        if analyze_mentions and messages:
            try:
                from app.api.auth import get_microsoft_token
                # Try to get current user email for mention analysis
                user_email = None
                try:
                    import httpx
                    token = await get_microsoft_token()
                    if token:
                        async with httpx.AsyncClient() as client:
                            user_response = await client.get(
                                "https://graph.microsoft.com/v1.0/me",
                                headers={"Authorization": f"Bearer {token}"},
                                timeout=5.0
                            )
                            if user_response.status_code == 200:
                                user_data = user_response.json()
                                user_email = user_data.get("mail") or user_data.get("userPrincipalName")
                except Exception:
                    pass
                
                mention_analysis = await ai_service.analyze_mentions(messages, user_email)
                summary["mention_analysis"] = mention_analysis
                
                # Mark messages that mention the user for easier frontend sorting
                mentioned_message_ids = set()
                for mention in mention_analysis.get("unanswered_mentions", []):
                    mentioned_message_ids.add(mention.get("message_id"))
                for mention in mention_analysis.get("requires_response", []):
                    mentioned_message_ids.add(mention.get("message_id"))
                
                # Add is_mentioned flag to messages
                for message in messages:
                    if message.get("message_id") in mentioned_message_ids:
                        message["is_mentioned"] = True
                    else:
                        # Also check content directly for mentions
                        content = (message.get("content", "") or "").lower()
                        if "@shubham" in content or "shubham garg" in content or "shubham.garg" in content:
                            message["is_mentioned"] = True
                        else:
                            message["is_mentioned"] = False
            except Exception as e:
                logger.warning(f"[Teams] Error analyzing mentions: {e}")
        
        # Add channel activity analysis if requested
        if analyze_activity and chat_type == "channels" and messages:
            try:
                channel_name = f"Channel {channel_id}"
                activity_analysis = await ai_service.analyze_channel_activity(messages, channel_name)
                summary["channel_activity"] = activity_analysis
            except Exception as e:
                logger.warning(f"[Teams] Error analyzing channel activity: {e}")
        
        # Cache the result (including priority scores for faster subsequent loads)
        if not force_refresh:
            _teams_cache[cache_key] = {
                "data": summary,
                "timestamp": time.time()
            }
            # Clean old cache entries (keep only last 10)
            if len(_teams_cache) > 10:
                oldest_key = min(_teams_cache.keys(), key=lambda k: _teams_cache[k]["timestamp"])
                del _teams_cache[oldest_key]
        
        logger.info(f"[Teams] Successfully retrieved {len(messages)} messages")
        return TeamsSummary(**summary)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Teams] Error fetching messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching Teams messages: {str(e)}")


@router.get("/joined")
async def get_joined_teams(
    max_results: int = Query(100, ge=1, le=500)
):
    """Get Teams the user is a member of"""
    try:
        logger.info(f"[Teams] Getting joined teams - max_results: {max_results}")
        
        teams = await teams_integration.get_joined_teams(max_results)
        
        logger.info(f"[Teams] Successfully retrieved {len(teams)} teams")
        return {"teams": teams, "total": len(teams)}
    except Exception as e:
        logger.error(f"[Teams] Error fetching joined teams: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching joined teams: {str(e)}")


@router.get("/{team_id}/channels")
async def get_team_channels(
    team_id: str,
    max_results: int = Query(100, ge=1, le=500)
):
    """Get channels in a Team"""
    try:
        logger.info(f"[Teams] Getting channels for team {team_id} - max_results: {max_results}")
        
        channels = await teams_integration.get_team_channels(team_id, max_results)
        
        # If no channels found, return dummy channels
        if not channels or len(channels) == 0:
            logger.info(f"[Teams] No channels found for team {team_id}, using dummy channels data")
            from app.integrations.dummy_data import generate_dummy_team_channels
            channels = generate_dummy_team_channels(team_id, max_results)
        
        logger.info(f"[Teams] Successfully retrieved {len(channels)} channels")
        return {"channels": channels, "team_id": team_id, "total": len(channels)}
    except Exception as e:
        logger.error(f"[Teams] Error fetching team channels: {e}", exc_info=True)
        # On error, return dummy channels as fallback
        logger.info(f"[Teams] Error occurred, using dummy channels data as fallback for team {team_id}")
        from app.integrations.dummy_data import generate_dummy_team_channels
        channels = generate_dummy_team_channels(team_id, max_results)
        return {"channels": channels, "team_id": team_id, "total": len(channels)}


@router.post("/authenticate")
async def authenticate_teams(auth_code: Optional[str] = None):
    """Authenticate with Microsoft Teams"""
    try:
        success = await teams_integration.authenticate(auth_code)
        
        if success:
            return {"status": "authenticated", "provider": "teams"}
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@router.post("/send-message", response_model=SendTeamsMessageResponse)
async def send_teams_message(request: SendTeamsMessageRequest):
    """Send a Teams message (chat or channel) based on AI-generated response"""
    try:
        # Validate request - must have either chat_id OR (team_id and channel_id)
        if not request.chat_id and not (request.team_id and request.channel_id):
            raise HTTPException(
                status_code=400,
                detail="Either 'chat_id' (for chat messages) or both 'team_id' and 'channel_id' (for channel messages) must be provided"
            )
        
        if request.chat_id:
            # Send to chat
            logger.info(f"[Teams] Sending message to chat {request.chat_id}")
            result = await teams_integration.send_chat_message(
                chat_id=request.chat_id,
                content=request.content,
                content_type=request.content_type
            )
        else:
            # Send to channel
            logger.info(f"[Teams] Sending message to channel {request.channel_id} in team {request.team_id}")
            result = await teams_integration.send_channel_message(
                team_id=request.team_id,
                channel_id=request.channel_id,
                content=request.content,
                content_type=request.content_type
            )
        
        logger.info(f"[Teams] Successfully sent message")
        return SendTeamsMessageResponse(**result)
    except ValueError as e:
        logger.error(f"[Teams] Validation error sending message: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Teams] Error sending message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")


@router.post("/generate-todos/{message_id}", response_model=List[TodoItemResponse])
async def generate_todos_from_teams_message(
    message_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generate AI-powered todos from a Teams message"""
    try:
        logger.info(f"[Teams] Generating todos from Teams message: {message_id}")
        
        # Fetch Teams messages to find the specific message
        teams_result = await teams_integration.get_chats(max_results=100)
        messages = teams_result.get("messages", [])
        message = next((m for m in messages if (m.get("id") == message_id or m.get("message_id") == message_id)), None)
        
        if not message:
            raise HTTPException(status_code=404, detail="Teams message not found")
        
        # Extract message content
        content = message.get("content", "") or message.get("body", {}).get("content", "") if isinstance(message.get("body"), dict) else str(message.get("body", ""))
        sender = message.get("sender", "") or (message.get("from", {}).get("user", {}).get("displayName", "") if isinstance(message.get("from"), dict) else "")
        
        if not content:
            raise HTTPException(status_code=400, detail="Message has no content")
        
        # Generate todos using AI (similar to email todos generation)
        todos_data = await ai_service.generate_todos_from_email(
            email_subject=f"Teams message from {sender}",
            email_body=content,
            email_priority="MEDIUM"  # Default priority for Teams messages
        )
        
        if not todos_data:
            return []
        
        # Create todos in database
        created_todos = []
        for todo_data in todos_data:
            # Get the maximum order value for todos with the same priority
            priority = todo_data.get("priority", "medium").upper()
            result = await db.execute(
                select(TodoItem).where(TodoItem.priority == priority)
            )
            todos_with_priority = result.scalars().all()
            max_order = max([t.order for t in todos_with_priority if t.order is not None], default=-1.0)
            new_order = max_order + 1.0
            
            db_todo = TodoItem(
                title=todo_data.get("title", "Untitled Todo"),
                description=todo_data.get("description", ""),
                priority=priority,
                order=new_order,
                source_type="teams",
                source_id=message_id,
                source_data={
                    "sender": sender,
                    "content": content[:500],
                    "sent_at": message.get("sent_at") or message.get("createdDateTime")
                },
                created_at=datetime.now(timezone.utc)
            )
            db.add(db_todo)
            created_todos.append(db_todo)
        
        await db.commit()
        
        # Refresh todos to get IDs
        for todo in created_todos:
            await db.refresh(todo)
        
        logger.info(f"[Teams] Successfully created {len(created_todos)} todos from Teams message")
        
        return [TodoItemResponse(
            id=todo.id,
            title=todo.title,
            description=todo.description,
            priority=todo.priority,
            is_completed=todo.is_completed,
            source_type=todo.source_type,
            created_at=todo.created_at.isoformat() if todo.created_at else None
        ) for todo in created_todos]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Teams] Error generating todos from Teams message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating todos: {str(e)}")



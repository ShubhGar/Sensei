"""
Teams API routes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
import time

from app.models.schemas import TeamsSummary
from app.integrations.teams_integration import TeamsIntegration
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)
router = APIRouter()
teams_integration = TeamsIntegration()
ai_service = AIService()

# Simple in-memory cache for Teams requests (TTL: 30 seconds)
_teams_cache = {}
_cache_ttl = 30  # seconds


@router.get("/messages", response_model=TeamsSummary)
async def get_messages(
    max_results: int = Query(50, ge=1, le=100),
    chat_type: str = Query("chats", description="Type: 'chats' or 'channels'"),
    team_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    analyze_mentions: bool = Query(False, description="Analyze @mentions"),
    analyze_activity: bool = Query(False, description="Analyze channel activity")
):
    """Get Teams messages with AI analysis"""
    try:
        # Check cache first (only for basic requests without analysis)
        cache_key = f"teams_{chat_type}_{max_results}_{team_id}_{channel_id}_{analyze_mentions}_{analyze_activity}"
        if not analyze_mentions and not analyze_activity:
            cached = _teams_cache.get(cache_key)
            if cached and (time.time() - cached["timestamp"]) < _cache_ttl:
                logger.info(f"[Teams] Returning cached messages data (age: {time.time() - cached['timestamp']:.1f}s)")
                return TeamsSummary(**cached["data"])
        
        logger.info(f"[Teams] Getting messages - chat_type: {chat_type}, max_results: {max_results}, team_id: {team_id}, channel_id: {channel_id}")
        
        result = None
        if chat_type == "chats":
            result = await teams_integration.get_chats(max_results)
        elif chat_type == "channels":
            if not team_id or not channel_id:
                logger.warning(f"[Teams] Missing team_id/channel_id for channels - team_id: {team_id}, channel_id: {channel_id}")
                raise HTTPException(
                    status_code=400,
                    detail="team_id and channel_id are required when chat_type is 'channels'"
                )
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
        
        # Cache the result if it's a basic request
        if not analyze_mentions and not analyze_activity:
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
        
        logger.info(f"[Teams] Successfully retrieved {len(channels)} channels")
        return {"channels": channels, "team_id": team_id, "total": len(channels)}
    except Exception as e:
        logger.error(f"[Teams] Error fetching team channels: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching team channels: {str(e)}")


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



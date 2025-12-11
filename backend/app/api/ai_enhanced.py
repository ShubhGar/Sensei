"""
Enhanced AI Processing API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging

from app.models.schemas import (
    MeetingInsights, EmailCategorization, ChatMessage, ChatResponse,
    TrendAnalysis, SemanticSearchRequest, EmailSentimentAnalysis,
    EmailPriorityScore, TeamsConversationSummary, ChannelActivityAnalysis,
    MentionAnalysis, CrossPlatformCorrelation, DailyDigest,
    DeadlineRiskPrediction, TeamsResponseSuggestion, JiraIssue,
    ConfluencePage, ToneOptimization, SmartNotifications
)
from app.database import get_db, MeetingSession, TodoItem
from app.services.ai_service import AIService
from app.integrations.email_integration import EmailIntegration
from app.integrations.teams_integration import TeamsIntegration
import json

logger = logging.getLogger(__name__)
router = APIRouter()
ai_service = AIService()
email_integration = EmailIntegration()
teams_integration = TeamsIntegration()


@router.post("/meeting-insights/{session_id}", response_model=MeetingInsights)
async def get_meeting_insights(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get AI-powered insights for a meeting (sentiment, topics, engagement)"""
    try:
        # Get meeting session
        result = await db.execute(
            select(MeetingSession).where(MeetingSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Meeting session not found")
        
        # Get transcript and MOM
        transcript = session.full_transcript or session.transcript or ""
        if not transcript:
            raise HTTPException(status_code=400, detail="No transcript available")
        
        mom = session.mom
        if isinstance(mom, str):
            import json
            try:
                mom = json.loads(mom)
            except:
                mom = {}
        elif mom is None:
            mom = {}
        
        # Generate insights
        insights = await ai_service.analyze_meeting_insights(transcript, mom)
        
        return MeetingInsights(**insights)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating meeting insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating insights: {str(e)}")


@router.post("/categorize-email", response_model=EmailCategorization)
async def categorize_email(
    email_content: str = Query(..., description="Email content"),
    subject: str = Query(..., description="Email subject"),
    sender: str = Query(..., description="Email sender")
):
    """Categorize and prioritize an email using AI"""
    try:
        categorization = await ai_service.categorize_email(email_content, subject, sender)
        return EmailCategorization(**categorization)
    except Exception as e:
        logger.error(f"Error categorizing email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error categorizing email: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat_assistant(
    message: ChatMessage,
    db: AsyncSession = Depends(get_db)
):
    """AI chat assistant for answering questions about meetings, emails, etc.
    Automatically fetches all available data (meetings, emails, teams, todos) to provide context."""
    try:
        # Build comprehensive context from all available data sources
        context = message.context or {}
        
        # Fetch meetings from database
        try:
            meetings_result = await db.execute(
                select(MeetingSession)
                .order_by(MeetingSession.started_at.desc())
                .limit(20)
            )
            meetings = meetings_result.scalars().all()
            
            meetings_data = []
            for meeting in meetings:
                # Parse MOM if it's a string
                mom = meeting.mom
                if isinstance(mom, str):
                    try:
                        mom = json.loads(mom)
                    except:
                        mom = None
                
                # Parse FAQs if it's a string
                faqs = meeting.faqs
                if isinstance(faqs, str):
                    try:
                        faqs = json.loads(faqs)
                    except:
                        faqs = None
                
                meeting_info = {
                    "id": meeting.id,
                    "title": meeting.title,
                    "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
                    "ended_at": meeting.ended_at.isoformat() if meeting.ended_at else None,
                    "transcript": (meeting.full_transcript or meeting.transcript or "")[:2000],  # Limit transcript length
                    "mom_summary": mom.get("summary", "") if isinstance(mom, dict) else "",
                    "mom_decisions": mom.get("decisions", []) if isinstance(mom, dict) else [],
                    "mom_action_items": mom.get("action_items", []) if isinstance(mom, dict) else [],
                    "faqs": faqs if faqs else []
                }
                meetings_data.append(meeting_info)
            
            context["meetings"] = meetings_data
            logger.info(f"[Chat] Loaded {len(meetings_data)} meetings for context")
        except Exception as e:
            logger.warning(f"[Chat] Error loading meetings: {e}")
            context["meetings"] = []
        
        # Fetch emails from email integration
        try:
            emails = await email_integration.get_outlook_inbox(max_results=20, unread_only=False)
            emails_data = []
            for email in emails:
                # Email integration returns: sender, sender_email, body_preview, received_at, is_read, etc.
                email_info = {
                    "id": email.get("id", ""),
                    "subject": email.get("subject", "No Subject"),
                    "sender": email.get("sender", "") or email.get("sender_email", ""),
                    "preview": email.get("body_preview", "") or email.get("body", "")[:500],
                    "received_at": email.get("received_at", ""),
                    "is_read": email.get("is_read", True),
                    "importance": email.get("importance", "normal")
                }
                emails_data.append(email_info)
            
            context["emails"] = emails_data
            logger.info(f"[Chat] Loaded {len(emails_data)} emails for context")
        except Exception as e:
            logger.warning(f"[Chat] Error loading emails: {e}")
            context["emails"] = []
        
        # Fetch Teams messages
        try:
            teams_result = await teams_integration.get_chats(max_results=20)
            teams_messages = teams_result.get("messages", [])
            teams_data = []
            for msg in teams_messages:
                message_info = {
                    "id": msg.get("id", ""),
                    "content": msg.get("body", {}).get("content", "")[:500] if isinstance(msg.get("body"), dict) else str(msg.get("body", ""))[:500],
                    "sender": msg.get("from", {}).get("user", {}).get("displayName", "") if isinstance(msg.get("from"), dict) else "",
                    "sent_at": msg.get("createdDateTime", ""),
                    "chat_id": msg.get("chatId", "")
                }
                teams_data.append(message_info)
            
            context["teams"] = teams_data
            logger.info(f"[Chat] Loaded {len(teams_data)} Teams messages for context")
        except Exception as e:
            logger.warning(f"[Chat] Error loading Teams messages: {e}")
            context["teams"] = []
        
        # Fetch todos from database - include both completed and incomplete
        try:
            # First get incomplete todos (priority)
            incomplete_todos_result = await db.execute(
                select(TodoItem)
                .where(TodoItem.is_completed == False)
                .order_by(TodoItem.priority.desc(), TodoItem.created_at.desc())
                .limit(30)
            )
            incomplete_todos = incomplete_todos_result.scalars().all()
            
            # Also get recently completed todos (last 10)
            completed_todos_result = await db.execute(
                select(TodoItem)
                .where(TodoItem.is_completed == True)
                .order_by(TodoItem.completed_at.desc())
                .limit(10)
            )
            completed_todos = completed_todos_result.scalars().all()
            
            todos_data = []
            for todo in incomplete_todos:
                todo_info = {
                    "id": todo.id,
                    "title": todo.title,
                    "description": todo.description or "",
                    "priority": todo.priority,
                    "source_type": todo.source_type,
                    "is_completed": False,
                    "created_at": todo.created_at.isoformat() if todo.created_at else None
                }
                todos_data.append(todo_info)
            
            for todo in completed_todos:
                todo_info = {
                    "id": todo.id,
                    "title": todo.title,
                    "description": todo.description or "",
                    "priority": todo.priority,
                    "source_type": todo.source_type,
                    "is_completed": True,
                    "created_at": todo.created_at.isoformat() if todo.created_at else None,
                    "completed_at": todo.completed_at.isoformat() if todo.completed_at else None
                }
                todos_data.append(todo_info)
            
            context["todos"] = todos_data
            logger.info(f"[Chat] Loaded {len(incomplete_todos)} incomplete and {len(completed_todos)} completed todos for context")
        except Exception as e:
            logger.warning(f"[Chat] Error loading todos: {e}")
            context["todos"] = []
        
        # Call AI service with comprehensive context
        response = await ai_service.chat_assistant(
            query=message.query,
            context=context
        )
        return ChatResponse(**response)
    except Exception as e:
        logger.error(f"Error in chat assistant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in chat assistant: {str(e)}")


@router.get("/trends", response_model=TrendAnalysis)
async def analyze_trends(
    limit: int = Query(10, ge=1, le=50, description="Number of meetings to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """Analyze trends across multiple meetings"""
    try:
        # Get recent meetings with MOM data
        result = await db.execute(
            select(MeetingSession)
            .where(MeetingSession.mom.isnot(None))
            .order_by(MeetingSession.started_at.desc())
            .limit(limit)
        )
        meetings = result.scalars().all()
        
        if not meetings:
            logger.info("No meetings with MOM data found for trends analysis")
            return TrendAnalysis()
        
        # Prepare meeting data and filter out meetings with empty/invalid MOM
        meetings_data = []
        for meeting in meetings:
            mom = meeting.mom
            # Check if MOM is valid (not None, not empty string, not empty dict)
            if mom is None:
                continue
            if isinstance(mom, str):
                try:
                    mom_parsed = json.loads(mom)
                    if not mom_parsed or (isinstance(mom_parsed, dict) and not mom_parsed):
                        continue
                except:
                    # If it's not valid JSON, skip this meeting
                    continue
            
            meeting_dict = {
                "id": meeting.id,
                "title": meeting.title or "Untitled Meeting",
                "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
                "mom": mom
            }
            meetings_data.append(meeting_dict)
        
        if not meetings_data:
            logger.info("No meetings with valid MOM data found for trends analysis")
            return TrendAnalysis()
        
        # Analyze trends
        trends = await ai_service.analyze_trends(meetings_data)
        
        return TrendAnalysis(**trends)
    except Exception as e:
        logger.error(f"Error analyzing trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error analyzing trends: {str(e)}")


@router.post("/semantic-search")
async def semantic_search(
    request: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Perform semantic search across meetings, emails, and teams"""
    try:
        # Collect documents from various sources
        documents = []
        
        # Search meetings
        meetings_result = await db.execute(
            select(MeetingSession)
            .where(
                (MeetingSession.transcript.isnot(None)) |
                (MeetingSession.full_transcript.isnot(None))
            )
            .limit(20)
        )
        meetings = meetings_result.scalars().all()
        
        for meeting in meetings:
            text = meeting.full_transcript or meeting.transcript or ""
            if text:
                documents.append({
                    "id": f"meeting_{meeting.id}",
                    "type": "meeting",
                    "title": meeting.title or "Untitled Meeting",
                    "text": text[:1000],
                    "metadata": {
                        "started_at": meeting.started_at.isoformat() if meeting.started_at else None
                    }
                })
        
        # Perform semantic search
        if documents:
            ranked_results = await ai_service.semantic_search(request.query, documents)
            # Limit results
            ranked_results = ranked_results[:request.limit or 10]
        else:
            ranked_results = []
        
        return {
            "query": request.query,
            "results": ranked_results,
            "total_results": len(ranked_results)
        }
    except Exception as e:
        logger.error(f"Error in semantic search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in semantic search: {str(e)}")


@router.post("/email/sentiment", response_model=EmailSentimentAnalysis)
async def analyze_email_sentiment(
    email_content: str = Query(..., description="Email content"),
    subject: str = Query(..., description="Email subject")
):
    """Analyze email sentiment (frustration, urgency, positive/negative)"""
    try:
        sentiment = await ai_service.analyze_email_sentiment(email_content, subject)
        return EmailSentimentAnalysis(**sentiment)
    except Exception as e:
        logger.error(f"Error analyzing email sentiment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error analyzing sentiment: {str(e)}")


@router.post("/email/priority-score", response_model=EmailPriorityScore)
async def score_email_priority(
    email_content: str = Query(..., description="Email content"),
    subject: str = Query(..., description="Email subject"),
    sender: str = Query(..., description="Email sender"),
    received_at: Optional[str] = Query(None, description="Email received date")
):
    """Score email priority by importance (0-100)"""
    try:
        priority = await ai_service.score_email_priority(
            email_content, subject, sender, received_at
        )
        return EmailPriorityScore(**priority)
    except Exception as e:
        logger.error(f"Error scoring email priority: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error scoring priority: {str(e)}")


class TeamsConversationRequest(BaseModel):
    """Request for Teams conversation summary"""
    messages: List[Dict[str, Any]]
    thread_id: Optional[str] = None


@router.post("/teams/conversation-summary", response_model=TeamsConversationSummary)
async def summarize_teams_conversation(
    request: TeamsConversationRequest
):
    """Generate thread-level summary for Teams conversation"""
    try:
        summary = await ai_service.summarize_teams_conversation(
            request.messages, request.thread_id
        )
        return TeamsConversationSummary(**summary)
    except Exception as e:
        logger.error(f"Error summarizing Teams conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error summarizing conversation: {str(e)}")


class ChannelActivityRequest(BaseModel):
    """Request for channel activity analysis"""
    messages: List[Dict[str, Any]]
    channel_name: Optional[str] = None


@router.post("/teams/channel-activity", response_model=ChannelActivityAnalysis)
async def analyze_channel_activity(
    request: ChannelActivityRequest
):
    """Analyze Teams channel activity for active discussions and blockers"""
    try:
        analysis = await ai_service.analyze_channel_activity(
            request.messages, request.channel_name
        )
        return ChannelActivityAnalysis(**analysis)
    except Exception as e:
        logger.error(f"Error analyzing channel activity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error analyzing channel: {str(e)}")


class MentionAnalysisRequest(BaseModel):
    """Request for mention analysis"""
    messages: List[Dict[str, Any]]
    user_email: Optional[str] = None


@router.post("/teams/mentions", response_model=MentionAnalysis)
async def analyze_mentions(
    request: MentionAnalysisRequest
):
    """Analyze @mentions in Teams messages"""
    try:
        analysis = await ai_service.analyze_mentions(
            request.messages, request.user_email
        )
        return MentionAnalysis(**analysis)
    except Exception as e:
        logger.error(f"Error analyzing mentions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error analyzing mentions: {str(e)}")


class CorrelationRequest(BaseModel):
    """Request for cross-platform correlation"""
    emails: List[Dict[str, Any]] = []
    teams_messages: List[Dict[str, Any]] = []


@router.post("/correlate", response_model=CrossPlatformCorrelation)
async def correlate_cross_platform(
    request: CorrelationRequest
):
    """Correlate Teams discussions with related emails"""
    try:
        correlation = await ai_service.correlate_cross_platform(
            request.emails, request.teams_messages
        )
        return CrossPlatformCorrelation(**correlation)
    except Exception as e:
        logger.error(f"Error correlating cross-platform: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error correlating: {str(e)}")


@router.get("/digest/daily", response_model=DailyDigest)
async def get_daily_digest(
    db: AsyncSession = Depends(get_db)
):
    """Generate daily digest combining emails + Teams activity"""
    try:
        # Fetch emails
        emails = []
        try:
            emails = await email_integration.get_outlook_inbox(max_results=50, unread_only=False)
        except Exception as e:
            logger.warning(f"Error fetching emails for digest: {e}")
        
        # Fetch Teams messages
        teams_messages = []
        try:
            teams_result = await teams_integration.get_chats(max_results=50)
            teams_messages = teams_result.get("messages", [])
        except Exception as e:
            logger.warning(f"Error fetching Teams for digest: {e}")
        
        # Fetch todos
        todos = []
        try:
            todos_result = await db.execute(
                select(TodoItem)
                .where(TodoItem.is_completed == False)
                .order_by(TodoItem.created_at.desc())
                .limit(50)
            )
            todos_list = todos_result.scalars().all()
            todos = [
                {
                    "id": t.id,
                    "title": t.title,
                    "priority": t.priority,
                    "created_at": t.created_at.isoformat() if t.created_at else None
                }
                for t in todos_list
            ]
        except Exception as e:
            logger.warning(f"Error fetching todos for digest: {e}")
        
        # Fetch meetings
        meetings = []
        try:
            meetings_result = await db.execute(
                select(MeetingSession)
                .order_by(MeetingSession.started_at.desc())
                .limit(10)
            )
            meetings_list = meetings_result.scalars().all()
            meetings = [
                {
                    "id": m.id,
                    "title": m.title,
                    "started_at": m.started_at.isoformat() if m.started_at else None
                }
                for m in meetings_list
            ]
        except Exception as e:
            logger.warning(f"Error fetching meetings for digest: {e}")
        
        digest = await ai_service.generate_daily_digest(
            emails, teams_messages, todos, meetings
        )
        return DailyDigest(**digest)
    except Exception as e:
        logger.error(f"Error generating daily digest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating digest: {str(e)}")


@router.get("/risks/deadlines", response_model=DeadlineRiskPrediction)
async def predict_deadline_risks(
    db: AsyncSession = Depends(get_db)
):
    """Predict deadline risks based on todos, emails, and meetings"""
    try:
        # Fetch todos
        todos_result = await db.execute(
            select(TodoItem)
            .where(TodoItem.is_completed == False)
            .order_by(TodoItem.priority.desc(), TodoItem.created_at.desc())
            .limit(50)
        )
        todos_list = todos_result.scalars().all()
        todos = [
            {
                "id": t.id,
                "title": t.title,
                "priority": t.priority,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "source_type": t.source_type
            }
            for t in todos_list
        ]
        
        # Fetch emails
        emails = []
        try:
            emails = await email_integration.get_outlook_inbox(max_results=20, unread_only=False)
        except Exception as e:
            logger.warning(f"Error fetching emails for risk prediction: {e}")
        
        # Fetch meetings
        meetings = []
        try:
            meetings_result = await db.execute(
                select(MeetingSession)
                .order_by(MeetingSession.started_at.desc())
                .limit(10)
            )
            meetings_list = meetings_result.scalars().all()
            meetings = [
                {
                    "id": m.id,
                    "title": m.title,
                    "started_at": m.started_at.isoformat() if m.started_at else None
                }
                for m in meetings_list
            ]
        except Exception as e:
            logger.warning(f"Error fetching meetings for risk prediction: {e}")
        
        risks = await ai_service.predict_deadline_risks(todos, emails, meetings)
        return DeadlineRiskPrediction(**risks)
    except Exception as e:
        logger.error(f"Error predicting deadline risks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error predicting risks: {str(e)}")


class TeamsResponseRequest(BaseModel):
    """Request for Teams response suggestion"""
    message_content: str
    conversation_context: Optional[List[Dict[str, Any]]] = None
    tone: Optional[str] = None


@router.post("/teams/suggest-response", response_model=TeamsResponseSuggestion)
async def suggest_teams_response(
    request: TeamsResponseRequest
):
    """Suggest polished Teams responses"""
    try:
        suggestion = await ai_service.suggest_teams_response(
            request.message_content, request.conversation_context, request.tone
        )
        return TeamsResponseSuggestion(**suggestion)
    except Exception as e:
        logger.error(f"Error suggesting Teams response: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error suggesting response: {str(e)}")


@router.post("/convert/jira", response_model=JiraIssue)
async def convert_to_jira(
    text: str = Query(..., description="Text to convert"),
    issue_type: str = Query("Task", description="Jira issue type")
):
    """Convert text into Jira issue format"""
    try:
        jira_issue = await ai_service.convert_to_jira(text, issue_type)
        return JiraIssue(**jira_issue)
    except Exception as e:
        logger.error(f"Error converting to Jira: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error converting to Jira: {str(e)}")


@router.post("/convert/confluence", response_model=ConfluencePage)
async def convert_to_confluence(
    text: str = Query(..., description="Text to convert"),
    page_type: str = Query("Documentation", description="Confluence page type")
):
    """Convert text into Confluence page format"""
    try:
        confluence_page = await ai_service.convert_to_confluence(text, page_type)
        return ConfluencePage(**confluence_page)
    except Exception as e:
        logger.error(f"Error converting to Confluence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error converting to Confluence: {str(e)}")


@router.post("/optimize-tone", response_model=ToneOptimization)
async def optimize_communication_tone(
    text: str = Query(..., description="Text to optimize"),
    target_audience: str = Query(..., description="Target audience"),
    desired_tone: str = Query(..., description="Desired tone"),
    context: Optional[str] = Query(None, description="Additional context")
):
    """Optimize communication tone for target audience"""
    try:
        optimization = await ai_service.optimize_communication_tone(
            text, target_audience, desired_tone, context
        )
        return ToneOptimization(**optimization)
    except Exception as e:
        logger.error(f"Error optimizing tone: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error optimizing tone: {str(e)}")


@router.get("/notifications/smart", response_model=SmartNotifications)
async def get_smart_notifications(
    db: AsyncSession = Depends(get_db)
):
    """Get smart notifications - only truly important items"""
    try:
        # Fetch emails
        emails = []
        try:
            emails = await email_integration.get_outlook_inbox(max_results=50, unread_only=False)
        except Exception as e:
            logger.warning(f"Error fetching emails for notifications: {e}")
        
        # Fetch Teams messages
        teams_messages = []
        try:
            teams_result = await teams_integration.get_chats(max_results=50)
            teams_messages = teams_result.get("messages", [])
        except Exception as e:
            logger.warning(f"Error fetching Teams for notifications: {e}")
        
        # Fetch todos
        todos = []
        try:
            todos_result = await db.execute(
                select(TodoItem)
                .where(TodoItem.is_completed == False)
                .order_by(TodoItem.priority.desc(), TodoItem.created_at.desc())
                .limit(50)
            )
            todos_list = todos_result.scalars().all()
            todos = [
                {
                    "id": t.id,
                    "title": t.title,
                    "priority": t.priority,
                    "is_completed": t.is_completed,
                    "created_at": t.created_at.isoformat() if t.created_at else None
                }
                for t in todos_list
            ]
        except Exception as e:
            logger.warning(f"Error fetching todos for notifications: {e}")
        
        # Fetch meetings
        meetings = []
        try:
            meetings_result = await db.execute(
                select(MeetingSession)
                .order_by(MeetingSession.started_at.desc())
                .limit(10)
            )
            meetings_list = meetings_result.scalars().all()
            meetings = [
                {
                    "id": m.id,
                    "title": m.title,
                    "started_at": m.started_at.isoformat() if m.started_at else None
                }
                for m in meetings_list
            ]
        except Exception as e:
            logger.warning(f"Error fetching meetings for notifications: {e}")
        
        notifications = await ai_service.generate_smart_notifications(
            emails, teams_messages, todos, meetings
        )
        # Ensure the response matches the schema
        try:
            return SmartNotifications(**notifications)
        except Exception as validation_error:
            logger.error(f"Pydantic validation error for smart notifications: {validation_error}", exc_info=True)
            # Return a safe fallback response
            return SmartNotifications(
                notifications=[],
                total=0,
                summary="Error generating notifications. Please try again."
            )
    except Exception as e:
        logger.error(f"Error generating smart notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating notifications: {str(e)}")


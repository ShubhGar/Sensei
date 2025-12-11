"""
Enhanced AI Processing API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import logging

from app.models.schemas import (
    MeetingInsights, EmailCategorization, ChatMessage, ChatResponse,
    TrendAnalysis, SemanticSearchRequest
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
        
        # Fetch todos from database
        try:
            todos_result = await db.execute(
                select(TodoItem)
                .where(TodoItem.is_completed == False)
                .order_by(TodoItem.priority.desc(), TodoItem.created_at.desc())
                .limit(20)
            )
            todos = todos_result.scalars().all()
            
            todos_data = []
            for todo in todos:
                todo_info = {
                    "id": todo.id,
                    "title": todo.title,
                    "description": todo.description or "",
                    "priority": todo.priority,
                    "source_type": todo.source_type,
                    "created_at": todo.created_at.isoformat() if todo.created_at else None
                }
                todos_data.append(todo_info)
            
            context["todos"] = todos_data
            logger.info(f"[Chat] Loaded {len(todos_data)} todos for context")
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


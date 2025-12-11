"""
Email API routes
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import EmailSummary, AutoReplySuggestion, TodoItemCreate, TodoItemResponse
from app.integrations.email_integration import EmailIntegration
from app.services.ai_service import AIService
from app.database import get_db
from app.api.todos import create_todo

logger = logging.getLogger(__name__)
router = APIRouter()
email_integration = EmailIntegration()
ai_service = AIService()


@router.get("/inbox", response_model=EmailSummary)
async def get_inbox(
    max_results: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False)
):
    """Get inbox summary with AI analysis"""
    try:
        logger.info(f"[Email] Getting inbox - max_results: {max_results}, unread_only: {unread_only}")
        
        emails = await email_integration.get_outlook_inbox(max_results, unread_only)
        summary = await email_integration.analyze_inbox(emails, ai_service)
        
        logger.info(f"[Email] Successfully retrieved {len(emails)} emails from Outlook")
        return EmailSummary(**summary)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Email] Error fetching inbox: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching inbox: {str(e)}")


@router.post("/suggest-reply/{email_id}")
async def suggest_reply(email_id: str):
    """Suggest auto-reply for an email"""
    try:
        emails = await email_integration.get_outlook_inbox(max_results=100)
        
        email = next((e for e in emails if e.get("id") == email_id), None)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        email_content = f"{email.get('subject', '')} {email.get('body', '')}"
        suggestion = await ai_service.suggest_auto_reply(email_content)
        
        return AutoReplySuggestion(
            email_id=email_id,
            suggested_reply=suggestion.get("suggested_reply", ""),
            confidence=suggestion.get("confidence", 0.0),
            reasoning=suggestion.get("reasoning")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error suggesting reply: {str(e)}")


@router.post("/summarize/{email_id}")
async def summarize_email(email_id: str):
    """Summarize a single email on demand"""
    try:
        logger.info(f"[Email] Summarizing email: {email_id}")
        
        emails = await email_integration.get_outlook_inbox(max_results=100)
        
        email = next((e for e in emails if e.get("id") == email_id), None)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        email_content = f"{email.get('subject', '')} {email.get('body', '') or email.get('body_preview', '')}"
        summary = await ai_service.summarize_email(email_content)
        
        return {"email_id": email_id, "summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Email] Error summarizing email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error summarizing email: {str(e)}")


@router.post("/authenticate")
async def authenticate_email(auth_code: Optional[str] = None):
    """Authenticate with Outlook"""
    try:
        success = await email_integration.authenticate_microsoft(auth_code)
        
        if success:
            return {"status": "authenticated", "provider": "outlook"}
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@router.post("/generate-todos/{email_id}", response_model=List[TodoItemResponse])
async def generate_todos_from_email(
    email_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generate AI-powered todos from an email"""
    try:
        logger.info(f"[Email] Generating todos from email: {email_id}")
        
        # Fetch the email
        emails = await email_integration.get_outlook_inbox(max_results=100)
        email = next((e for e in emails if e.get("id") == email_id), None)
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Extract email content
        subject = email.get("subject", "")
        body = email.get("body", "") or email.get("body_preview", "")
        priority = email.get("importance", "normal")  # normal, low, high
        
        # Map Microsoft importance to our priority format
        email_priority = None
        if priority == "high":
            email_priority = "CRITICAL"
        elif priority == "normal":
            email_priority = "MEDIUM"
        elif priority == "low":
            email_priority = "LOW"
        
        # Generate todos using AI
        todos_data = await ai_service.generate_todos_from_email(
            email_subject=subject,
            email_body=body,
            email_priority=email_priority
        )
        
        if not todos_data:
            return []
        
        # Create todos in database
        created_todos = []
        for todo_data in todos_data:
            todo_create = TodoItemCreate(
                title=todo_data.get("title", subject[:100]),
                description=todo_data.get("description"),
                priority=todo_data.get("priority", "medium"),
                source_type="email",
                source_id=email_id,
                source_data={
                    "email_subject": subject,
                    "email_sender": email.get("sender", ""),
                    "email_received_at": email.get("received_at")
                }
            )
            
            # Create todo using the todos API function
            created_todo = await create_todo(todo_create, db)
            created_todos.append(created_todo)
        
        logger.info(f"[Email] Successfully created {len(created_todos)} todos from email {email_id}")
        return created_todos
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Email] Error generating todos from email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating todos: {str(e)}")



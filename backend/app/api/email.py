"""
Email API routes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.models.schemas import EmailSummary, AutoReplySuggestion
from app.integrations.email_integration import EmailIntegration
from app.services.ai_service import AIService

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



"""
AI Processing API routes
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import ValidationError
import logging

from app.models.schemas import AIProcessingRequest, AIProcessingResponse, MOMResponse, FAQItem, EmailDraft
from app.database import get_db, MeetingSession
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)
router = APIRouter()
ai_service = AIService()


@router.post("/summarize", response_model=AIProcessingResponse)
async def summarize_transcript(
    request: AIProcessingRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate MOM, FAQs, email draft, and risk analysis from transcript"""
    try:
        logger.info(f"[AI Processing] Received summarize request for session_id: {request.session_id}")
        logger.info(f"[AI Processing] Request params - include_faqs: {request.include_faqs}, include_email_draft: {request.include_email_draft}")
        
        # Get meeting session
        result = await db.execute(
            select(MeetingSession).where(MeetingSession.id == request.session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            logger.warning(f"[AI Processing] ERROR: Session {request.session_id} not found")
            raise HTTPException(status_code=404, detail="Meeting session not found")
        
        # Get transcript from either full_transcript or transcript field
        transcript = session.full_transcript or session.transcript or ""
        logger.info(f"[AI Processing] Transcript length: {len(transcript)}, full_transcript: {bool(session.full_transcript)}, transcript: {bool(session.transcript)}")
        
        if not transcript or not transcript.strip():
            logger.warning(f"[AI Processing] ERROR: No transcript available for session {request.session_id}")
            raise HTTPException(
                status_code=400, 
                detail="No transcript available for this session. Please ensure the transcription was completed successfully."
            )
        
        # Generate MOM
        logger.info(f"[AI Processing] Generating MOM for session {request.session_id}...")
        try:
            mom_data = await ai_service.generate_mom(
                transcript=transcript,
                session_id=request.session_id
            )
            logger.info(f"[AI Processing] MOM data received: {list(mom_data.keys())}")
        except Exception as e:
            logger.error(f"[AI Processing] ERROR generating MOM: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to generate MOM: {str(e)}")
        
        # Ensure all required fields are present with defaults
        if "summary" not in mom_data or not mom_data["summary"]:
            mom_data["summary"] = "No summary available."
        if "decisions" not in mom_data:
            mom_data["decisions"] = []
        if "action_items" not in mom_data:
            mom_data["action_items"] = []
        if "key_points" not in mom_data:
            mom_data["key_points"] = []
        if "attendees" not in mom_data:
            mom_data["attendees"] = []
        
        logger.info(f"[AI Processing] Normalized MOM data - summary length: {len(mom_data.get('summary', ''))}, decisions: {len(mom_data.get('decisions', []))}, action_items: {len(mom_data.get('action_items', []))}")
        
        # Ensure decisions and action_items are properly formatted
        decisions = []
        for decision in mom_data.get("decisions", []):
            if isinstance(decision, dict):
                decisions.append(DecisionItem(
                    decision=decision.get("decision", ""),
                    context=decision.get("context"),
                    timestamp=decision.get("timestamp")
                ))
        
        action_items = []
        for item in mom_data.get("action_items", []):
            if isinstance(item, dict):
                action_items.append(ActionItem(
                    task=item.get("task", ""),
                    owner=item.get("owner", "TBD"),
                    deadline=item.get("deadline"),
                    priority=item.get("priority", "medium"),
                    context=item.get("context")
                ))
        
        try:
            mom = MOMResponse(
                session_id=mom_data.get("session_id", request.session_id),
                summary=mom_data.get("summary", "No summary available."),
                decisions=decisions,
                action_items=action_items,
                key_points=mom_data.get("key_points", []),
                attendees=mom_data.get("attendees", []),
                duration=mom_data.get("duration")
            )
            logger.info(f"[AI Processing] MOMResponse created successfully")
        except Exception as e:
            logger.error(f"[AI Processing] ERROR creating MOMResponse: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create MOM response: {str(e)}")
        
        # Generate FAQs if requested
        faqs = None
        if request.include_faqs:
            try:
                faq_data = await ai_service.generate_faqs(transcript, mom_data)
                faqs = []
                for faq in faq_data:
                    if isinstance(faq, dict):
                        faqs.append(FAQItem(
                            question=faq.get("question", ""),
                            answer=faq.get("answer", ""),
                            context=faq.get("context")
                        ))
            except Exception as e:
                logger.warning(f"[AI Processing] Error generating FAQs: {e}")
                faqs = []  # Return empty list instead of None if requested
        
        # Generate email draft if requested
        email_draft = None
        if request.include_email_draft:
            try:
                email_data = await ai_service.generate_email_draft(mom_data)
                if isinstance(email_data, dict):
                    email_draft = EmailDraft(
                        to=email_data.get("to", []),
                        subject=email_data.get("subject", "Meeting Follow-up"),
                        body=email_data.get("body", ""),
                        cc=email_data.get("cc"),
                        bcc=email_data.get("bcc")
                    )
            except Exception as e:
                logger.warning(f"[AI Processing] Error generating email draft: {e}")
                email_draft = None
        
        # Detect risks
        risks = None
        try:
            risks = await ai_service.detect_risks(
                transcript=transcript,
                action_items=mom_data.get("action_items", [])
            )
            if not isinstance(risks, list):
                risks = []
        except Exception as e:
            logger.warning(f"[AI Processing] Error detecting risks: {e}")
            risks = []
        
        # Update session with MOM data
        session.mom = {
            "summary": mom_data.get("summary"),
            "decisions": mom_data.get("decisions", []),
            "action_items": mom_data.get("action_items", []),
            "key_points": mom_data.get("key_points", []),
            "attendees": mom_data.get("attendees", []),
            "duration": mom_data.get("duration")
        }
        session.faqs = [faq.dict() for faq in faqs] if faqs else None
        session.email_draft = email_draft.dict() if email_draft else None
        session.risks = risks
        
        await db.commit()
        logger.info(f"[AI Processing] Session updated successfully")
        
        # Create response
        try:
            response = AIProcessingResponse(
                mom=mom,
                faqs=faqs,
                email_draft=email_draft,
                risks=risks
            )
            logger.info(f"[AI Processing] Response created successfully for session {request.session_id}")
            return response
        except ValidationError as e:
            logger.error(f"[AI Processing] ERROR: Validation error creating response: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create response: {str(e)}")
    except HTTPException as he:
        logger.warning(f"[AI Processing] HTTPException raised: {he.status_code} - {he.detail}")
        raise
    except ValidationError as e:
        logger.error(f"[AI Processing] Validation error in summarize_transcript: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid request data: {str(e)}")
    except Exception as e:
        logger.error(f"[AI Processing] Unexpected error in summarize_transcript: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing transcript: {str(e)}")

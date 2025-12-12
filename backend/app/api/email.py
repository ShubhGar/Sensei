"""
Email API routes
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
import logging
import time
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import EmailSummary, AutoReplySuggestion, TodoItemCreate, TodoItemResponse, SendEmailRequest, SendEmailResponse
from app.integrations.email_integration import EmailIntegration
from app.services.ai_service import AIService
from app.database import get_db
from app.api.todos import create_todo

logger = logging.getLogger(__name__)
router = APIRouter()
email_integration = EmailIntegration()
ai_service = AIService()

# Simple in-memory cache for inbox requests (TTL: 60 seconds - increased for better performance)
_inbox_cache = {}
_cache_ttl = 60  # seconds


@router.get("/inbox", response_model=EmailSummary)
async def get_inbox(
    max_results: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    include_sentiment: bool = Query(False, description="Include sentiment analysis"),
    include_priority_score: bool = Query(False, description="Include priority scoring")
):
    """Get inbox summary with AI analysis"""
    try:
        # Check cache first (cache works for all requests including priority scores)
        cache_key = f"inbox_{max_results}_{unread_only}_{include_sentiment}_{include_priority_score}"
        cached = _inbox_cache.get(cache_key)
        if cached and (time.time() - cached["timestamp"]) < _cache_ttl:
            logger.info(f"[Email] Returning cached inbox data (age: {time.time() - cached['timestamp']:.1f}s)")
            return EmailSummary(**cached["data"])
        
        logger.info(f"[Email] Getting inbox - max_results: {max_results}, unread_only: {unread_only}")
        
        emails = await email_integration.get_outlook_inbox(max_results, unread_only)
        
        # Enhance emails with priority scoring and sentiment for criticality/urgency sorting
        # Only if not cached (cached results already have priority scores)
        # Process in parallel with timeout to avoid blocking
        
        async def score_email_priority_with_timeout(email, timeout=2.0):
            """Score email priority with timeout"""
            subject = email.get("subject", "")
            body = email.get("body", "") or email.get("body_preview", "")
            sender = email.get("sender", "")
            received_at = email.get("received_at")
            
            try:
                priority = await asyncio.wait_for(
                    ai_service.score_email_priority(body, subject, sender, received_at),
                    timeout=timeout
                )
                email["priority_score"] = priority
                # Set default urgency and criticality if not provided
                if "urgency_score" not in priority:
                    priority["urgency_score"] = priority.get("priority_score", 50)
                if "criticality_score" not in priority:
                    priority["criticality_score"] = priority.get("priority_score", 50)
            except asyncio.TimeoutError:
                logger.warning(f"[Email] Priority scoring timeout for email {email.get('id')}")
                email["priority_score"] = {
                    "priority_score": 50,
                    "priority_level": "medium",
                    "urgency_score": 50,
                    "criticality_score": 50,
                    "waiting_for_us": False,
                    "blocked_on_us": False,
                    "factors": []
                }
            except Exception as e:
                logger.warning(f"[Email] Error scoring priority for email {email.get('id')}: {e}")
                email["priority_score"] = {
                    "priority_score": 50,
                    "priority_level": "medium",
                    "urgency_score": 50,
                    "criticality_score": 50,
                    "waiting_for_us": False,
                    "blocked_on_us": False,
                    "factors": []
                }
        
        async def analyze_sentiment_with_timeout(email, timeout=3.0):
            """Analyze email sentiment with timeout"""
            if not include_sentiment:
                return
            subject = email.get("subject", "")
            body = email.get("body", "") or email.get("body_preview", "")
            try:
                sentiment = await asyncio.wait_for(
                    ai_service.analyze_email_sentiment(body, subject),
                    timeout=timeout
                )
                email["sentiment"] = sentiment
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"[Email] Error analyzing sentiment for email {email.get('id')}: {e}")
        
        async def check_needs_jira_with_timeout(email, timeout=2.0):
            """Check if email needs JIRA ticket with timeout"""
            try:
                # Get full email content (prefer body over body_preview for better detection)
                email_body = email.get("body", "") or email.get("body_preview", "") or ""
                email_subject = email.get("subject", "")
                
                # Combine subject and body for better context
                full_content = f"{email_subject} {email_body}".strip()
                
                needs_jira = await asyncio.wait_for(
                    ai_service.check_needs_jira("email", {
                        "subject": email_subject,
                        "sender": email.get("sender", ""),
                        "body_preview": email_body[:2000],  # Limit to avoid token issues
                        "content": email_body[:2000]
                    }),
                    timeout=timeout
                )
                email["needs_jira"] = needs_jira
                logger.info(f"[Email] JIRA check for email {email.get('id')[:20]}... - needs_jira: {needs_jira}, subject: {email_subject[:50]}")
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"[Email] Error checking if email needs JIRA {email.get('id')}: {e}")
                # Fallback: do a quick keyword check (but ALWAYS exclude leave requests)
                email_body = email.get("body", "") or email.get("body_preview", "") or ""
                email_subject = email.get("subject", "")
                text = f"{email_subject} {email_body}".lower()
                
                # First check for leave request keywords - ALWAYS exclude these
                leave_keywords = ['leave request', 'leave application', 'vacation', 'time off', 'holiday', 
                                'sick leave', 'personal leave', 'annual leave', 'casual leave',
                                'applying for leave', 'requesting leave', 'need leave', 'taking leave',
                                'leave approval', 'leave balance', 'leave days']
                if any(leave_keyword in text for leave_keyword in leave_keywords):
                    email["needs_jira"] = False
                    logger.info(f"[Email] Fallback JIRA check - excluded (leave request) for email {email.get('id')[:20]}...")
                else:
                    # Not a leave request, check for bug/task keywords
                    fallback_keywords = ['bug', 'issue', 'problem', 'observed', 'seeing', 'multiple', 'fix', 'defect', 'verification']
                    email["needs_jira"] = any(keyword in text for keyword in fallback_keywords)
                    logger.info(f"[Email] Fallback JIRA check for email {email.get('id')[:20]}... - needs_jira: {email['needs_jira']}")
        
        # Process emails in parallel batches (limit to 10 for better coverage)
        # Check JIRA needs for more emails (up to 10) to catch important issues
        emails_to_score = emails[:10]  # Increased from 5 to 10
        if emails_to_score:
            # Score priority in parallel with shorter timeout
            await asyncio.gather(*[score_email_priority_with_timeout(email, timeout=1.5) for email in emails_to_score], return_exceptions=True)
            # Analyze sentiment in parallel if requested
            if include_sentiment:
                await asyncio.gather(*[analyze_sentiment_with_timeout(email, timeout=1.5) for email in emails_to_score], return_exceptions=True)
            # Check if emails need JIRA tickets (with longer timeout for better accuracy)
            await asyncio.gather(*[check_needs_jira_with_timeout(email, timeout=2.0) for email in emails_to_score], return_exceptions=True)
        
        # For remaining emails, set default priority scores and needs_jira flag
        for email in emails[10:]:
            if "priority_score" not in email:
                email["priority_score"] = {
                    "priority_score": 50,
                    "priority_level": "medium",
                    "urgency_score": 50,
                    "criticality_score": 50,
                    "waiting_for_us": False,
                    "blocked_on_us": False,
                    "factors": []
                }
            if "needs_jira" not in email:
                email["needs_jira"] = False
        
        summary = await email_integration.analyze_inbox(emails, ai_service)
        
        # Cache the result (including priority scores for faster subsequent loads)
        _inbox_cache[cache_key] = {
            "data": summary,
            "timestamp": time.time()
        }
        # Clean old cache entries (keep only last 10)
        if len(_inbox_cache) > 10:
                oldest_key = min(_inbox_cache.keys(), key=lambda k: _inbox_cache[k]["timestamp"])
                del _inbox_cache[oldest_key]
        
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


@router.post("/send", response_model=SendEmailResponse)
async def send_email(request: SendEmailRequest):
    """Send an email based on AI-generated response"""
    try:
        logger.info(f"[Email] Sending email to {', '.join(request.to)}")
        
        result = await email_integration.send_email(
            to=request.to,
            subject=request.subject,
            body=request.body,
            body_type=request.body_type,
            cc=request.cc,
            bcc=request.bcc,
            importance=request.importance
        )
        
        logger.info(f"[Email] Successfully sent email")
        return SendEmailResponse(**result)
    except ValueError as e:
        logger.error(f"[Email] Validation error sending email: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Email] Error sending email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")



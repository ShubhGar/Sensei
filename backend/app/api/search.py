"""
Global search API endpoint
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import List
import json
import logging

from app.database import get_db, MeetingSession, TodoItem
from app.models.schemas import SearchResponse, SearchResultItem
from app.integrations.email_integration import EmailIntegration
from app.integrations.teams_integration import TeamsIntegration

logger = logging.getLogger(__name__)
router = APIRouter()
email_integration = EmailIntegration()
teams_integration = TeamsIntegration()


def normalize_search_term(term: str) -> str:
    """Normalize search term for case-insensitive matching"""
    return term.lower().strip()


def highlight_snippet(text: str, search_term: str, max_length: int = 150) -> str:
    """Extract a snippet with the search term highlighted"""
    if not text:
        return ""
    
    normalized_text = text.lower()
    normalized_term = normalize_search_term(search_term)
    
    # Find the first occurrence
    idx = normalized_text.find(normalized_term)
    
    if idx == -1:
        # If not found, return beginning of text
        snippet = text[:max_length]
        if len(text) > max_length:
            snippet += "..."
        return snippet
    
    # Extract context around the match
    start = max(0, idx - 50)
    end = min(len(text), idx + len(search_term) + 50)
    
    snippet = text[start:end]
    
    # Add ellipsis if needed
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    
    return snippet


@router.get("/", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """
    Global search across meetings, todos, emails, and teams messages
    """
    try:
        search_term = normalize_search_term(q)
        results: List[SearchResultItem] = []
        
        # Search in Meeting Sessions
        try:
            meetings_query = select(MeetingSession).where(
                or_(
                    MeetingSession.title.ilike(f"%{q}%"),
                    MeetingSession.transcript.ilike(f"%{q}%"),
                    MeetingSession.full_transcript.ilike(f"%{q}%")
                )
            ).limit(limit)
            
            meetings_result = await db.execute(meetings_query)
            meetings = meetings_result.scalars().all()
            
            for meeting in meetings:
                # Check all text fields for matches
                searchable_text = f"{meeting.title or ''} {meeting.transcript or ''} {meeting.full_transcript or ''}"
                
                # Check JSON fields
                if meeting.mom:
                    try:
                        mom_data = json.loads(meeting.mom) if isinstance(meeting.mom, str) else meeting.mom
                        if isinstance(mom_data, dict):
                            # Extract text from MOM structure
                            summary = mom_data.get('summary', '')
                            key_points = ' '.join(mom_data.get('key_points', []))
                            decisions = ' '.join([d.get('decision', '') for d in mom_data.get('decisions', []) if isinstance(d, dict)])
                            action_items = ' '.join([a.get('task', '') for a in mom_data.get('action_items', []) if isinstance(a, dict)])
                            searchable_text += f" {summary} {key_points} {decisions} {action_items}"
                    except Exception as e:
                        logger.debug(f"Error parsing MOM JSON: {e}")
                        pass
                
                if meeting.faqs:
                    try:
                        faqs_data = json.loads(meeting.faqs) if isinstance(meeting.faqs, str) else meeting.faqs
                        if isinstance(faqs_data, list):
                            # Extract text from FAQs
                            faq_text = ' '.join([
                                f"{faq.get('question', '')} {faq.get('answer', '')}" 
                                for faq in faqs_data 
                                if isinstance(faq, dict)
                            ])
                            searchable_text += f" {faq_text}"
                    except Exception as e:
                        logger.debug(f"Error parsing FAQs JSON: {e}")
                        pass
                
                if search_term in searchable_text.lower():
                    snippet = highlight_snippet(
                        meeting.full_transcript or meeting.transcript or meeting.title or "",
                        q
                    )
                    
                    results.append(SearchResultItem(
                        type="meeting",
                        id=meeting.id,
                        title=meeting.title or "Untitled Meeting",
                        snippet=snippet,
                        metadata={
                            "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
                            "is_active": meeting.is_active
                        }
                    ))
        except Exception as e:
            logger.warning(f"Error searching meetings: {e}")
        
        # Search in Todo Items
        try:
            todos_query = select(TodoItem).where(
                or_(
                    TodoItem.title.ilike(f"%{q}%"),
                    TodoItem.description.ilike(f"%{q}%")
                )
            ).limit(limit)
            
            todos_result = await db.execute(todos_query)
            todos = todos_result.scalars().all()
            
            for todo in todos:
                snippet = highlight_snippet(
                    todo.description or todo.title or "",
                    q
                )
                
                results.append(SearchResultItem(
                    type="todo",
                    id=str(todo.id),
                    title=todo.title,
                    snippet=snippet,
                    metadata={
                        "priority": todo.priority,
                        "is_completed": todo.is_completed,
                        "source_type": todo.source_type
                    }
                ))
        except Exception as e:
            logger.warning(f"Error searching todos: {e}")
        
        # Search in Emails (from email integration)
        try:
            emails = await email_integration.get_outlook_inbox(max_results=100, unread_only=False)
            
            for email in emails:
                email_text = f"{email.get('subject', '')} {email.get('bodyPreview', '')} {email.get('body', {}).get('content', '') if isinstance(email.get('body'), dict) else email.get('body', '')}"
                
                if search_term in email_text.lower():
                    snippet = highlight_snippet(
                        email.get('bodyPreview') or email.get('subject', ''),
                        q
                    )
                    
                    results.append(SearchResultItem(
                        type="email",
                        id=email.get('id', ''),
                        title=email.get('subject', 'No Subject'),
                        snippet=snippet,
                        metadata={
                            "from": email.get('from', {}).get('emailAddress', {}).get('address', '') if isinstance(email.get('from'), dict) else '',
                            "receivedDateTime": email.get('receivedDateTime'),
                            "isRead": email.get('isRead', False)
                        }
                    ))
        except Exception as e:
            logger.warning(f"Error searching emails: {e}")
        
        # Search in Teams Messages (from teams integration)
        try:
            teams_messages = await teams_integration.get_chats(max_results=100)
            
            for message in teams_messages:
                message_text = f"{message.get('subject', '')} {message.get('body', {}).get('content', '') if isinstance(message.get('body'), dict) else message.get('body', '')}"
                
                if search_term in message_text.lower():
                    snippet = highlight_snippet(
                        message.get('body', {}).get('content', '') if isinstance(message.get('body'), dict) else message.get('body', '') or message.get('subject', ''),
                        q
                    )
                    
                    results.append(SearchResultItem(
                        type="teams",
                        id=message.get('id', ''),
                        title=message.get('subject') or message.get('topic') or 'Teams Message',
                        snippet=snippet,
                        metadata={
                            "from": message.get('from', {}).get('user', {}).get('displayName', '') if isinstance(message.get('from'), dict) else '',
                            "createdDateTime": message.get('createdDateTime')
                        }
                    ))
        except Exception as e:
            logger.warning(f"Error searching teams messages: {e}")
        
        # Limit total results
        results = results[:limit]
        
        logger.info(f"[Search] Query '{q}' returned {len(results)} results")
        
        return SearchResponse(
            query=q,
            total_results=len(results),
            results=results
        )
        
    except Exception as e:
        logger.error(f"[Search] Error searching: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


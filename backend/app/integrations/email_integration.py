"""
Email integration for Outlook
"""
import os
import re
import html
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
import httpx
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Import the token getter - avoid circular import by importing at function level


def clean_html(html_content: str) -> str:
    """Remove HTML tags and decode HTML entities from email content"""
    if not html_content:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_content)
    
    # Decode HTML entities using Python's built-in html.unescape
    try:
        text = html.unescape(text)
    except Exception:
        # Fallback to manual decoding if html.unescape fails
        html_entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&apos;': "'",
        }
        for entity, char in html_entities.items():
            text = text.replace(entity, char)
    
    # Clean up whitespace (preserve line breaks for readability)
    # First, normalize line breaks
    text = re.sub(r'\r\n|\r', '\n', text)
    # Collapse multiple spaces but preserve line breaks
    text = re.sub(r'[ \t]+', ' ', text)
    # Collapse multiple line breaks to max 2 (paragraph breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text


def extract_priority_from_text(text: str) -> Optional[str]:
    """Extract priority from email subject or body text"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Look for priority patterns like "critical Priority (1)", "medium Priority (2)", etc.
    # Check for explicit priority markers first (most reliable)
    if re.search(r'\bcritical\s+priority', text_lower) or re.search(r'priority\s*\(1\)', text_lower):
        return "high"  # Map to Microsoft's "high" importance
    elif re.search(r'\bmedium\s+priority', text_lower) or re.search(r'priority\s*\(2\)', text_lower):
        return "normal"
    elif re.search(r'\blow\s+priority', text_lower) or re.search(r'priority\s*\(3\)', text_lower):
        return "low"
    
    # Check for priority in subject line patterns (e.g., "critical Priority (1)" at start)
    # This handles cases where priority appears in the subject
    priority_match = re.search(r'^(critical|high|medium|low)\s+priority', text_lower)
    if priority_match:
        priority_word = priority_match.group(1)
        if priority_word in ['critical', 'high']:
            return "high"
        elif priority_word == 'medium':
            return "normal"
        elif priority_word == 'low':
            return "low"
    
    # Also check for standalone priority keywords in context
    if re.search(r'\b(critical|urgent|asap|immediate)\s+priority', text_lower):
        return "high"
    elif re.search(r'\b(low|minor|trivial)\s+priority', text_lower):
        return "low"
    
    return None


class EmailIntegration:
    """Email integration service for Outlook"""
    
    def __init__(self):
        self.microsoft_client_id = os.getenv("MICROSOFT_CLIENT_ID")
        self.microsoft_client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
        self.microsoft_tenant_id = os.getenv("MICROSOFT_TENANT_ID")
        self.microsoft_token = None
    
    async def authenticate_microsoft(self, auth_code: Optional[str] = None) -> bool:
        """Authenticate with Microsoft Graph API for Outlook (deprecated - use OAuth flow)"""
        # Try to get token from stored OAuth tokens
        from app.api.auth import get_microsoft_token
        token = await get_microsoft_token()
        if token:
            self.microsoft_token = token
            return True
        return False
    
    async def get_outlook_inbox(
        self,
        max_results: int = 50,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get Outlook inbox emails"""
        # Get token from stored OAuth tokens
        from app.api.auth import get_microsoft_token
        self.microsoft_token = await get_microsoft_token()
        
        if not self.microsoft_token:
            logger.warning("[Email] No authentication token available")
            return []
        
        try:
            url = "https://graph.microsoft.com/v1.0/me/mailfolders/inbox/messages"
            params = {
                "$top": max_results,
                "$orderby": "receivedDateTime desc",
                "$select": "id,subject,bodyPreview,body,from,receivedDateTime,isRead,importance,hasAttachments"
            }
            
            if unread_only:
                params["$filter"] = "isRead eq false"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {self.microsoft_token}"},
                    params=params,
                    timeout=10.0
                )
                
                # If we get an auth error, return empty list
                if response.status_code in [401, 403]:
                    logger.warning(f"[Email] API returned authentication error status {response.status_code}")
                    return []
                
                # For other errors, raise exception to be handled by caller
                if response.status_code in [404, 500, 502, 503]:
                    logger.error(f"[Email] API returned error status {response.status_code}")
                    response.raise_for_status()
                
                response.raise_for_status()
                data = response.json()
                
                emails = []
                for msg in data.get("value", []):
                    from_info = msg.get("from", {}).get("emailAddress", {})
                    body_content = msg.get("body", {})
                    subject = msg.get("subject", "")
                    raw_body = body_content.get("content", "") or msg.get("bodyPreview", "")
                    raw_preview = msg.get("bodyPreview", "")
                    
                    # Clean HTML from body and preview
                    clean_body = clean_html(raw_body)
                    clean_preview = clean_html(raw_preview) if raw_preview else clean_body[:500]
                    
                    # Get importance from Microsoft API
                    importance = msg.get("importance", "normal")
                    
                    # Try to extract priority from subject/body if importance is normal
                    if importance == "normal":
                        extracted_priority = extract_priority_from_text(subject + " " + clean_body)
                        if extracted_priority:
                            importance = extracted_priority
                    
                    emails.append({
                        "id": msg.get("id"),
                        "subject": subject,
                        "body": clean_body,
                        "body_preview": clean_preview,
                        "sender": from_info.get("name", ""),
                        "sender_email": from_info.get("address", ""),
                        "received_at": msg.get("receivedDateTime"),
                        "is_read": msg.get("isRead", False),
                        "importance": importance,
                        "has_attachments": msg.get("hasAttachments", False)
                    })
                
                # Return emails (even if empty - empty is a valid response)
                return emails
        except httpx.HTTPStatusError as e:
            logger.error(f"[Email] HTTP error fetching Outlook inbox: {e}")
            raise
        except Exception as e:
            logger.error(f"[Email] Error fetching Outlook inbox: {e}")
            raise
    
    async def analyze_inbox(
        self,
        emails: List[Dict[str, Any]],
        ai_service
    ) -> Dict[str, Any]:
        """Analyze inbox emails for urgency and categorization"""
        urgent_keywords = ["urgent", "asap", "immediate", "deadline", "action required", "important"]
        approval_keywords = ["approve", "approval", "sign", "review", "confirm"]
        
        urgent_emails = []
        pending_approvals = []
        
        for email in emails:
            content_lower = (email.get("subject", "") + " " + email.get("body", "")).lower()
            is_urgent = any(keyword in content_lower for keyword in urgent_keywords)
            needs_approval = any(keyword in content_lower for keyword in approval_keywords)
            
            if is_urgent:
                email["is_urgent"] = True
                urgent_emails.append(email)
            
            if needs_approval:
                email["needs_approval"] = True
                pending_approvals.append(email)
        
        # Generate mailbox summary using AI (but not individual email summaries)
        mailbox_summary = None
        if ai_service:
            try:
                mailbox_summary = await ai_service.summarize_mailbox(emails)
            except Exception as e:
                logger.warning(f"[Email] Error generating mailbox summary: {e}")
                # Fallback summary
                unread_count = sum(1 for e in emails if not e.get("is_read", True))
                urgent_count = len(urgent_emails)
                mailbox_summary = f"Your mailbox has {len(emails)} emails with {unread_count} unread messages. {urgent_count} urgent items require immediate attention."
        
        return {
            "total_emails": len(emails),
            "unread": sum(1 for e in emails if not e.get("is_read", True)),
            "urgent": len(urgent_emails),
            "pending_approvals": len(pending_approvals),
            "mailbox_summary": mailbox_summary,
            "emails": emails
        }

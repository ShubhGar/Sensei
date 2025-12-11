"""
Email integration for Outlook
"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
import httpx
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Import the token getter - avoid circular import by importing at function level


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
                    
                    emails.append({
                        "id": msg.get("id"),
                        "subject": msg.get("subject", ""),
                        "body": body_content.get("content", "") or msg.get("bodyPreview", ""),
                        "body_preview": msg.get("bodyPreview", ""),
                        "sender": from_info.get("name", ""),
                        "sender_email": from_info.get("address", ""),
                        "received_at": msg.get("receivedDateTime"),
                        "is_read": msg.get("isRead", False),
                        "importance": msg.get("importance", "normal"),
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
            
            # Generate summaries for unread emails
            if not email.get("is_read", True) and ai_service:
                email_content = f"{email.get('subject', '')} {email.get('body_preview', '')}"
                email["summary"] = await ai_service.summarize_email(email_content)
        
        # Generate mailbox summary using AI
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

"""
Microsoft Teams integration
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


class TeamsIntegration:
    """Microsoft Teams integration service"""
    
    def __init__(self):
        self.client_id = os.getenv("MICROSOFT_CLIENT_ID")
        self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
        self.tenant_id = os.getenv("MICROSOFT_TENANT_ID")
        self.token = None
    
    async def authenticate(self, auth_code: Optional[str] = None) -> bool:
        """Authenticate with Microsoft Graph API for Teams (deprecated - use OAuth flow)"""
        # Try to get token from stored OAuth tokens
        from app.api.auth import get_microsoft_token
        token = await get_microsoft_token()
        if token:
            self.token = token
            return True
        return False
    
    async def get_chats(self, max_results: int = 50) -> Dict[str, Any]:
        """Get Teams chat messages
        
        Returns:
            Dict with 'messages' list and optional 'error' and 'error_type' fields
        """
        # Get token from stored OAuth tokens
        from app.api.auth import get_microsoft_token
        self.token = await get_microsoft_token()
        
        if not self.token:
            logger.warning("[Teams] No authentication token available")
            return {
                "messages": [],
                "error": "No authentication token found. Please set a token from Microsoft Graph Explorer.",
                "error_type": "auth"
            }
        
        try:
            url = "https://graph.microsoft.com/v1.0/me/chats"
            params = {"$top": max_results}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {self.token}"},
                    params=params,
                    timeout=10.0
                )
                
                # Log response details for debugging
                if response.status_code != 200:
                    error_body = response.text
                    logger.error(f"[Teams] API returned error status {response.status_code}: {error_body}")
                
                # If we get an auth error, return error info
                if response.status_code in [401, 403]:
                    error_body = response.text
                    logger.warning(f"[Teams] API returned authentication error status {response.status_code}: {error_body}")
                    
                    error_type = "permission" if response.status_code == 403 else "auth"
                    error_msg = "Token expired or invalid. Please refresh your token from Microsoft Graph Explorer."
                    if response.status_code == 403:
                        error_msg = "Missing required permissions. Please grant Chat.Read and Chat.ReadWrite permissions in Graph Explorer."
                    
                    return {
                        "messages": [],
                        "error": error_msg,
                        "error_type": error_type,
                        "api_error": error_body
                    }
                
                # For other errors, raise exception to be handled by caller
                if response.status_code in [404, 500, 502, 503]:
                    logger.error(f"[Teams] API returned error status {response.status_code}")
                    response.raise_for_status()
                
                response.raise_for_status()
                data = response.json()
                
                # Log if we got empty results
                if not data.get("value"):
                    logger.info("[Teams] API returned empty chats list")
                    return {
                        "messages": [],
                        "error": "No Teams chats found. You may not have any active chats.",
                        "error_type": "empty"
                    }
                
                # Get current user info to determine if message is from self
                current_user_email = None
                try:
                    user_response = await client.get(
                        "https://graph.microsoft.com/v1.0/me",
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=5.0
                    )
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        current_user_email = user_data.get("mail") or user_data.get("userPrincipalName")
                        logger.info(f"[Teams] Current user: {current_user_email}")
                except Exception as e:
                    logger.warning(f"[Teams] Could not get current user info: {e}")
                
                chats = []
                for chat in data.get("value", []):
                    # Get messages for each chat
                    chat_id = chat.get("id")
                    unread_count = chat.get("unreadCount", 0)
                    messages_url = f"https://graph.microsoft.com/v1.0/me/chats/{chat_id}/messages"
                    
                    messages_response = await client.get(
                        messages_url,
                        headers={"Authorization": f"Bearer {self.token}"},
                        params={"$top": 10, "$orderby": "lastModifiedDateTime desc"}
                    )
                    
                    if messages_response.status_code == 200:
                        messages_data = messages_response.json()
                        messages_list = messages_data.get("value", [])
                        logger.info(f"[Teams] Retrieved {len(messages_list)} messages from chat {chat_id} (unread: {unread_count})")
                        
                        # Determine read status: mark oldest messages as read if unread_count is less than total
                        for idx, msg in enumerate(messages_list):
                            sender_info = msg.get("from", {}).get("user", {})
                            sender_email = sender_info.get("mail") or sender_info.get("userPrincipalName") or sender_info.get("id")
                            
                            # Check if message is from current user
                            is_from_self = False
                            if current_user_email and sender_email:
                                # Compare emails directly or check if they match
                                is_from_self = (sender_email.lower() == current_user_email.lower() or 
                                               sender_email.lower().endswith("@" + current_user_email.split("@")[-1]))
                            
                            # If message is from self, it's read
                            # Otherwise, mark as unread if it's in the most recent unread_count messages
                            is_read = is_from_self or (idx >= unread_count)
                            
                            chats.append({
                                "chat_id": chat_id,
                                "message_id": msg.get("id"),
                                "sender": msg.get("from", {}).get("user", {}).get("displayName", ""),
                                "content": msg.get("body", {}).get("content", ""),
                                "sent_at": msg.get("createdDateTime"),
                                "is_read": is_read
                            })
                    else:
                        logger.warning(f"[Teams] Failed to get messages for chat {chat_id}: status {messages_response.status_code}")
                
                # Log summary
                logger.info(f"[Teams] Retrieved {len(chats)} total messages from {len(data.get('value', []))} chats")
                
                # Return chats with success indicator
                if len(chats) == 0:
                    return {
                        "messages": [],
                        "error": "No messages found in your Teams chats.",
                        "error_type": "empty"
                    }
                
                return {
                    "messages": chats,
                    "error": None,
                    "error_type": None
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"[Teams] HTTP error fetching Teams chats: {e}")
            return {
                "messages": [],
                "error": f"HTTP error: {str(e)}",
                "error_type": "api"
            }
        except Exception as e:
            logger.error(f"[Teams] Error fetching Teams chats: {e}")
            return {
                "messages": [],
                "error": f"Error fetching Teams chats: {str(e)}",
                "error_type": "api"
            }
    
    async def get_joined_teams(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """Get Teams the user is a member of"""
        # Get token from stored OAuth tokens
        from app.api.auth import get_microsoft_token
        self.token = await get_microsoft_token()
        
        if not self.token:
            logger.warning("[Teams] No authentication token available")
            return []
        
        try:
            url = "https://graph.microsoft.com/v1.0/me/joinedTeams"
            params = {"$top": max_results}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {self.token}"},
                    params=params,
                    timeout=10.0
                )
                
                # Log response details for debugging
                if response.status_code != 200:
                    error_body = response.text
                    logger.error(f"[Teams] API returned error status {response.status_code}: {error_body}")
                
                # If we get an auth error, log details and return empty list
                if response.status_code in [401, 403]:
                    error_body = response.text
                    logger.warning(f"[Teams] API returned authentication error status {response.status_code}: {error_body}")
                    logger.warning("[Teams] This might be due to missing permissions. Required: Team.ReadBasic.All or TeamMember.Read.All")
                    return []
                
                # For other errors, raise exception to be handled by caller
                if response.status_code in [404, 500, 502, 503]:
                    logger.error(f"[Teams] API returned error status {response.status_code}")
                    response.raise_for_status()
                
                response.raise_for_status()
                data = response.json()
                
                # Log if we got empty results
                if not data.get("value"):
                    logger.info("[Teams] API returned empty teams list")
                
                teams = []
                for team in data.get("value", []):
                    teams.append({
                        "id": team.get("id"),
                        "displayName": team.get("displayName", ""),
                        "description": team.get("description", ""),
                        "internalId": team.get("internalId"),
                        "visibility": team.get("visibility"),
                    })
                
                logger.info(f"[Teams] Retrieved {len(teams)} joined teams")
                
                return teams
        except httpx.HTTPStatusError as e:
            logger.error(f"[Teams] HTTP error fetching joined teams: {e}")
            raise
        except Exception as e:
            logger.error(f"[Teams] Error fetching joined teams: {e}")
            raise
    
    async def get_team_channels(
        self,
        team_id: str,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Get channels in a Team"""
        # Get token from stored OAuth tokens
        from app.api.auth import get_microsoft_token
        self.token = await get_microsoft_token()
        
        if not self.token:
            logger.warning("[Teams] No authentication token available")
            return []
        
        try:
            url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels"
            params = {"$top": max_results}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {self.token}"},
                    params=params,
                    timeout=10.0
                )
                
                # Log response details for debugging
                if response.status_code != 200:
                    error_body = response.text
                    logger.error(f"[Teams] API returned error status {response.status_code}: {error_body}")
                
                # If we get an auth error, log details and return empty list
                if response.status_code in [401, 403]:
                    error_body = response.text
                    logger.warning(f"[Teams] API returned authentication error status {response.status_code}: {error_body}")
                    logger.warning("[Teams] This might be due to missing permissions. Required: Channel.ReadBasic.All or Channel.Read.All")
                    return []
                
                # For other errors, raise exception to be handled by caller
                if response.status_code in [404, 500, 502, 503]:
                    logger.error(f"[Teams] API returned error status {response.status_code}")
                    response.raise_for_status()
                
                response.raise_for_status()
                data = response.json()
                
                # Log if we got empty results
                if not data.get("value"):
                    logger.info(f"[Teams] API returned empty channels list for team {team_id}")
                
                channels = []
                for channel in data.get("value", []):
                    channels.append({
                        "id": channel.get("id"),
                        "displayName": channel.get("displayName", ""),
                        "description": channel.get("description", ""),
                        "email": channel.get("email"),
                        "webUrl": channel.get("webUrl"),
                        "membershipType": channel.get("membershipType"),
                        "createdDateTime": channel.get("createdDateTime"),
                    })
                
                logger.info(f"[Teams] Retrieved {len(channels)} channels from team {team_id}")
                
                return channels
        except httpx.HTTPStatusError as e:
            logger.error(f"[Teams] HTTP error fetching team channels: {e}")
            raise
        except Exception as e:
            logger.error(f"[Teams] Error fetching team channels: {e}")
            raise
    
    async def get_channel_messages(
        self,
        team_id: str,
        channel_id: str,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Get Teams channel messages"""
        # Get token from stored OAuth tokens
        from app.api.auth import get_microsoft_token
        self.token = await get_microsoft_token()
        
        if not self.token:
            logger.warning("[Teams] No authentication token available")
            return []
        
        try:
            url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
            params = {"$top": max_results, "$orderby": "lastModifiedDateTime desc"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {self.token}"},
                    params=params,
                    timeout=10.0
                )
                
                # Log response details for debugging
                if response.status_code != 200:
                    error_body = response.text
                    logger.error(f"[Teams] API returned error status {response.status_code}: {error_body}")
                
                # If we get an auth error, log details and return empty list
                if response.status_code in [401, 403]:
                    error_body = response.text
                    logger.warning(f"[Teams] API returned authentication error status {response.status_code}: {error_body}")
                    logger.warning("[Teams] This might be due to missing permissions. Required: ChannelMessage.Read.All")
                    return []
                
                # For other errors, raise exception to be handled by caller
                if response.status_code in [404, 500, 502, 503]:
                    logger.error(f"[Teams] API returned error status {response.status_code}")
                    response.raise_for_status()
                
                response.raise_for_status()
                data = response.json()
                
                # Log if we got empty results
                if not data.get("value"):
                    logger.info("[Teams] API returned empty channel messages list")
                
                # Get current user info to determine if message is from self
                current_user_email = None
                try:
                    user_response = await client.get(
                        "https://graph.microsoft.com/v1.0/me",
                        headers={"Authorization": f"Bearer {self.token}"},
                        timeout=5.0
                    )
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        current_user_email = user_data.get("mail") or user_data.get("userPrincipalName")
                        logger.info(f"[Teams] Current user: {current_user_email}")
                except Exception as e:
                    logger.warning(f"[Teams] Could not get current user info: {e}")
                
                messages = []
                for msg in data.get("value", []):
                    sender_info = msg.get("from", {}).get("user", {})
                    sender_email = sender_info.get("mail") or sender_info.get("userPrincipalName") or sender_info.get("id")
                    
                    # Check if message is from current user
                    is_from_self = False
                    if current_user_email and sender_email:
                        # Compare emails directly or check if they match
                        is_from_self = (sender_email.lower() == current_user_email.lower() or 
                                       sender_email.lower().endswith("@" + current_user_email.split("@")[-1]))
                    
                    # For channel messages, mark as read if from self, otherwise assume unread for recent messages
                    # Channel messages don't have direct read status, so we'll mark recent non-self messages as unread
                    is_read = is_from_self
                    
                    messages.append({
                        "message_id": msg.get("id"),
                        "channel_id": channel_id,
                        "sender": msg.get("from", {}).get("user", {}).get("displayName", ""),
                        "content": msg.get("body", {}).get("content", ""),
                        "sent_at": msg.get("createdDateTime"),
                        "is_reply": "replyToId" in msg,
                        "is_read": is_read
                    })
                
                logger.info(f"[Teams] Retrieved {len(messages)} messages from channel {channel_id}")
                
                # Return messages (even if empty - empty is a valid response)
                return messages
        except httpx.HTTPStatusError as e:
            logger.error(f"[Teams] HTTP error fetching channel messages: {e}")
            raise
        except Exception as e:
            logger.error(f"[Teams] Error fetching channel messages: {e}")
            raise
    
    async def analyze_messages(
        self,
        messages: List[Dict[str, Any]],
        ai_service
    ) -> Dict[str, Any]:
        """Analyze Teams messages for urgency and action items"""
        urgent_keywords = ["urgent", "asap", "immediate", "deadline", "action", "blocking"]
        
        urgent_messages = []
        
        for msg in messages:
            content_lower = msg.get("content", "").lower()
            is_urgent = any(keyword in content_lower for keyword in urgent_keywords)
            
            if is_urgent:
                msg["is_urgent"] = True
                urgent_messages.append(msg)
        
        # Generate summaries
        for msg in messages[:10]:
            if ai_service:
                msg["summary"] = await ai_service.summarize_email(msg.get("content", "")[:500])
        
        # Generate Teams summary using AI
        teams_summary = None
        if ai_service:
            try:
                teams_summary = await ai_service.summarize_teams(messages)
            except Exception as e:
                logger.warning(f"[Teams] Error generating Teams summary: {e}")
                # Fallback summary
                unread_count = sum(1 for m in messages if not m.get("is_read", True))
                urgent_count = len(urgent_messages)
                teams_summary = f"Your Teams has {len(messages)} messages with {unread_count} unread. {urgent_count} urgent items require immediate attention."
        
        return {
            "total_messages": len(messages),
            "unread": sum(1 for m in messages if not m.get("is_read", True)),
            "urgent": len(urgent_messages),
            "teams_summary": teams_summary,
            "messages": messages
        }






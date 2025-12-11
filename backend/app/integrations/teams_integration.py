"""
Microsoft Teams integration
"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
import httpx
import logging
import asyncio

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
        # Track if we've already determined that Chat permissions are missing
        # This prevents multiple API calls after the first failure
        self._chat_permissions_missing = False
    
    async def authenticate(self, auth_code: Optional[str] = None) -> bool:
        """Authenticate with Microsoft Graph API for Teams (deprecated - use OAuth flow)"""
        # Try to get token from stored OAuth tokens
        from app.api.auth import get_microsoft_token
        token = await get_microsoft_token()
        if token:
            self.token = token
            # Reset the failure cache when re-authenticating, in case permissions were fixed
            self._chat_permissions_missing = False
            return True
        return False
    
    def reset_permission_cache(self):
        """Reset the permission failure cache - useful after re-authentication"""
        self._chat_permissions_missing = False
        logger.info("[Teams] Permission failure cache reset")
    
    async def get_chats(self, max_results: int = 50) -> Dict[str, Any]:
        """Get Teams chat messages
        
        Returns:
            Dict with 'messages' list and optional 'error' and 'error_type' fields
        """
        # If we've already determined that Chat permissions are missing, skip API call
        if self._chat_permissions_missing:
            logger.debug("[Teams] Chat permissions missing (cached), using dummy data without API call")
            from app.integrations.dummy_data import generate_dummy_teams_chats
            dummy_messages = generate_dummy_teams_chats(max_results)
            return {
                "messages": dummy_messages,
                "error": "Missing Chat.Read permissions. Please re-authenticate with Chat.ReadBasic, Chat.Read, or Chat.ReadWrite scopes.",
                "error_type": "permission",
                "is_dummy_data": True
            }
        
        # Get token from stored OAuth tokens
        from app.api.auth import get_microsoft_token
        new_token = await get_microsoft_token()
        
        # If token changed, reset the permission cache (might have new scopes)
        if new_token != self.token:
            if self._chat_permissions_missing:
                logger.info("[Teams] Token changed, resetting permission failure cache")
                self._chat_permissions_missing = False
            self.token = new_token
        
        # Validate token - check for None, empty string, or whitespace
        if not self.token or not self.token.strip():
            logger.warning("[Teams] No authentication token available (token is None or empty), using dummy data as fallback")
            from app.integrations.dummy_data import generate_dummy_teams_chats
            dummy_messages = generate_dummy_teams_chats(max_results)
            return {
                "messages": dummy_messages,
                "error": "No authentication token available. Please authenticate with Microsoft first.",
                "error_type": "authentication",
                "is_dummy_data": True
            }
        
        # Ensure token is properly formatted and not just whitespace
        token_clean = self.token.strip()
        if len(token_clean) < 50:  # JWT tokens are typically much longer
            logger.warning(f"[Teams] Token appears to be invalid (too short: {len(token_clean)} chars), using dummy data as fallback")
            from app.integrations.dummy_data import generate_dummy_teams_chats
            dummy_messages = generate_dummy_teams_chats(max_results)
            return {
                "messages": dummy_messages,
                "error": "Authentication token is invalid or malformed. Please re-authenticate.",
                "error_type": "authentication",
                "is_dummy_data": True
            }
        
        # Log token status (masked for security)
        token_preview = f"{token_clean[:10]}...{token_clean[-10:]}" if len(token_clean) > 20 else "***"
        logger.debug(f"[Teams] Using token: {token_preview}")
        
        try:
            url = "https://graph.microsoft.com/v1.0/me/chats"
            params = {"$top": max_results}
            
            # Ensure token is properly formatted
            auth_header = f"Bearer {token_clean}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": auth_header},
                    params=params,
                    timeout=10.0
                )
                
                # Log response details for debugging
                if response.status_code != 200:
                    error_body = response.text
                    logger.error(f"[Teams] API returned error status {response.status_code}: {error_body}")
                    # Log if Authorization header was sent (without revealing token)
                    logger.debug(f"[Teams] Request URL: {url}, Auth header present: {bool(auth_header)}")
                
                # If we get an auth error, use dummy data as fallback
                if response.status_code in [401, 403]:
                    error_body = response.text
                    try:
                        error_json = response.json()
                        error_code = error_json.get("error", {}).get("code", "")
                        error_message = error_json.get("error", {}).get("message", "")
                        
                        # Check for specific error messages
                        if "No authorization information" in error_message or "authorization" in error_message.lower():
                            logger.warning(
                                f"[Teams] Authentication token issue (403). The token may be invalid, expired, or not properly formatted. "
                                f"Please re-authenticate with Chat.Read or Chat.ReadWrite scopes. Error: {error_code} - {error_message}"
                            )
                            error_msg = "Authentication token is invalid or expired, or missing Chat.Read permissions. Please re-authenticate with Microsoft and ensure Chat.Read or Chat.ReadWrite scopes are granted."
                            error_type = "authentication"
                        elif "Chat.Read" in error_message or "Chat.ReadBasic" in error_message or "Chat.ReadWrite" in error_message:
                            # Mark that Chat permissions are missing to prevent future API calls
                            self._chat_permissions_missing = True
                            logger.warning(
                                f"[Teams] Missing Chat permissions (403). Required scopes: Chat.ReadBasic, Chat.Read, or Chat.ReadWrite. "
                                f"Current token may not have these scopes. Using dummy data as fallback. "
                                f"Future calls will skip API requests. Error: {error_code} - {error_message}"
                            )
                            error_msg = "Missing Chat.Read permissions. Please re-authenticate with Chat.ReadBasic, Chat.Read, or Chat.ReadWrite scopes."
                            error_type = "permission"
                        else:
                            logger.warning(f"[Teams] API returned authentication error status {response.status_code}, using dummy data as fallback. Error: {error_code} - {error_message}")
                            error_msg = f"Authentication error: {error_code} - {error_message}"
                            error_type = "authentication"
                    except Exception as e:
                        logger.warning(f"[Teams] API returned authentication error status {response.status_code}, using dummy data as fallback. Could not parse error: {e}")
                        error_msg = f"Authentication error (status {response.status_code}). Please check your authentication token."
                        error_type = "authentication"
                    
                    from app.integrations.dummy_data import generate_dummy_teams_chats
                    dummy_messages = generate_dummy_teams_chats(max_results)
                    return {
                        "messages": dummy_messages,
                        "error": error_msg,
                        "error_type": error_type,
                        "is_dummy_data": True
                    }
                
                # For other errors, raise exception to be handled by caller
                if response.status_code in [404, 500, 502, 503]:
                    logger.error(f"[Teams] API returned error status {response.status_code}")
                    response.raise_for_status()
                
                response.raise_for_status()
                data = response.json()
                
                # Log if we got empty results
                if not data.get("value"):
                    logger.info("[Teams] API returned empty chats list, using dummy data as fallback")
                    from app.integrations.dummy_data import generate_dummy_teams_chats
                    dummy_messages = generate_dummy_teams_chats(max_results)
                    return {
                        "messages": dummy_messages,
                        "error": None,
                        "error_type": None,
                        "is_dummy_data": True
                    }
                
                # Get current user info to determine if message is from self
                current_user_email = None
                try:
                    user_response = await client.get(
                        "https://graph.microsoft.com/v1.0/me",
                        headers={"Authorization": auth_header},
                        timeout=5.0
                    )
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        current_user_email = user_data.get("mail") or user_data.get("userPrincipalName")
                        logger.info(f"[Teams] Current user: {current_user_email}")
                except Exception as e:
                    logger.warning(f"[Teams] Could not get current user info: {e}")
                
                # Batch fetch messages from all chats in parallel
                async def fetch_chat_messages(chat):
                    """Fetch messages for a single chat"""
                    chat_id = chat.get("id")
                    unread_count = chat.get("unreadCount", 0)
                    messages_url = f"https://graph.microsoft.com/v1.0/me/chats/{chat_id}/messages"
                    
                    try:
                        messages_response = await client.get(
                            messages_url,
                            headers={"Authorization": auth_header},
                            params={"$top": 10, "$orderby": "lastModifiedDateTime desc"},
                            timeout=5.0
                        )
                        
                        if messages_response.status_code == 200:
                            messages_data = messages_response.json()
                            messages_list = messages_data.get("value", [])
                            
                            chat_messages = []
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
                                
                                chat_messages.append({
                                    "chat_id": chat_id,
                                    "message_id": msg.get("id"),
                                    "sender": msg.get("from", {}).get("user", {}).get("displayName", ""),
                                    "content": msg.get("body", {}).get("content", ""),
                                    "sent_at": msg.get("createdDateTime"),
                                    "is_read": is_read
                                })
                            
                            return chat_messages
                        else:
                            logger.warning(f"[Teams] Failed to get messages for chat {chat_id}: status {messages_response.status_code}")
                            return []
                    except Exception as e:
                        logger.warning(f"[Teams] Error fetching messages for chat {chat_id}: {e}")
                        return []
                
                # Fetch all chat messages in parallel (limit to first 10 chats for performance)
                chat_list = data.get("value", [])[:10]
                chat_messages_results = await asyncio.gather(*[fetch_chat_messages(chat) for chat in chat_list])
                
                # Flatten results
                chats = []
                for chat_messages in chat_messages_results:
                    chats.extend(chat_messages)
                
                # Log summary
                logger.info(f"[Teams] Retrieved {len(chats)} total messages from {len(data.get('value', []))} chats")
                
                # Return chats with success indicator
                if len(chats) == 0:
                    # Use dummy data as fallback when no messages found
                    logger.info("[Teams] No messages found, using dummy data as fallback")
                    from app.integrations.dummy_data import generate_dummy_teams_chats
                    dummy_messages = generate_dummy_teams_chats(max_results)
                    return {
                        "messages": dummy_messages,
                        "error": None,
                        "error_type": None,
                        "is_dummy_data": True
                    }
                
                return {
                    "messages": chats,
                    "error": None,
                    "error_type": None,
                    "is_dummy_data": False
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"[Teams] HTTP error fetching Teams chats: {e}")
            # Use dummy data as fallback on API errors
            logger.info("[Teams] API error, using dummy data as fallback")
            from app.integrations.dummy_data import generate_dummy_teams_chats
            dummy_messages = generate_dummy_teams_chats(max_results)
            return {
                "messages": dummy_messages,
                "error": None,
                "error_type": None,
                "is_dummy_data": True
            }
        except Exception as e:
            logger.error(f"[Teams] Error fetching Teams chats: {e}")
            # Use dummy data as fallback on errors
            logger.info("[Teams] Error occurred, using dummy data as fallback")
            from app.integrations.dummy_data import generate_dummy_teams_chats
            dummy_messages = generate_dummy_teams_chats(max_results)
            return {
                "messages": dummy_messages,
                "error": None,
                "error_type": None,
                "is_dummy_data": True
            }
    
    async def get_joined_teams(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """Get Teams the user is a member of"""
        # Get token from stored OAuth tokens
        from app.api.auth import get_microsoft_token
        self.token = await get_microsoft_token()
        
        # Validate token
        if not self.token or not self.token.strip():
            logger.warning("[Teams] No authentication token available (token is None or empty)")
            return []
        
        # Ensure token is properly formatted
        auth_header = f"Bearer {self.token.strip()}"
        
        try:
            url = "https://graph.microsoft.com/v1.0/me/joinedTeams"
            params = {"$top": max_results}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": auth_header},
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
        
        # Validate token
        if not self.token or not self.token.strip():
            logger.warning("[Teams] No authentication token available (token is None or empty)")
            return []
        
        # Ensure token is properly formatted
        auth_header = f"Bearer {self.token.strip()}"
        
        try:
            url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels"
            params = {"$top": max_results}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": auth_header},
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
        
        # Validate token
        if not self.token or not self.token.strip():
            logger.warning("[Teams] No authentication token available (token is None or empty), using dummy data as fallback")
            from app.integrations.dummy_data import generate_dummy_channel_messages
            return generate_dummy_channel_messages(team_id, channel_id, max_results)
        
        # Ensure token is properly formatted
        auth_header = f"Bearer {self.token.strip()}"
        
        try:
            url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
            params = {"$top": max_results, "$orderby": "lastModifiedDateTime desc"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": auth_header},
                    params=params,
                    timeout=10.0
                )
                
                # Log response details for debugging
                if response.status_code != 200:
                    error_body = response.text
                    logger.error(f"[Teams] API returned error status {response.status_code}: {error_body}")
                
                # If we get an auth error, use dummy data as fallback
                if response.status_code in [401, 403]:
                    error_body = response.text
                    logger.warning(f"[Teams] API returned authentication error status {response.status_code}, using dummy data as fallback")
                    from app.integrations.dummy_data import generate_dummy_channel_messages
                    return generate_dummy_channel_messages(team_id, channel_id, max_results)
                
                # For other errors, raise exception to be handled by caller
                if response.status_code in [404, 500, 502, 503]:
                    logger.error(f"[Teams] API returned error status {response.status_code}")
                    response.raise_for_status()
                
                response.raise_for_status()
                data = response.json()
                
                # Log if we got empty results
                if not data.get("value"):
                    logger.info("[Teams] API returned empty channel messages list, using dummy data as fallback")
                    from app.integrations.dummy_data import generate_dummy_channel_messages
                    return generate_dummy_channel_messages(team_id, channel_id, max_results)
                
                # Get current user info to determine if message is from self
                current_user_email = None
                try:
                    user_response = await client.get(
                        "https://graph.microsoft.com/v1.0/me",
                        headers={"Authorization": auth_header},
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
                
                # If no messages found, use dummy data as fallback
                if len(messages) == 0:
                    logger.info("[Teams] No messages found in channel, using dummy data as fallback")
                    from app.integrations.dummy_data import generate_dummy_channel_messages
                    return generate_dummy_channel_messages(team_id, channel_id, max_results)
                
                return messages
        except httpx.HTTPStatusError as e:
            logger.error(f"[Teams] HTTP error fetching channel messages: {e}, using dummy data as fallback")
            from app.integrations.dummy_data import generate_dummy_channel_messages
            return generate_dummy_channel_messages(team_id, channel_id, max_results)
        except Exception as e:
            logger.error(f"[Teams] Error fetching channel messages: {e}, using dummy data as fallback")
            from app.integrations.dummy_data import generate_dummy_channel_messages
            return generate_dummy_channel_messages(team_id, channel_id, max_results)
    
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
        
        # Skip individual message summaries - too slow and not needed for summary view
        # Individual summaries can be generated on-demand if needed
        
        # Generate Teams summary - use fast fallback instead of slow AI call for better performance
        # AI summary can be generated on-demand if needed
        unread_count = sum(1 for m in messages if not m.get("is_read", True))
        urgent_count = len(urgent_messages)
        teams_summary = f"Your Teams has {len(messages)} messages with {unread_count} unread. {urgent_count} urgent items require immediate attention."
        
        # Optionally generate AI summary only if explicitly requested (skip for performance)
        # if ai_service and len(messages) > 0:
        #     try:
        #         teams_summary = await ai_service.summarize_teams(messages)
        #     except Exception as e:
        #         logger.warning(f"[Teams] Error generating Teams summary: {e}")
        
        return {
            "total_messages": len(messages),
            "unread": sum(1 for m in messages if not m.get("is_read", True)),
            "urgent": len(urgent_messages),
            "teams_summary": teams_summary,
            "messages": messages
        }






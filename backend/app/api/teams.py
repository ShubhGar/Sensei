"""
Teams API routes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.models.schemas import TeamsSummary
from app.integrations.teams_integration import TeamsIntegration
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)
router = APIRouter()
teams_integration = TeamsIntegration()
ai_service = AIService()


@router.get("/messages", response_model=TeamsSummary)
async def get_messages(
    max_results: int = Query(50, ge=1, le=100),
    chat_type: str = Query("chats", description="Type: 'chats' or 'channels'"),
    team_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None)
):
    """Get Teams messages with AI analysis"""
    try:
        logger.info(f"[Teams] Getting messages - chat_type: {chat_type}, max_results: {max_results}, team_id: {team_id}, channel_id: {channel_id}")
        
        result = None
        if chat_type == "chats":
            result = await teams_integration.get_chats(max_results)
        elif chat_type == "channels":
            if not team_id or not channel_id:
                logger.warning(f"[Teams] Missing team_id/channel_id for channels - team_id: {team_id}, channel_id: {channel_id}")
                raise HTTPException(
                    status_code=400,
                    detail="team_id and channel_id are required when chat_type is 'channels'"
                )
            else:
                # get_channel_messages still returns a list, so wrap it
                messages_list = await teams_integration.get_channel_messages(team_id, channel_id, max_results)
                result = {
                    "messages": messages_list,
                    "error": None if messages_list else "No messages found in channel.",
                    "error_type": "empty" if not messages_list else None
                }
        else:
            logger.warning(f"[Teams] Invalid chat_type: {chat_type}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid chat_type '{chat_type}'. Must be 'chats' or 'channels'"
            )
        
        # Extract messages and error info from result
        messages = result.get("messages", [])
        error = result.get("error")
        error_type = result.get("error_type")
        
        # If there's an error, return it in the summary
        if error:
            logger.info(f"[Teams] Error or empty result - error_type: {error_type}, error: {error}")
            return TeamsSummary(
                total_messages=0,
                unread=0,
                urgent=0,
                teams_summary=error,
                messages=[],
                error=error,
                error_type=error_type
            )
        
        # If no messages but no error, it's just empty
        if not messages:
            logger.info("[Teams] No messages found - returning empty summary")
            return TeamsSummary(
                total_messages=0,
                unread=0,
                urgent=0,
                teams_summary="No Teams messages found.",
                messages=[],
                error=None,
                error_type="empty"
            )
        
        # Analyze messages if we have them
        summary = await teams_integration.analyze_messages(messages, ai_service)
        summary["error"] = None
        summary["error_type"] = None
        
        logger.info(f"[Teams] Successfully retrieved {len(messages)} messages")
        return TeamsSummary(**summary)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Teams] Error fetching messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching Teams messages: {str(e)}")


@router.get("/joined")
async def get_joined_teams(
    max_results: int = Query(100, ge=1, le=500)
):
    """Get Teams the user is a member of"""
    try:
        logger.info(f"[Teams] Getting joined teams - max_results: {max_results}")
        
        teams = await teams_integration.get_joined_teams(max_results)
        
        logger.info(f"[Teams] Successfully retrieved {len(teams)} teams")
        return {"teams": teams, "total": len(teams)}
    except Exception as e:
        logger.error(f"[Teams] Error fetching joined teams: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching joined teams: {str(e)}")


@router.get("/{team_id}/channels")
async def get_team_channels(
    team_id: str,
    max_results: int = Query(100, ge=1, le=500)
):
    """Get channels in a Team"""
    try:
        logger.info(f"[Teams] Getting channels for team {team_id} - max_results: {max_results}")
        
        channels = await teams_integration.get_team_channels(team_id, max_results)
        
        logger.info(f"[Teams] Successfully retrieved {len(channels)} channels")
        return {"channels": channels, "team_id": team_id, "total": len(channels)}
    except Exception as e:
        logger.error(f"[Teams] Error fetching team channels: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching team channels: {str(e)}")


@router.post("/authenticate")
async def authenticate_teams(auth_code: Optional[str] = None):
    """Authenticate with Microsoft Teams"""
    try:
        success = await teams_integration.authenticate(auth_code)
        
        if success:
            return {"status": "authenticated", "provider": "teams"}
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")



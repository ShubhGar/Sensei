"""
Microsoft OAuth authentication API routes
"""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from typing import Optional
import logging
import os
import secrets
import base64
import hashlib
from urllib.parse import urlencode
from datetime import datetime, timedelta
from dotenv import load_dotenv
import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, MicrosoftAuth
from app.models.schemas import TokenInput

load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter()

# Microsoft OAuth configuration
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")
REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:8000/api/auth/microsoft/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Required scopes for Outlook and Teams
SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Chat.Read",
    "https://graph.microsoft.com/Chat.ReadWrite",
    "https://graph.microsoft.com/ChannelMessage.Read.All",
    "https://graph.microsoft.com/User.Read",
    "offline_access"
]


def generate_pkce():
    """Generate PKCE code verifier and challenge"""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge


@router.get("/auth/microsoft/login")
async def microsoft_login():
    """Generate Microsoft OAuth login URL"""
    if not MICROSOFT_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Microsoft OAuth not configured. Please set MICROSOFT_CLIENT_ID in environment variables."
        )
    
    # Generate PKCE parameters
    code_verifier, code_challenge = generate_pkce()
    
    # Store code_verifier in session (for production, use proper session storage)
    # For now, we'll pass it in state parameter (not ideal but works for demo)
    state = base64.urlsafe_b64encode(f"{code_verifier}".encode()).decode()
    
    # Build authorization URL
    auth_url = (
        f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/oauth2/v2.0/authorize?"
        f"client_id={MICROSOFT_CLIENT_ID}&"
        f"response_type=code&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_mode=query&"
        f"scope={' '.join(SCOPES)}&"
        f"state={state}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256"
    )
    
    return {"auth_url": auth_url, "redirect_uri": REDIRECT_URI}


@router.get("/auth/microsoft/callback")
async def microsoft_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None)
):
    """Handle Microsoft OAuth callback"""
    if error:
        logger.error(f"OAuth error: {error}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/auth/error?error={error}",
            status_code=302
        )
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    try:
        # Decode state to get code_verifier (in production, use proper session storage)
        code_verifier = None
        if state:
            try:
                # Add padding if needed for base64 decoding
                padding = 4 - (len(state) % 4)
                if padding != 4:
                    state_padded = state + '=' * padding
                else:
                    state_padded = state
                code_verifier = base64.urlsafe_b64decode(state_padded).decode()
            except Exception as e:
                logger.warning(f"Failed to decode state parameter: {e}")
                code_verifier = None
        
        # Exchange authorization code for tokens
        token_url = f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
        
        if not MICROSOFT_CLIENT_SECRET:
            logger.error("MICROSOFT_CLIENT_SECRET not configured")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/auth/error?error=client_secret_not_configured",
                status_code=302
            )
        
        token_data = {
            "client_id": MICROSOFT_CLIENT_ID,
            "client_secret": MICROSOFT_CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        
        if code_verifier:
            token_data["code_verifier"] = code_verifier
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                return RedirectResponse(
                    url=f"http://localhost:3000/auth/error?error=token_exchange_failed",
                    status_code=302
                )
            
            token_response = response.json()
            
            # Calculate token expiration
            expires_in = token_response.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Store tokens in database
            async with AsyncSessionLocal() as session:
                # Check if user already exists
                result = await session.execute(
                    select(MicrosoftAuth).where(MicrosoftAuth.user_id == "default")
                )
                auth_record = result.scalar_one_or_none()
                
                try:
                    if auth_record:
                        # Update existing record
                        auth_record.access_token = token_response.get("access_token")
                        auth_record.refresh_token = token_response.get("refresh_token")
                        auth_record.expires_at = expires_at
                        auth_record.token_type = token_response.get("token_type", "Bearer")
                        auth_record.updated_at = datetime.utcnow()
                    else:
                        # Create new record
                        auth_record = MicrosoftAuth(
                            user_id="default",
                            access_token=token_response.get("access_token"),
                            refresh_token=token_response.get("refresh_token"),
                            expires_at=expires_at,
                            token_type=token_response.get("token_type", "Bearer")
                        )
                        session.add(auth_record)
                    
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Failed to store OAuth tokens: {e}", exc_info=True)
                    raise
            
            logger.info("Microsoft OAuth tokens stored successfully")
            
            # Redirect to frontend with success
            return RedirectResponse(
                url=f"{FRONTEND_URL}/auth/success",
                status_code=302
            )
            
    except Exception as e:
        logger.error(f"Error processing OAuth callback: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{FRONTEND_URL}/auth/error?error={str(e)}",
            status_code=302
        )


@router.get("/auth/microsoft/status")
async def auth_status():
    """Check Microsoft authentication status"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MicrosoftAuth).where(MicrosoftAuth.user_id == "default")
            )
            auth_record = result.scalar_one_or_none()
            
            if not auth_record or not auth_record.access_token:
                return {"authenticated": False, "provider": "microsoft"}
            
            # Check if token is expired
            is_expired = auth_record.expires_at and auth_record.expires_at < datetime.utcnow()
            
            if is_expired and auth_record.refresh_token:
                # Try to refresh token
                try:
                    token_url = f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
                    
                    if not MICROSOFT_CLIENT_SECRET:
                        logger.error("MICROSOFT_CLIENT_SECRET not configured for token refresh")
                        return {"authenticated": False, "provider": "microsoft", "error": "client_secret_not_configured"}
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            token_url,
                            data={
                                "client_id": MICROSOFT_CLIENT_ID,
                                "client_secret": MICROSOFT_CLIENT_SECRET,
                                "refresh_token": auth_record.refresh_token,
                                "grant_type": "refresh_token",
                                "redirect_uri": REDIRECT_URI,
                            },
                            headers={"Content-Type": "application/x-www-form-urlencoded"}
                        )
                        
                        if response.status_code == 200:
                            token_response = response.json()
                            expires_in = token_response.get("expires_in", 3600)
                            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                            
                            try:
                                auth_record.access_token = token_response.get("access_token")
                                auth_record.refresh_token = token_response.get("refresh_token", auth_record.refresh_token)
                                auth_record.expires_at = expires_at
                                auth_record.updated_at = datetime.utcnow()
                                
                                await session.commit()
                                
                                return {
                                    "authenticated": True,
                                    "provider": "microsoft",
                                    "expires_at": expires_at.isoformat()
                                }
                            except Exception as e:
                                await session.rollback()
                                logger.error(f"Failed to commit token refresh: {e}", exc_info=True)
                                return {"authenticated": False, "provider": "microsoft", "error": "token_refresh_failed"}
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")
                    return {"authenticated": False, "provider": "microsoft", "error": "token_refresh_failed"}
            
            return {
                "authenticated": not is_expired,
                "provider": "microsoft",
                "expires_at": auth_record.expires_at.isoformat() if auth_record.expires_at else None
            }
            
    except Exception as e:
        logger.error(f"Error checking auth status: {e}", exc_info=True)
        return {"authenticated": False, "provider": "microsoft", "error": str(e)}


@router.post("/auth/microsoft/logout")
async def microsoft_logout():
    """Logout and clear Microsoft tokens"""
    try:
        async with AsyncSessionLocal() as session:
            try:
                # Use delete statement for proper async support
                result = await session.execute(
                    delete(MicrosoftAuth).where(MicrosoftAuth.user_id == "default")
                )
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to commit logout: {e}", exc_info=True)
                raise
            
            return {"status": "logged_out", "provider": "microsoft"}
            
    except Exception as e:
        logger.error(f"Error during logout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Logout error: {str(e)}")


@router.post("/auth/microsoft/token")
async def set_microsoft_token(token_input: TokenInput):
    """Manually set Microsoft access token (for Graph Explorer)"""
    try:
        access_token = token_input.access_token.strip()
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Access token cannot be empty")
        
        # Optionally validate the token by making a test request
        try:
            async with httpx.AsyncClient() as client:
                test_response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=5.0
                )
                if test_response.status_code == 401:
                    raise HTTPException(status_code=401, detail="Invalid or expired token")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Token validation failed: {e}, but storing token anyway")
        
        # Calculate expiration (Graph Explorer tokens typically last 1 hour)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Store token in database
        async with AsyncSessionLocal() as session:
            # Check if user already exists
            result = await session.execute(
                select(MicrosoftAuth).where(MicrosoftAuth.user_id == "default")
            )
            auth_record = result.scalar_one_or_none()
            
            try:
                if auth_record:
                    # Update existing record
                    auth_record.access_token = access_token
                    auth_record.refresh_token = None  # Graph Explorer tokens don't have refresh tokens
                    auth_record.expires_at = expires_at
                    auth_record.token_type = "Bearer"
                    auth_record.updated_at = datetime.utcnow()
                else:
                    # Create new record
                    auth_record = MicrosoftAuth(
                        user_id="default",
                        access_token=access_token,
                        refresh_token=None,
                        expires_at=expires_at,
                        token_type="Bearer"
                    )
                    session.add(auth_record)
                
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to commit token storage: {e}", exc_info=True)
                raise
        
        logger.info("Microsoft token set successfully from Graph Explorer")
        
        return {
            "status": "token_set",
            "provider": "microsoft",
            "expires_at": expires_at.isoformat(),
            "message": "Token set successfully. Note: Graph Explorer tokens expire after ~1 hour."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error setting token: {str(e)}")


async def get_microsoft_token() -> Optional[str]:
    """Get stored Microsoft access token"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MicrosoftAuth).where(MicrosoftAuth.user_id == "default")
            )
            auth_record = result.scalar_one_or_none()
            
            if not auth_record:
                logger.debug("[Auth] No Microsoft auth record found in database")
                return None
            
            # Check if access_token exists and is not empty
            if not auth_record.access_token or not auth_record.access_token.strip():
                logger.warning("[Auth] Access token is None or empty in database")
                return None
            
            # Check if token is expired
            if auth_record.expires_at and auth_record.expires_at < datetime.utcnow():
                logger.info("[Auth] Access token expired, attempting refresh...")
                # Token expired, try to refresh
                if auth_record.refresh_token:
                    try:
                        if not MICROSOFT_CLIENT_SECRET:
                            logger.error("[Auth] MICROSOFT_CLIENT_SECRET not configured for token refresh")
                            return None
                        
                        token_url = f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
                        
                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                                token_url,
                                data={
                                    "client_id": MICROSOFT_CLIENT_ID,
                                    "client_secret": MICROSOFT_CLIENT_SECRET,
                                    "refresh_token": auth_record.refresh_token,
                                    "grant_type": "refresh_token",
                                    "redirect_uri": REDIRECT_URI,
                                },
                                headers={"Content-Type": "application/x-www-form-urlencoded"}
                            )
                            
                            if response.status_code == 200:
                                token_response = response.json()
                                expires_in = token_response.get("expires_in", 3600)
                                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                                
                                new_access_token = token_response.get("access_token")
                                if not new_access_token or not new_access_token.strip():
                                    logger.error("[Auth] Refreshed token is empty")
                                    return None
                                
                                try:
                                    auth_record.access_token = new_access_token
                                    auth_record.refresh_token = token_response.get("refresh_token", auth_record.refresh_token)
                                    auth_record.expires_at = expires_at
                                    auth_record.updated_at = datetime.utcnow()
                                    
                                    await session.commit()
                                    
                                    logger.info("[Auth] Token refreshed successfully")
                                    return auth_record.access_token
                                except Exception as e:
                                    await session.rollback()
                                    logger.error(f"[Auth] Failed to commit token refresh: {e}", exc_info=True)
                                    return None
                            else:
                                logger.error(f"[Auth] Token refresh failed with status {response.status_code}: {response.text}")
                                return None
                    except Exception as e:
                        logger.error(f"[Auth] Token refresh failed with exception: {e}", exc_info=True)
                        return None
                else:
                    logger.warning("[Auth] Token expired but no refresh token available")
                    return None
            
            # Validate token format (should be a JWT-like string)
            token = auth_record.access_token.strip()
            if len(token) < 50:  # JWT tokens are typically much longer
                logger.warning(f"[Auth] Token appears to be invalid (too short: {len(token)} chars)")
                return None
            
            logger.debug(f"[Auth] Returning valid token (expires at: {auth_record.expires_at})")
            return token
            
    except Exception as e:
        logger.error(f"[Auth] Error getting Microsoft token: {e}", exc_info=True)
        return None


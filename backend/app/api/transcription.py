"""
Transcription API endpoints
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import json
import base64
import asyncio
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
import time
import numpy as np

from app.database import get_db, MeetingSession
from app.models.schemas import MeetingSessionCreate, MeetingSessionResponse, MeetingDetailsResponse, TranscriptUpdateRequest
from app.services.transcription_service import TranscriptionService, AudioCaptureService

logger = logging.getLogger(__name__)
router = APIRouter()

# Store active sessions with lock for thread safety
active_sessions: Dict[str, Dict] = {}

# Create lock lazily on first use (since asyncio.Lock requires event loop)
_active_sessions_lock: Optional[asyncio.Lock] = None

def get_active_sessions_lock() -> asyncio.Lock:
    """Get or create the active sessions lock (lazy initialization)"""
    global _active_sessions_lock
    if _active_sessions_lock is None:
        try:
            _active_sessions_lock = asyncio.Lock()
        except RuntimeError:
            # If no event loop exists yet, create a new one (shouldn't happen in FastAPI)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _active_sessions_lock = asyncio.Lock()
    return _active_sessions_lock

# Initialize transcription service
transcription_service = TranscriptionService()

# Initialize audio capture service for system audio
audio_capture_service = AudioCaptureService()


def merge_transcripts_with_labels(user_transcripts: List[Tuple[float, str]], 
                                  audience_transcripts: List[Tuple[float, str]]) -> str:
    """Merge transcripts from user and audience chronologically with speaker labels
    
    Args:
        user_transcripts: List of (timestamp, text) tuples for user microphone
        audience_transcripts: List of (timestamp, text) tuples for system audio
    
    Returns:
        Merged transcript string in conversation format
    """
    # Combine all transcripts with their source labels
    all_transcripts = []
    for timestamp, text in user_transcripts:
        if text and text.strip():
            all_transcripts.append((timestamp, "User", text.strip()))
    for timestamp, text in audience_transcripts:
        if text and text.strip():
            all_transcripts.append((timestamp, "Audience", text.strip()))
    
    # Sort by timestamp
    all_transcripts.sort(key=lambda x: x[0])
    
    # Format as conversation
    conversation_lines = []
    for timestamp, speaker, text in all_transcripts:
        conversation_lines.append(f'"{speaker}": {text}')
    
    return "\n\n".join(conversation_lines)


def format_transcript_for_display(user_transcripts: List[Tuple[float, str]], 
                                  audience_transcripts: List[Tuple[float, str]]) -> str:
    """Format transcripts for real-time display (most recent first, then merge)"""
    # Get the most recent transcript from each source for the buffer
    user_latest = user_transcripts[-1][1] if user_transcripts else ""
    audience_latest = audience_transcripts[-1][1] if audience_transcripts else ""
    
    # Return merged full transcript
    return merge_transcripts_with_labels(user_transcripts, audience_transcripts)


@router.post("/start", response_model=MeetingSessionResponse)
async def start_session(
    request: MeetingSessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Start a new transcription session - only stored in memory until insights are generated"""
    session_id = str(uuid.uuid4())
    title = request.title or "Untitled Meeting"
    started_at = datetime.utcnow()
    
    logger.info(f"[Transcription] Starting session {session_id} with title: {title} (memory only)")
    
    # Create session object but don't save to database yet
    # Only save to database when insights are generated
    session_obj = {
        "id": session_id,
        "title": title,
        "started_at": started_at,
        "is_active": True,
        "transcript": "",
        "full_transcript": ""
    }
    
    # Store in active sessions with separate tracking for user and audience
    async with get_active_sessions_lock():
        active_sessions[session_id] = {
            "session": session_obj,
            "full_transcript": "",
            "transcript_buffer": "",
            "user_transcripts": [],  # List of (timestamp, text) tuples
            "audience_transcripts": []  # List of (timestamp, text) tuples
        }
    
    logger.info(f"[Transcription] Session {session_id} started successfully (memory only). Active sessions: {len(active_sessions)}")
    
    return MeetingSessionResponse(
        id=session_id,
        title=title,
        started_at=started_at,
        ended_at=None,
        is_active=True,
        transcript=""
    )


@router.post("/stop/{session_id}")
async def stop_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Stop a transcription session - only saves to DB if insights were generated"""
    logger.info(f"[Transcription] Stopping session {session_id}")
    
    # Check if session exists in database (only if insights were generated)
    result = await db.execute(
        select(MeetingSession).where(MeetingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    # Update transcript in memory
    async with get_active_sessions_lock():
        active_data = active_sessions.get(session_id)
        if active_data:
            # Ensure final merge of all transcripts
            user_transcripts = active_data.get("user_transcripts", [])
            audience_transcripts = active_data.get("audience_transcripts", [])
            merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
            
            transcript_len = len(merged_transcript)
            buffer_len = len(active_data.get("transcript_buffer", ""))
            
            # Only update database if session exists (insights were generated)
            if session:
                session.is_active = False
                session.ended_at = datetime.utcnow()
                session.full_transcript = merged_transcript
                session.transcript = active_data.get("transcript_buffer", "")
                await db.commit()
                logger.info(f"[Transcription] Session {session_id} stopped and saved to DB (insights exist). Transcript length: {transcript_len}")
            else:
                # Session not in DB means insights weren't generated - just remove from memory
                logger.info(f"[Transcription] Session {session_id} stopped but not saved to DB (no insights). Transcript length: {transcript_len}, buffer: {buffer_len}")
            
            # Remove from active sessions
            if session_id in active_sessions:
                del active_sessions[session_id]
        else:
            logger.warning(f"[Transcription] Session {session_id} not in active_sessions")
            if session:
                # Session exists in DB but not in memory - mark as inactive
                session.is_active = False
                session.ended_at = datetime.utcnow()
                await db.commit()
    
    return {"status": "stopped", "session_id": session_id}


@router.get("/session/{session_id}", response_model=MeetingSessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get session details - checks both database and memory"""
    # First check database
    result = await db.execute(
        select(MeetingSession).where(MeetingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if session:
        return MeetingSessionResponse(
            id=session.id,
            title=session.title,
            started_at=session.started_at,
            ended_at=session.ended_at,
            is_active=session.is_active,
            transcript=session.transcript
        )
    
    # If not in DB, check memory
    async with get_active_sessions_lock():
        if session_id in active_sessions:
            active_data = active_sessions[session_id]
            session_obj = active_data.get("session", {})
            return MeetingSessionResponse(
                id=session_obj.get("id", session_id),
                title=session_obj.get("title", "Untitled Meeting"),
                started_at=session_obj.get("started_at", datetime.utcnow()),
                ended_at=None,
                is_active=session_obj.get("is_active", True),
                transcript=active_data.get("transcript_buffer", "")
            )
    
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/session/{session_id}/details", response_model=MeetingDetailsResponse)
async def get_session_details(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive session details including MOM, FAQs, email draft, etc."""
    # First check database
    result = await db.execute(
        select(MeetingSession).where(MeetingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if session:
        return MeetingDetailsResponse(
            id=session.id,
            title=session.title,
            started_at=session.started_at,
            ended_at=session.ended_at,
            is_active=session.is_active,
            transcript=session.transcript or "",
            full_transcript=session.full_transcript or "",
            mom=session.mom if session.mom else None,
            faqs=session.faqs if session.faqs else None,
            email_draft=session.email_draft if session.email_draft else None,
            risks=session.risks if session.risks else None
        )
    
    # If not in DB, check memory
    async with get_active_sessions_lock():
        if session_id in active_sessions:
            active_data = active_sessions[session_id]
            session_obj = active_data.get("session", {})
            return MeetingDetailsResponse(
                id=session_obj.get("id", session_id),
                title=session_obj.get("title", "Untitled Meeting"),
                started_at=session_obj.get("started_at", datetime.utcnow()),
                ended_at=None,
                is_active=session_obj.get("is_active", True),
                transcript=active_data.get("transcript_buffer", ""),
                full_transcript=active_data.get("full_transcript", ""),
                mom=None,
                faqs=None,
                email_draft=None,
                risks=None
            )
    
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/transcript/{session_id}")
async def get_transcript(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get full transcript for a session - checks both database and memory"""
    # First check database
    result = await db.execute(
        select(MeetingSession).where(MeetingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if session:
        return {
            "session_id": session_id,
            "transcript": session.full_transcript or session.transcript or "",
            "title": session.title
        }
    
    # If not in DB, check memory
    async with get_active_sessions_lock():
        if session_id in active_sessions:
            active_data = active_sessions[session_id]
            session_obj = active_data.get("session", {})
            return {
                "session_id": session_id,
                "transcript": active_data.get("full_transcript", active_data.get("transcript_buffer", "")),
                "title": session_obj.get("title", "Untitled Meeting")
            }
    
    raise HTTPException(status_code=404, detail="Session not found")


@router.put("/transcript/{session_id}")
async def update_transcript(
    session_id: str,
    request: TranscriptUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update the transcript for a session - updates memory, and DB if session exists"""
    # Check if session exists in database (only if insights were generated)
    result = await db.execute(
        select(MeetingSession).where(MeetingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    # Update in memory
    async with get_active_sessions_lock():
        if session_id in active_sessions:
            active_sessions[session_id]["full_transcript"] = request.transcript
            active_sessions[session_id]["transcript_buffer"] = request.transcript
    
    # Update database if session exists (insights were generated)
    if session:
        session.full_transcript = request.transcript
        session.transcript = request.transcript
        await db.commit()
        await db.refresh(session)
        logger.info(f"[Transcription] Updated transcript for session {session_id} in DB and memory, length: {len(request.transcript)}")
    else:
        logger.info(f"[Transcription] Updated transcript for session {session_id} in memory only, length: {len(request.transcript)}")
    
    return {
        "session_id": session_id,
        "transcript": request.transcript,
        "status": "updated"
    }


@router.get("/status")
async def get_transcription_status():
    """Get transcription service status"""
    return {
        "active_service": "whisper" if transcription_service.local_model is not None else None,
        "use_deepgram": False,
        "deepgram_configured": False,
        "deepgram_client_available": False,
        "whisper_available": transcription_service.local_model is not None,
        "status": "configured" if transcription_service.local_model is not None else "not_configured"
    }


@router.get("/meetings")
async def list_meetings(
    db: AsyncSession = Depends(get_db)
):
    """List all meeting sessions that have insights generated (mom field is not null)."""
    try:
        # Only get meetings that have insights (mom is not null)
        result = await db.execute(
            select(MeetingSession)
            .where(MeetingSession.mom.isnot(None))
            .order_by(MeetingSession.started_at.desc())
        )
        sessions = result.scalars().all()
        
        if sessions and len(sessions) > 0:
            # Convert database sessions to response format
            meetings = []
            for session in sessions:
                meeting_data = {
                    "id": session.id,
                    "title": session.title,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "is_active": session.is_active,
                    "transcript": session.transcript or "",
                    "full_transcript": session.full_transcript or "",
                    "mom": session.mom if session.mom else None,
                    "faqs": session.faqs if session.faqs else None,
                    "email_draft": session.email_draft if session.email_draft else None,
                    "risks": session.risks if session.risks else None
                }
                meetings.append(meeting_data)
            
            logger.info(f"[Transcription] Returning {len(meetings)} meetings with insights from database")
            return {"meetings": meetings, "count": len(meetings), "source": "database"}
        else:
            # Database is empty or no meetings with insights, return empty list
            logger.info("[Transcription] No meetings with insights found, returning empty list")
            return {"meetings": [], "count": 0, "source": "database"}
    except Exception as e:
        logger.error(f"[Transcription] Error fetching meetings: {e}", exc_info=True)
        # On error, return empty list
        return {"meetings": [], "count": 0, "source": "error"}


@router.delete("/meetings/cleanup")
async def cleanup_meetings_without_insights(
    db: AsyncSession = Depends(get_db)
):
    """Delete all meeting sessions that don't have insights generated (mom is null)"""
    try:
        # Find all meetings without insights
        result = await db.execute(
            select(MeetingSession).where(
                (MeetingSession.mom.is_(None)) | (MeetingSession.mom == {})
            )
        )
        sessions_to_delete = result.scalars().all()
        
        count = len(sessions_to_delete)
        if count > 0:
            for session in sessions_to_delete:
                await db.delete(session)
            await db.commit()
            logger.info(f"[Transcription] Deleted {count} meetings without insights")
            return {"deleted": count, "message": f"Deleted {count} meeting(s) without insights"}
        else:
            logger.info("[Transcription] No meetings without insights to delete")
            return {"deleted": 0, "message": "No meetings without insights to delete"}
    except Exception as e:
        logger.error(f"[Transcription] Error cleaning up meetings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error cleaning up meetings: {str(e)}")


@router.websocket("/ws/{session_id}")
async def websocket_transcription(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time audio transcription"""
    logger.info(f"[Transcription] WebSocket connection opened for session {session_id}")
    await websocket.accept()
    
    async with get_active_sessions_lock():
        if session_id not in active_sessions:
            logger.warning(f"[Transcription] WebSocket connection rejected - session {session_id} not found")
            await websocket.close(code=1008, reason="Session not found")
            return
    
    # Initialize variables outside try block for finally access
    full_transcript = ""
    pcm_buffer = bytearray()  # Store PCM data instead of WebM
    webm_buffer = bytearray()  # Accumulate WebM chunks - first chunk has initialization, subsequent are clusters
    webm_header_end = 0  # Track where the WebM header ends (after first chunk)
    # Use larger buffer for Whisper (better quality)
    # 96000 bytes = ~6 seconds at 16kHz (better for Whisper - longer context improves accuracy)
    buffer_size_threshold = 96000
    pcm_buffer_max_size = 256000  # Maximum 250KB for PCM buffer to prevent memory issues
    webm_buffer_max_size = 262144  # Maximum 256KB for WebM buffer
    webm_buffer_min_size = 32768  # Minimum 32KB before attempting conversion
    total_user_bytes = 0
    user_chunk_count = 0
    last_conversion_attempt = 0  # Track last conversion attempt
    last_transcription_attempt = 0  # Track last transcription attempt
    WEBM_HEADER = b'\x1a\x45\xdf\xa3'  # WebM/Matroska EBML header
    
    logger.info(f"[Audio Capture] User microphone WebSocket ready for session {session_id}")
    
    try:
        while True:
            try:
                # Receive audio data from client
                data = await websocket.receive()
            except WebSocketDisconnect:
                break
            except RuntimeError as e:
                # Handle "Cannot call receive once a disconnect message has been received"
                if "disconnect" in str(e).lower():
                    break
                raise
            
            if "text" in data:
                # Handle text messages (control messages)
                message = json.loads(data["text"])
                if message.get("type") == "close":
                    break
            elif "bytes" in data:
                # Handle binary audio data (WebM format from browser)
                # MediaRecorder sends fragmented WebM: first chunk has initialization, subsequent are clusters
                # We need to accumulate chunks to form a valid WebM stream
                webm_bytes = data["bytes"]
                user_chunk_count += 1
                total_user_bytes += len(webm_bytes)
                
                # Accumulate WebM chunks (first chunk has headers, subsequent are clusters)
                webm_buffer.extend(webm_bytes)
                
                # Track WebM header position (first chunk contains the header)
                if user_chunk_count == 1 and webm_buffer.startswith(WEBM_HEADER):
                    # Find where the header segment ends (roughly after first chunk)
                    # The header is typically in the first few KB, but we'll track the first chunk size
                    webm_header_end = len(webm_buffer)
                    logger.debug(f"[Transcription] WebM header detected in first chunk, header end at position {webm_header_end}")
                
                # Prevent buffer overflow - preserve header if we have it
                if len(webm_buffer) > webm_buffer_max_size:
                    logger.warning(f"[Transcription] WebM buffer overflow detected ({len(webm_buffer)} bytes), preserving header and keeping recent data")
                    if webm_header_end > 0 and webm_header_end < len(webm_buffer):
                        # Preserve header and keep recent data
                        header = webm_buffer[:webm_header_end]
                        recent_data = webm_buffer[-(webm_buffer_max_size - webm_header_end):]
                        webm_buffer = bytearray(header) + bytearray(recent_data)
                    else:
                        # No header tracked, just keep recent data
                        webm_buffer = webm_buffer[-131072:]
                if len(pcm_buffer) > pcm_buffer_max_size:
                    logger.warning(f"[Transcription] PCM buffer overflow detected ({len(pcm_buffer)} bytes), clearing buffer")
                    pcm_buffer.clear()
                
                # Continuous real-time logging - log every chunk
                if user_chunk_count == 1:
                    logger.info(f"[Audio Capture] 🎙️ User microphone capture started - Chunk #{user_chunk_count}: {len(webm_bytes)} bytes | WebM Buffer: {len(webm_buffer)} bytes | PCM Buffer: {len(pcm_buffer)} bytes | Total: {total_user_bytes} bytes")
                else:
                    # Log every chunk at INFO level for continuous visibility
                    logger.info(f"[Audio Capture] 🎙️ Chunk #{user_chunk_count}: {len(webm_bytes)} bytes | WebM Buffer: {len(webm_buffer)} bytes | PCM Buffer: {len(pcm_buffer)} bytes | Total: {total_user_bytes} bytes")
                
                # Convert accumulated WebM buffer when we have enough data
                # MediaRecorder fragments need to be accumulated to form a valid WebM stream
                should_convert = (
                    len(webm_buffer) >= webm_buffer_min_size and
                    (user_chunk_count - last_conversion_attempt >= 3 or len(webm_buffer) >= webm_buffer_max_size)
                )
                
                if should_convert:
                    last_conversion_attempt = user_chunk_count
                    # Convert accumulated WebM chunks (first chunk has initialization, rest are clusters)
                    webm_data_to_convert = bytes(webm_buffer)
                    # Save original buffer state before modifying
                    original_buffer = bytearray(webm_buffer)
                    
                    # Keep overlap to maintain WebM structure continuity
                    # Preserve header if we have it, otherwise keep last 32KB
                    overlap_size = 32768
                    if webm_header_end > 0 and webm_header_end < len(webm_buffer):
                        # Preserve header and keep recent data for overlap
                        header = webm_buffer[:webm_header_end]
                        if len(webm_buffer) > webm_header_end + overlap_size:
                            recent_data = webm_buffer[-(overlap_size):]
                            webm_buffer = bytearray(header) + bytearray(recent_data)
                        else:
                            # Not enough data to overlap, keep everything
                            pass
                    elif len(webm_buffer) > overlap_size:
                        # No header tracked, just keep last overlap_size
                        webm_buffer = webm_buffer[-overlap_size:]
                    else:
                        # Buffer too small, keep everything
                        pass
                    
                    logger.info(f"[Transcription] 🔄 Attempting WebM to PCM conversion - Accumulated buffer size: {len(webm_data_to_convert)} bytes")
                    pcm_chunk = await transcription_service.convert_webm_to_pcm(webm_data_to_convert)
                    
                    if pcm_chunk:
                        logger.info(f"[Transcription] ✅ WebM conversion successful! PCM size: {len(pcm_chunk)} bytes")
                        # Accumulate PCM data (PCM can be safely concatenated)
                        pcm_buffer.extend(pcm_chunk)
                        
                        # Transcribe when PCM buffer reaches threshold, or if we have accumulated some data
                        # and it's been a while since last transcription (to avoid losing audio)
                        should_transcribe = (
                            len(pcm_buffer) >= buffer_size_threshold or
                            (len(pcm_buffer) >= buffer_size_threshold // 2 and 
                             user_chunk_count - last_transcription_attempt >= 10)
                        )
                        
                        if should_transcribe:
                            chunk_to_transcribe = bytes(pcm_buffer)
                            buffer_size = len(chunk_to_transcribe)
                            pcm_buffer.clear()
                            last_transcription_attempt = user_chunk_count
                            
                            logger.info(f"[Transcription] 📝 Processing User audio chunk for transcription - Size: {buffer_size} bytes (PCM)")
                            # Transcribe PCM audio chunk (force English language)
                            transcript = await transcription_service.transcribe_audio_chunk(chunk_to_transcribe, language='en', audio_format='pcm')
                            if transcript:
                                logger.info(f"[Transcription] ✅ User Transcript: {transcript[:100]}...")
                            else:
                                logger.warning(f"[Transcription] ⚠️ No transcript generated for this chunk")
                                # Send error message to client if transcription service is not available (only once)
                                if not transcription_service.local_model and not transcription_service._transcription_warning_logged:
                                    try:
                                        await websocket.send_json({
                                            "type": "error",
                                            "message": "Transcription service not configured. Whisper model not loaded. Check backend logs for details."
                                        })
                                    except:
                                        pass
                            
                            if transcript and transcript.strip():
                                # Get current timestamp using time.time() for consistency
                                timestamp = time.time()
                                
                                # Store transcript with timestamp in user_transcripts (with lock)
                                async with get_active_sessions_lock():
                                    if session_id in active_sessions:
                                        active_data = active_sessions[session_id]
                                        active_data["user_transcripts"].append((timestamp, transcript))
                                        logger.info(f"[Transcription] 📝 Stored User transcript: {transcript[:50]}... (Total user transcripts: {len(active_data['user_transcripts'])})")
                                        
                                        # Merge all transcripts chronologically
                                        user_transcripts = active_data.get("user_transcripts", [])
                                        audience_transcripts = active_data.get("audience_transcripts", [])
                                        merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                                        
                                        active_data["full_transcript"] = merged_transcript
                                        # Accumulate transcript in buffer (keep recent transcripts)
                                        if active_data["transcript_buffer"]:
                                            active_data["transcript_buffer"] += " " + transcript
                                        else:
                                            active_data["transcript_buffer"] = transcript
                                        
                                        # Get full_transcript for sending (while holding lock)
                                        full_transcript_to_send = active_data["full_transcript"]
                                    else:
                                        full_transcript_to_send = ""
                                
                                # Send transcript back to client with speaker label
                                try:
                                    message = {
                                        "type": "transcript",
                                        "speaker": "User",
                                        "text": transcript,
                                        "full_transcript": full_transcript_to_send
                                    }
                                    await websocket.send_json(message)
                                    logger.info(f"[Transcription] ✅ Sent User transcript to client: {transcript[:50]}... (full_transcript length: {len(full_transcript_to_send)})")
                                except (WebSocketDisconnect, RuntimeError) as e:
                                    logger.warning(f"[Transcription] Failed to send transcript to client: {e}")
                                    break
                                except Exception as e:
                                    logger.error(f"[Transcription] Unexpected error sending transcript: {e}", exc_info=True)
                                    break
                    else:
                        logger.warning(f"[Transcription] ⚠️ WebM conversion failed for accumulated buffer ({len(webm_data_to_convert)} bytes) - will retry with more data")
                        # Restore original buffer if conversion failed (preserve header if we have it)
                        if len(original_buffer) < webm_buffer_max_size * 2:
                            # Restore the original buffer
                            webm_buffer = original_buffer
                        else:
                            logger.warning(f"[Transcription] WebM buffer too large after failed conversion, preserving header and keeping recent data")
                            if webm_data_to_convert.startswith(WEBM_HEADER):
                                # Keep header and recent data
                                if webm_header_end > 0 and webm_header_end < len(webm_data_to_convert):
                                    header = webm_data_to_convert[:webm_header_end]
                                    recent_data = webm_data_to_convert[-(webm_buffer_max_size - webm_header_end):]
                                    webm_buffer = bytearray(header) + bytearray(recent_data)
                                else:
                                    # Try to find header
                                    header_pos = webm_data_to_convert.find(WEBM_HEADER)
                                    if header_pos >= 0:
                                        # Estimate header size (typically 1-4KB)
                                        estimated_header_size = min(4096, len(webm_data_to_convert) // 4)
                                        header = webm_data_to_convert[header_pos:header_pos + estimated_header_size]
                                        recent_data = webm_data_to_convert[-(webm_buffer_max_size - estimated_header_size):]
                                        webm_buffer = bytearray(header) + bytearray(recent_data)
                                    else:
                                        webm_buffer = bytearray(webm_data_to_convert[-webm_buffer_max_size:])
                            else:
                                webm_buffer = bytearray(webm_data_to_convert[-webm_buffer_max_size:])
            elif "close" in data:
                break
                
    except WebSocketDisconnect:
        logger.info(f"[Transcription] WebSocket disconnected for session {session_id}")
        logger.info(f"[Audio Capture] User microphone capture ended - Total chunks: {user_chunk_count}, Total bytes: {total_user_bytes}")
        pass
    except Exception as e:
        logger.error(f"[Transcription] WebSocket error for session {session_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass
    finally:
        # Process any remaining WebM buffer
        if webm_buffer and len(webm_buffer) > webm_buffer_min_size:
            try:
                logger.info(f"[Transcription] Processing remaining WebM buffer: {len(webm_buffer)} bytes")
                pcm_chunk = await transcription_service.convert_webm_to_pcm(bytes(webm_buffer))
                if pcm_chunk:
                    pcm_buffer.extend(pcm_chunk)
            except Exception as e:
                logger.warning(f"[Transcription] Failed to convert remaining WebM buffer: {e}")
        
        # Process any remaining audio in PCM buffer
        if pcm_buffer and len(pcm_buffer) > 1000:
            try:
                transcript = await transcription_service.transcribe_audio_chunk(bytes(pcm_buffer), language='en', audio_format='pcm')
                if transcript and transcript.strip():
                    timestamp = time.time()
                    async with get_active_sessions_lock():
                        if session_id in active_sessions:
                            active_data = active_sessions[session_id]
                            active_data["user_transcripts"].append((timestamp, transcript))
                            # Merge all transcripts
                            user_transcripts = active_data.get("user_transcripts", [])
                            audience_transcripts = active_data.get("audience_transcripts", [])
                            merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                            active_data["full_transcript"] = merged_transcript
            except Exception as e:
                logger.warning(f"[Transcription] Error processing remaining PCM buffer: {e}")
        
        # Don't update database here - only update memory
        # Database will be updated when insights are generated or session is stopped (if insights exist)
        async with get_active_sessions_lock():
            if session_id in active_sessions:
                active_data = active_sessions.get(session_id)
                if active_data:
                    # Final merge of all transcripts (memory only)
                    user_transcripts = active_data.get("user_transcripts", [])
                    audience_transcripts = active_data.get("audience_transcripts", [])
                    merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                    transcript_len = len(merged_transcript)
                    active_data["full_transcript"] = merged_transcript
                    logger.info(f"[Transcription] User microphone WebSocket closed for session {session_id}. Final transcript length: {transcript_len} (memory only)")
            
            # Don't delete session here - it may still be used by system audio WebSocket
            # Session will be cleaned up by /stop endpoint


@router.websocket("/ws-system/{session_id}")
async def websocket_system_audio_transcription(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time system audio transcription"""
    logger.info(f"[Transcription] System audio WebSocket connection opened for session {session_id}")
    await websocket.accept()
    
    async with get_active_sessions_lock():
        if session_id not in active_sessions:
            logger.warning(f"[Transcription] System audio WebSocket connection rejected - session {session_id} not found")
            await websocket.close(code=1008, reason="Session not found")
            return
    
    # Initialize variables
    full_transcript = ""
    audio_buffer = bytearray()
    # Use larger buffer for Whisper (better quality)
    # 96000 bytes = ~6 seconds at 16kHz (better for Whisper - longer context improves accuracy)
    buffer_size_threshold = 96000
    audio_buffer_max_size = 256000  # Maximum 250KB for audio buffer to prevent memory issues
    capture_task = None
    total_system_bytes = 0
    system_chunk_count = 0
    
    try:
        # Start system audio capture
        logger.info(f"[Transcription] Starting system audio capture for session {session_id}")
        audio_capture_service.is_recording = True
        
        # Create a task to handle audio capture
        async def capture_and_transcribe():
            nonlocal full_transcript, audio_buffer, total_system_bytes, system_chunk_count
            
            try:
                async for audio_chunk in audio_capture_service.start_capture():
                    if not audio_capture_service.is_recording:
                        break
                    
                    # Prevent buffer overflow - clear if too large
                    if len(audio_buffer) > audio_buffer_max_size:
                        logger.warning(f"[Transcription] Audio buffer overflow detected ({len(audio_buffer)} bytes), clearing buffer")
                        audio_buffer.clear()
                    
                    # Accumulate audio chunks
                    audio_buffer.extend(audio_chunk)
                    system_chunk_count += 1
                    total_system_bytes += len(audio_chunk)
                    
                    # Continuous real-time logging - log every chunk
                    if system_chunk_count == 1:
                        logger.info(f"[Audio Capture] 🎤 System audio capture started - Chunk #{system_chunk_count}: {len(audio_chunk)} bytes | Total: {total_system_bytes} bytes")
                    else:
                        # Log every chunk at INFO level for continuous visibility
                        logger.info(f"[Audio Capture] 🎤 Chunk #{system_chunk_count}: {len(audio_chunk)} bytes | Buffer: {len(audio_buffer)} bytes | Total: {total_system_bytes} bytes")
                    
                    # Transcribe when buffer reaches threshold
                    if len(audio_buffer) >= buffer_size_threshold:
                        chunk_to_transcribe = bytes(audio_buffer)
                        buffer_size = len(chunk_to_transcribe)
                        audio_buffer.clear()
                        
                        # Log audio characteristics before transcription
                        audio_np = np.frombuffer(chunk_to_transcribe, dtype=np.int16).astype(np.float32) / 32768.0
                        audio_max = np.abs(audio_np).max()
                        audio_rms = np.sqrt(np.mean(audio_np**2))
                        audio_std = np.std(audio_np)
                        logger.info(f"[Transcription] 📝 Processing system audio chunk - Size: {buffer_size} bytes | Max: {audio_max:.4f}, RMS: {audio_rms:.4f}, Std: {audio_std:.4f}")
                        
                        # Pre-validate audio before transcription - reject only if BOTH max and RMS are too low
                        # Use more lenient thresholds for system audio (which may have lower RMS even when audio is playing)
                        silence_threshold_max = 0.03  # 3% of full scale (more lenient)
                        silence_threshold_rms = 0.01   # 1% RMS (more lenient for system audio)
                        # Use AND logic: only skip if BOTH conditions are true (both max and RMS are low)
                        if audio_max < silence_threshold_max and audio_rms < silence_threshold_rms:
                            logger.info(f"[Transcription] ⚠️ Skipping transcription - audio too quiet (max: {audio_max:.4f}, RMS: {audio_rms:.4f})")
                            audio_buffer.clear()  # Clear buffer to prevent accumulation
                            continue
                        
                        # Transcribe audio chunk (system audio is raw PCM, force English language)
                        transcript = await transcription_service.transcribe_audio_chunk(chunk_to_transcribe, language='en', audio_format='pcm')
                        if transcript:
                            logger.info(f"[Transcription] ✅ Audience Transcript: {transcript[:100]}...")
                        else:
                            logger.info(f"[Transcription] ⚠️ No transcript generated (likely silence/noise filtered out)")
                            # Send error message to client if transcription service is not available
                            if not transcription_service.local_model:
                                try:
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": "Transcription service not configured. Whisper model not loaded. Check backend logs for details."
                                    })
                                except:
                                    pass
                        
                        if transcript and transcript.strip():
                            # Get current timestamp using time.time() for consistency
                            timestamp = time.time()
                            
                            # Store transcript with timestamp in audience_transcripts (with lock)
                            async with get_active_sessions_lock():
                                if session_id in active_sessions:
                                    active_data = active_sessions[session_id]
                                    active_data["audience_transcripts"].append((timestamp, transcript))
                                    logger.info(f"[Transcription] 📝 Stored Audience transcript: {transcript[:50]}... (Total audience transcripts: {len(active_data['audience_transcripts'])})")
                                    
                                    # Merge all transcripts chronologically
                                    user_transcripts = active_data.get("user_transcripts", [])
                                    audience_transcripts = active_data.get("audience_transcripts", [])
                                    merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                                    
                                    active_data["full_transcript"] = merged_transcript
                                    # Accumulate transcript in buffer (keep recent transcripts)
                                    if active_data["transcript_buffer"]:
                                        active_data["transcript_buffer"] += " " + transcript
                                    else:
                                        active_data["transcript_buffer"] = transcript
                                    
                                    # Get full_transcript for sending (while holding lock)
                                    full_transcript_to_send = active_data["full_transcript"]
                                else:
                                    full_transcript_to_send = ""
                            
                            # Send transcript back to client with speaker label
                            try:
                                message = {
                                    "type": "transcript",
                                    "speaker": "Audience",
                                    "text": transcript,
                                    "full_transcript": full_transcript_to_send
                                }
                                await websocket.send_json(message)
                                logger.info(f"[Transcription] ✅ Sent Audience transcript to client: {transcript[:50]}... (full_transcript length: {len(full_transcript_to_send)})")
                            except (WebSocketDisconnect, RuntimeError) as e:
                                logger.warning(f"[Transcription] Failed to send transcript to client: {e}")
                                break
                            except Exception as e:
                                logger.error(f"[Transcription] Unexpected error sending transcript: {e}", exc_info=True)
                                break
            except RuntimeError as e:
                # RuntimeError from AudioCaptureService (e.g., no device found)
                error_msg = str(e)
                logger.error(f"[Transcription] System audio capture error: {error_msg}", exc_info=True)
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": error_msg
                    })
                except:
                    pass
            except Exception as e:
                # Other exceptions
                error_msg = f"System audio capture error: {str(e)}"
                logger.error(f"[Transcription] Error in system audio capture: {e}", exc_info=True)
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": error_msg
                    })
                except:
                    pass
        
        # Start the capture task
        capture_task = asyncio.create_task(capture_and_transcribe())
        
        # Listen for control messages from client
        while True:
            try:
                data = await websocket.receive()
            except WebSocketDisconnect:
                break
            except RuntimeError as e:
                if "disconnect" in str(e).lower():
                    break
                raise
            
            if "text" in data:
                # Handle text messages (control messages)
                message = json.loads(data["text"])
                if message.get("type") == "close" or message.get("type") == "stop":
                    logger.info(f"[Transcription] Stop signal received for system audio session {session_id}")
                    audio_capture_service.stop_capture()
                    break
            elif "close" in data:
                break
                
    except WebSocketDisconnect:
        logger.info(f"[Transcription] System audio WebSocket disconnected for session {session_id}")
        logger.info(f"[Audio Capture] System audio capture ended - Total chunks: {system_chunk_count}, Total bytes: {total_system_bytes}")
        pass
    except Exception as e:
        logger.error(f"[Transcription] System audio WebSocket error for session {session_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass
    finally:
        # Stop audio capture
        audio_capture_service.stop_capture()
        
        # Cancel capture task if running
        if capture_task and not capture_task.done():
            capture_task.cancel()
            try:
                await capture_task
            except asyncio.CancelledError:
                pass
        
        # Process any remaining audio in buffer
        if audio_buffer and len(audio_buffer) > 1000:
            try:
                transcript = await transcription_service.transcribe_audio_chunk(bytes(audio_buffer), language='en', audio_format='pcm')
                if transcript and transcript.strip():
                    timestamp = time.time()
                    async with get_active_sessions_lock():
                        if session_id in active_sessions:
                            active_data = active_sessions[session_id]
                            active_data["audience_transcripts"].append((timestamp, transcript))
                            # Merge all transcripts
                            user_transcripts = active_data.get("user_transcripts", [])
                            audience_transcripts = active_data.get("audience_transcripts", [])
                            merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                            active_data["full_transcript"] = merged_transcript
            except Exception as e:
                logger.warning(f"[Transcription] Error processing remaining audio buffer: {e}")
        
        # Don't update database here - only update memory
        # Database will be updated when insights are generated or session is stopped (if insights exist)
        async with get_active_sessions_lock():
            if session_id in active_sessions:
                active_data = active_sessions.get(session_id)
                if active_data:
                    # Final merge of all transcripts (memory only)
                    user_transcripts = active_data.get("user_transcripts", [])
                    audience_transcripts = active_data.get("audience_transcripts", [])
                    merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                    transcript_len = len(merged_transcript)
                    active_data["full_transcript"] = merged_transcript
                    logger.info(f"[Transcription] System audio WebSocket closed for session {session_id}. Final transcript length: {transcript_len} (memory only)")
            
            # Don't delete session here - it may still be used by user microphone WebSocket
            # Session will be cleaned up by /stop endpoint

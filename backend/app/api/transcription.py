"""
Transcription API endpoints
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import json
import base64
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
import logging
import time
import numpy as np

from app.database import get_db, MeetingSession
from app.models.schemas import MeetingSessionCreate, MeetingSessionResponse, MeetingDetailsResponse, TranscriptUpdateRequest
from app.services.transcription_service import TranscriptionService, AudioCaptureService
from app.services.assemblyai_service import AssemblyAIService

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

# Initialize Assembly AI service
assemblyai_service = AssemblyAIService()


def merge_transcripts_with_labels(user_transcripts: List[Tuple[float, str]], 
                                  audience_transcripts: List[Tuple[float, str]]) -> str:
    """Merge transcripts from user and audience chronologically with speaker labels
    Detects duplicate content from both sources and merges them intelligently
    
    Args:
        user_transcripts: List of (timestamp, text) tuples for user microphone
        audience_transcripts: List of (timestamp, text) tuples for system audio
    
    Returns:
        Merged transcript string in conversation format
    """
    # Combine all transcripts with their source labels
    all_transcripts = []
    processed_audience = set()  # Track processed audience transcripts to avoid duplicates
    
    # Process user transcripts first
    for timestamp, text in user_transcripts:
        if text and text.strip():
            all_transcripts.append((timestamp, "User", text.strip()))
    
    # Process audience transcripts, but skip if very similar to recent user transcript
    for timestamp, text in audience_transcripts:
        if text and text.strip():
            text_clean = text.strip().lower()
            
            # Check if this audience transcript is similar to any recent user transcript
            # (within 5 seconds and >80% similarity)
            is_duplicate = False
            for user_ts, user_text in user_transcripts:
                if abs(timestamp - user_ts) <= 5.0:  # Within 5 seconds
                    user_clean = user_text.strip().lower()
                    # Simple similarity check: if one contains the other or vice versa
                    if (text_clean in user_clean or user_clean in text_clean or 
                        len(set(text_clean.split()) & set(user_clean.split())) / max(len(text_clean.split()), len(user_clean.split())) > 0.8):
                        is_duplicate = True
                        break
            
            # Only add audience transcript if it's not a duplicate of user transcript
            if not is_duplicate:
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
    started_at = datetime.now(timezone.utc)
    
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
                try:
                    session.is_active = False
                    session.ended_at = datetime.now(timezone.utc)
                    session.full_transcript = merged_transcript
                    session.transcript = active_data.get("transcript_buffer", "")
                    await db.commit()
                    logger.info(f"[Transcription] Session {session_id} stopped and saved to DB (insights exist). Transcript length: {transcript_len}")
                except Exception as e:
                    await db.rollback()
                    logger.error(f"[Transcription] Failed to commit session stop: {e}", exc_info=True)
                    raise
            else:
                # Session not in DB means insights weren't generated - keep in memory for now
                # Session will be removed when insights are generated or manually cleaned up
                active_data["session"]["is_active"] = False
                active_data["full_transcript"] = merged_transcript  # Ensure merged transcript is stored
                active_data["transcript_buffer"] = merged_transcript  # Also update buffer
                logger.info(f"[Transcription] Session {session_id} stopped but kept in memory (no insights yet). Transcript length: {transcript_len}, buffer: {buffer_len}")
            
            # Only remove from active sessions if session exists in DB (insights were already generated)
            # Otherwise keep it in memory so transcript can be fetched and insights can be generated
            if session and session_id in active_sessions:
                del active_sessions[session_id]
                logger.info(f"[Transcription] Removed session {session_id} from memory (insights already exist in DB)")
        else:
            logger.warning(f"[Transcription] Session {session_id} not in active_sessions")
            if session:
                # Session exists in DB but not in memory - mark as inactive
                try:
                    session.is_active = False
                    session.ended_at = datetime.now(timezone.utc)
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    logger.error(f"[Transcription] Failed to commit session stop: {e}", exc_info=True)
                    raise
    
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
                started_at=session_obj.get("started_at", datetime.now(timezone.utc)),
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
                started_at=session_obj.get("started_at", datetime.now(timezone.utc)),
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
        try:
            session.full_transcript = request.transcript
            session.transcript = request.transcript
            await db.commit()
            await db.refresh(session)
            logger.info(f"[Transcription] Updated transcript for session {session_id} in DB and memory, length: {len(request.transcript)}")
        except Exception as e:
            await db.rollback()
            logger.error(f"[Transcription] Failed to commit transcript update: {e}", exc_info=True)
            raise
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
                    "started_at": session.started_at.isoformat() + 'Z' if session.started_at else None,
                    "ended_at": session.ended_at.isoformat() + 'Z' if session.ended_at else None,
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
            try:
                for session in sessions_to_delete:
                    db.delete(session)
                await db.commit()
                logger.info(f"[Transcription] Deleted {count} meetings without insights")
                return {"deleted": count, "message": f"Deleted {count} meeting(s) without insights"}
            except Exception as e:
                await db.rollback()
                logger.error(f"[Transcription] Failed to commit meeting cleanup: {e}", exc_info=True)
                raise
        else:
            logger.info("[Transcription] No meetings without insights to delete")
            return {"deleted": 0, "message": "No meetings without insights to delete"}
    except Exception as e:
        logger.error(f"[Transcription] Error cleaning up meetings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error cleaning up meetings: {str(e)}")


@router.post("/upload-transcript", response_model=MeetingSessionResponse)
async def upload_transcript(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload a transcript file and create a session for analysis"""
    try:
        # Read file content
        content = await file.read()
        transcript_text = content.decode('utf-8')
        
        if not transcript_text or not transcript_text.strip():
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        # Create a new session
        session_id = str(uuid.uuid4())
        session_title = title or file.filename or "Uploaded Transcript"
        started_at = datetime.now(timezone.utc)
        
        logger.info(f"[Transcription] Creating session {session_id} from uploaded transcript file: {file.filename}")
        
        # Create session in database immediately (since we have the transcript)
        session = MeetingSession(
            id=session_id,
            title=session_title,
            started_at=started_at,
            ended_at=started_at,  # Mark as ended since it's a file upload
            is_active=False,
            transcript=transcript_text,
            full_transcript=transcript_text
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        logger.info(f"[Transcription] Created session {session_id} from uploaded transcript, length: {len(transcript_text)}")
        
        return MeetingSessionResponse(
            id=session_id,
            title=session_title,
            started_at=started_at,
            ended_at=started_at,
            is_active=False,
            transcript=transcript_text
        )
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be a valid UTF-8 text file")
    except Exception as e:
        logger.error(f"[Transcription] Error uploading transcript: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading transcript: {str(e)}")


@router.websocket("/ws/{session_id}")
async def websocket_transcription(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for final transcription (accumulates audio until done)"""
    logger.info(f"[Transcription] WebSocket connection opened for session {session_id}")
    await websocket.accept()
    
    async with get_active_sessions_lock():
        if session_id not in active_sessions:
            logger.warning(f"[Transcription] WebSocket connection rejected - session {session_id} not found")
            await websocket.close(code=1008, reason="Session not found")
            return
    
    # Initialize variables outside try block for finally access
    full_transcript = ""
    webm_buffer = bytearray()  # Accumulate all WebM chunks until transcription
    webm_header_end = 0  # Track where the WebM header ends (after first chunk)
    webm_buffer_max_size = 50 * 1024 * 1024  # Maximum 50MB for accumulated audio
    total_user_bytes = 0
    user_chunk_count = 0
    is_recording = True
    WEBM_HEADER = b'\x1a\x45\xdf\xa3'  # WebM/Matroska EBML header
    
    # Real-time transcription: transcribe every 8 seconds (increased to allow more complete sentences)
    last_transcription_time = time.time()
    transcription_interval = 8.0  # Transcribe every 8 seconds (increased from 5s to allow complete sentences)
    transcribed_buffer_size = 0  # Track how much we've already transcribed
    
    logger.info(f"[Audio Capture] User microphone WebSocket ready for session {session_id} - Real-time transcription mode (every {transcription_interval}s)")
    
    try:
        while is_recording:
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
                if message.get("type") == "close" or message.get("type") == "stop":
                    logger.info(f"[Transcription] Received stop signal, processing final transcription")
                    is_recording = False
                    break
            elif "bytes" in data:
                # Handle binary audio data (WebM format from browser)
                # Accumulate all chunks until we're done
                webm_bytes = data["bytes"]
                user_chunk_count += 1
                total_user_bytes += len(webm_bytes)
                
                # Accumulate WebM chunks (first chunk has headers, subsequent are clusters)
                webm_buffer.extend(webm_bytes)
                
                # Track WebM header position (first chunk contains the header)
                if user_chunk_count == 1 and webm_buffer.startswith(WEBM_HEADER):
                    webm_header_end = len(webm_buffer)
                    logger.debug(f"[Transcription] WebM header detected in first chunk, header end at position {webm_header_end}")
                
                # Prevent buffer overflow
                if len(webm_buffer) > webm_buffer_max_size:
                    logger.warning(f"[Transcription] WebM buffer overflow detected ({len(webm_buffer)} bytes), truncating")
                    if webm_header_end > 0 and webm_header_end < len(webm_buffer):
                        # Preserve header and keep recent data
                        header = webm_buffer[:webm_header_end]
                        recent_data = webm_buffer[-(webm_buffer_max_size - webm_header_end):]
                        webm_buffer = bytearray(header) + bytearray(recent_data)
                    else:
                        webm_buffer = webm_buffer[-webm_buffer_max_size:]
                
                # Log periodically (every 10 chunks) instead of every chunk
                if user_chunk_count == 1:
                    logger.info(f"[Audio Capture] 🎙️ User microphone capture started - Chunk #{user_chunk_count}: {len(webm_bytes)} bytes | WebM Buffer: {len(webm_buffer)} bytes | Total: {total_user_bytes} bytes")
                elif user_chunk_count % 10 == 0:
                    logger.info(f"[Audio Capture] 🎙️ Chunk #{user_chunk_count}: {len(webm_bytes)} bytes | WebM Buffer: {len(webm_buffer)} bytes | Total: {total_user_bytes} bytes")
                
                # Real-time transcription: transcribe periodically (every 8 seconds)
                current_time = time.time()
                # Increased threshold: need at least 100KB new data (was 50KB) to ensure we have enough audio for complete sentences
                if current_time - last_transcription_time >= transcription_interval and len(webm_buffer) > transcribed_buffer_size + 100000:  # At least 100KB new data
                    try:
                        # Get the new audio since last transcription
                        new_audio = webm_buffer[transcribed_buffer_size:]
                        if len(new_audio) > 20000:  # Minimum 20KB to transcribe (increased from 10KB for better quality)
                            logger.info(f"[Transcription] 🔄 Real-time transcription triggered - New audio: {len(new_audio)} bytes | Total buffer: {len(webm_buffer)} bytes")
                            
                            # Convert and transcribe the new audio
                            pcm_data = await transcription_service.convert_webm_to_pcm(bytes(new_audio))
                            if pcm_data and len(pcm_data) > 0:
                                transcript = await transcription_service.transcribe_audio_chunk(pcm_data, language='en', audio_format='pcm')
                                
                                if transcript and transcript.strip():
                                    timestamp = time.time()
                                    
                                    # Store transcript with timestamp
                                    async with get_active_sessions_lock():
                                        if session_id in active_sessions:
                                            active_data = active_sessions[session_id]
                                            active_data["user_transcripts"].append((timestamp, transcript))
                                            
                                            # Merge all transcripts
                                            user_transcripts = active_data.get("user_transcripts", [])
                                            audience_transcripts = active_data.get("audience_transcripts", [])
                                            merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                                            
                                            active_data["full_transcript"] = merged_transcript
                                            
                                            # Send real-time transcript to client
                                            try:
                                                message = {
                                                    "type": "transcript",
                                                    "speaker": "User",
                                                    "text": transcript,
                                                    "full_transcript": merged_transcript
                                                }
                                                await websocket.send_json(message)
                                                logger.info(f"[Transcription] ✅ Sent real-time transcript: {transcript[:50]}...")
                                            except (WebSocketDisconnect, RuntimeError):
                                                pass
                                    
                                    # Update transcription tracking
                                    transcribed_buffer_size = len(webm_buffer)
                                    last_transcription_time = current_time
                                else:
                                    logger.debug(f"[Transcription] Real-time transcription returned empty (silence or no speech)")
                            else:
                                logger.debug(f"[Transcription] WebM conversion failed for real-time chunk")
                    except Exception as e:
                        logger.warning(f"[Transcription] Error in real-time transcription: {e}", exc_info=True)
                        # Don't break the loop, just log and continue
            elif "close" in data:
                is_recording = False
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
        # Process any remaining accumulated audio for final transcription
        # Only transcribe the part we haven't transcribed yet
        remaining_audio_size = len(webm_buffer) - transcribed_buffer_size
        if remaining_audio_size > 5000:  # Minimum size check (increased from 1000 to ensure quality)
            try:
                logger.info(f"[Transcription] Processing final accumulated audio - Remaining: {remaining_audio_size} bytes | Total buffer: {len(webm_buffer)} bytes")
                
                # Get the remaining audio that hasn't been transcribed
                remaining_audio = webm_buffer[transcribed_buffer_size:]
                
                # Convert remaining WebM buffer to PCM
                pcm_data = await transcription_service.convert_webm_to_pcm(bytes(remaining_audio))
                
                if pcm_data and len(pcm_data) > 0:
                    logger.info(f"[Transcription] ✅ WebM conversion successful! PCM size: {len(pcm_data)} bytes")
                    
                    # Transcribe the entire accumulated audio
                    logger.info(f"[Transcription] 📝 Starting final transcription of accumulated audio")
                    transcript = await transcription_service.transcribe_audio_chunk(pcm_data, language='en', audio_format='pcm')
                    
                    if transcript and transcript.strip():
                        timestamp = time.time()
                        
                        # Store transcript with timestamp in user_transcripts (with lock)
                        async with get_active_sessions_lock():
                            if session_id in active_sessions:
                                active_data = active_sessions[session_id]
                                active_data["user_transcripts"].append((timestamp, transcript))
                                logger.info(f"[Transcription] 📝 Stored final User transcript: {transcript[:100]}...")
                                
                                # Merge all transcripts chronologically
                                user_transcripts = active_data.get("user_transcripts", [])
                                audience_transcripts = active_data.get("audience_transcripts", [])
                                merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                                
                                active_data["full_transcript"] = merged_transcript
                                active_data["transcript_buffer"] = transcript
                                
                                # Send final transcript back to client
                                try:
                                    message = {
                                        "type": "final_transcript",
                                        "speaker": "User",
                                        "text": transcript,
                                        "full_transcript": merged_transcript
                                    }
                                    await websocket.send_json(message)
                                    logger.info(f"[Transcription] ✅ Sent final User transcript to client: {transcript[:100]}... (full_transcript length: {len(merged_transcript)})")
                                except (WebSocketDisconnect, RuntimeError) as e:
                                    logger.warning(f"[Transcription] Failed to send final transcript to client: {e}")
                                except Exception as e:
                                    logger.error(f"[Transcription] Unexpected error sending final transcript: {e}", exc_info=True)
                    else:
                        logger.warning(f"[Transcription] ⚠️ No transcript generated from accumulated audio")
                        # Send error message to client if transcription service is not available
                        if not transcription_service.local_model:
                            try:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": "Transcription service not configured. Whisper model not loaded. Check backend logs for details."
                                })
                            except:
                                pass
                else:
                    logger.warning(f"[Transcription] ⚠️ WebM to PCM conversion failed or produced empty output")
            except Exception as e:
                logger.error(f"[Transcription] Error processing final accumulated audio: {e}", exc_info=True)
        else:
            logger.info(f"[Transcription] No audio accumulated to transcribe (buffer size: {len(webm_buffer) if webm_buffer else 0} bytes)")
        
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
    """WebSocket endpoint for final system audio transcription (accumulates audio until done)"""
    logger.info(f"[Transcription] System audio WebSocket connection opened for session {session_id}")
    await websocket.accept()
    
    async with get_active_sessions_lock():
        if session_id not in active_sessions:
            logger.warning(f"[Transcription] System audio WebSocket connection rejected - session {session_id} not found")
            await websocket.close(code=1008, reason="Session not found")
            return
    
    # Initialize variables
    full_transcript = ""
    audio_buffer = bytearray()  # Accumulate all audio until transcription
    audio_buffer_max_size = 50 * 1024 * 1024  # Maximum 50MB for accumulated audio
    capture_task = None
    total_system_bytes = 0
    system_chunk_count = 0
    
    # Real-time transcription: transcribe every 8 seconds (increased to allow more complete sentences)
    last_transcription_time = time.time()
    transcription_interval = 8.0  # Transcribe every 8 seconds (increased from 5s to allow complete sentences)
    transcribed_buffer_size = 0  # Track how much we've already transcribed
    
    try:
        # Start system audio capture
        logger.info(f"[Transcription] Starting system audio capture for session {session_id}")
        audio_capture_service.is_recording = True
        
        # Create a task to handle audio capture with real-time transcription
        async def capture_audio():
            nonlocal audio_buffer, total_system_bytes, system_chunk_count, last_transcription_time, transcribed_buffer_size
            
            try:
                async for audio_chunk in audio_capture_service.start_capture():
                    if not audio_capture_service.is_recording:
                        break
                    
                    # Prevent buffer overflow
                    if len(audio_buffer) > audio_buffer_max_size:
                        logger.warning(f"[Transcription] Audio buffer overflow detected ({len(audio_buffer)} bytes), truncating")
                        audio_buffer = audio_buffer[-audio_buffer_max_size:]
                        # Adjust transcribed buffer size if we truncated
                        if transcribed_buffer_size > len(audio_buffer):
                            transcribed_buffer_size = max(0, len(audio_buffer) - 100000)  # Keep some margin
                    
                    # Accumulate audio chunks
                    audio_buffer.extend(audio_chunk)
                    system_chunk_count += 1
                    total_system_bytes += len(audio_chunk)
                    
                    # Log periodically (every 10 chunks) instead of every chunk
                    if system_chunk_count == 1:
                        logger.info(f"[Audio Capture] 🎤 System audio capture started - Chunk #{system_chunk_count}: {len(audio_chunk)} bytes | Buffer: {len(audio_buffer)} bytes | Total: {total_system_bytes} bytes")
                    elif system_chunk_count % 10 == 0:
                        logger.info(f"[Audio Capture] 🎤 Chunk #{system_chunk_count}: {len(audio_chunk)} bytes | Buffer: {len(audio_buffer)} bytes | Total: {total_system_bytes} bytes")
                    
                    # Real-time transcription: transcribe periodically (every 8 seconds)
                    current_time = time.time()
                    # Increased threshold: need at least 100KB new data (was 50KB) to ensure we have enough audio for complete sentences
                    if current_time - last_transcription_time >= transcription_interval and len(audio_buffer) > transcribed_buffer_size + 100000:  # At least 100KB new data
                        try:
                            # Get the new audio since last transcription
                            new_audio = audio_buffer[transcribed_buffer_size:]
                            if len(new_audio) > 20000:  # Minimum 20KB to transcribe (increased from 10KB for better quality)
                                logger.info(f"[Transcription] 🔄 Real-time system audio transcription - New audio: {len(new_audio)} bytes | Total buffer: {len(audio_buffer)} bytes")
                                
                                # Transcribe the new audio
                                transcript = await transcription_service.transcribe_audio_chunk(bytes(new_audio), language='en', audio_format='pcm')
                                
                                if transcript and transcript.strip():
                                    timestamp = time.time()
                                    
                                    # Store transcript with timestamp
                                    async with get_active_sessions_lock():
                                        if session_id in active_sessions:
                                            active_data = active_sessions[session_id]
                                            active_data["audience_transcripts"].append((timestamp, transcript))
                                            
                                            # Merge all transcripts
                                            user_transcripts = active_data.get("user_transcripts", [])
                                            audience_transcripts = active_data.get("audience_transcripts", [])
                                            merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                                            
                                            active_data["full_transcript"] = merged_transcript
                                            
                                            # Send real-time transcript to client
                                            try:
                                                message = {
                                                    "type": "transcript",
                                                    "speaker": "Audience",
                                                    "text": transcript,
                                                    "full_transcript": merged_transcript
                                                }
                                                await websocket.send_json(message)
                                                logger.info(f"[Transcription] ✅ Sent real-time system audio transcript: {transcript[:50]}...")
                                            except (WebSocketDisconnect, RuntimeError):
                                                pass
                                    
                                    # Update transcription tracking
                                    transcribed_buffer_size = len(audio_buffer)
                                    last_transcription_time = current_time
                                else:
                                    logger.debug(f"[Transcription] Real-time system audio transcription returned empty (silence or no speech)")
                        except Exception as e:
                            logger.warning(f"[Transcription] Error in real-time system audio transcription: {e}", exc_info=True)
                            # Don't break the loop, just log and continue
            except RuntimeError as e:
                # RuntimeError from AudioCaptureService (e.g., no device found)
                error_msg = str(e)
                logger.error(f"[Transcription] System audio capture error: {error_msg}", exc_info=True)
                
                # Provide helpful error message
                helpful_msg = error_msg
                if "No system audio" in error_msg or "device" in error_msg.lower():
                    helpful_msg = (
                        f"{error_msg}\n\n"
                        "To fix system audio capture:\n"
                        "1. Install BlackHole: brew install blackhole-2ch\n"
                        "2. OR set AUDIO_CAPTURE_METHOD=ffmpeg in .env\n"
                        "3. Check system audio permissions in System Settings"
                    )
                elif "ffmpeg" in error_msg.lower():
                    helpful_msg = (
                        f"{error_msg}\n\n"
                        "FFmpeg is required for system audio capture.\n"
                        "Install with: brew install ffmpeg"
                    )
                
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": helpful_msg
                    })
                except:
                    pass
            except Exception as e:
                # Other exceptions
                error_msg = f"System audio capture error: {str(e)}"
                logger.error(f"[Transcription] Error in system audio capture: {e}", exc_info=True)
                
                # Check if it's an FFmpeg issue
                if "ffmpeg" in str(e).lower() or "FileNotFoundError" in str(type(e)):
                    helpful_msg = (
                        f"{error_msg}\n\n"
                        "FFmpeg is required for system audio capture.\n"
                        "Install with: brew install ffmpeg"
                    )
                else:
                    helpful_msg = error_msg
                
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": helpful_msg
                    })
                except:
                    pass
        
        # Start the capture task
        capture_task = asyncio.create_task(capture_audio())
        
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
        
        # Process any remaining accumulated audio for final transcription
        # Only transcribe the part we haven't transcribed yet
        remaining_audio_size = len(audio_buffer) - transcribed_buffer_size
        if remaining_audio_size > 5000:  # Minimum size check (increased from 1000 to ensure quality)
            try:
                logger.info(f"[Transcription] Processing final accumulated system audio - Remaining: {remaining_audio_size} bytes | Total buffer: {len(audio_buffer)} bytes")
                
                # Get the remaining audio that hasn't been transcribed
                remaining_audio = audio_buffer[transcribed_buffer_size:]
                
                # Transcribe the remaining audio
                logger.info(f"[Transcription] 📝 Starting final transcription of remaining system audio")
                transcript = await transcription_service.transcribe_audio_chunk(bytes(remaining_audio), language='en', audio_format='pcm')
                
                if transcript and transcript.strip():
                    timestamp = time.time()
                    
                    # Store transcript with timestamp in audience_transcripts (with lock)
                    async with get_active_sessions_lock():
                        if session_id in active_sessions:
                            active_data = active_sessions[session_id]
                            active_data["audience_transcripts"].append((timestamp, transcript))
                            logger.info(f"[Transcription] 📝 Stored final Audience transcript: {transcript[:100]}...")
                            
                            # Merge all transcripts chronologically
                            user_transcripts = active_data.get("user_transcripts", [])
                            audience_transcripts = active_data.get("audience_transcripts", [])
                            merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                            
                            active_data["full_transcript"] = merged_transcript
                            active_data["transcript_buffer"] = transcript
                            
                            # Send final transcript back to client
                            try:
                                message = {
                                    "type": "final_transcript",
                                    "speaker": "Audience",
                                    "text": transcript,
                                    "full_transcript": merged_transcript
                                }
                                await websocket.send_json(message)
                                logger.info(f"[Transcription] ✅ Sent final Audience transcript to client: {transcript[:100]}... (full_transcript length: {len(merged_transcript)})")
                            except (WebSocketDisconnect, RuntimeError) as e:
                                logger.warning(f"[Transcription] Failed to send final transcript to client: {e}")
                            except Exception as e:
                                logger.error(f"[Transcription] Unexpected error sending final transcript: {e}", exc_info=True)
                else:
                    logger.warning(f"[Transcription] ⚠️ No transcript generated from accumulated system audio")
                    # Send error message to client if transcription service is not available
                    if not transcription_service.local_model:
                        try:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Transcription service not configured. Whisper model not loaded. Check backend logs for details."
                            })
                        except:
                            pass
            except Exception as e:
                logger.error(f"[Transcription] Error processing final accumulated system audio: {e}", exc_info=True)
        else:
            logger.info(f"[Transcription] No system audio accumulated to transcribe (buffer size: {len(audio_buffer) if audio_buffer else 0} bytes)")
        
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

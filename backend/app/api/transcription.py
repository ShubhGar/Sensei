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
from typing import Dict, List, Tuple
import logging

from app.database import get_db, MeetingSession
from app.models.schemas import MeetingSessionCreate, MeetingSessionResponse
from app.services.transcription_service import TranscriptionService, AudioCaptureService

logger = logging.getLogger(__name__)
router = APIRouter()

# Store active sessions
active_sessions: Dict[str, Dict] = {}

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
    """Start a new transcription session"""
    session_id = str(uuid.uuid4())
    title = request.title or "Untitled Meeting"
    
    logger.info(f"[Transcription] Starting session {session_id} with title: {title}")
    
    session = MeetingSession(
        id=session_id,
        title=title,
        started_at=datetime.utcnow(),
        is_active=True,
        transcript="",
        full_transcript=""
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    # Store in active sessions with separate tracking for user and audience
    active_sessions[session_id] = {
        "session": session,
        "full_transcript": "",
        "transcript_buffer": "",
        "user_transcripts": [],  # List of (timestamp, text) tuples
        "audience_transcripts": []  # List of (timestamp, text) tuples
    }
    
    logger.info(f"[Transcription] Session {session_id} started successfully. Active sessions: {len(active_sessions)}")
    
    return MeetingSessionResponse(
        id=session.id,
        title=session.title,
        started_at=session.started_at,
        ended_at=session.ended_at,
        is_active=session.is_active,
        transcript=session.transcript
    )


@router.post("/stop/{session_id}")
async def stop_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Stop a transcription session"""
    logger.info(f"[Transcription] Stopping session {session_id}")
    
    result = await db.execute(
        select(MeetingSession).where(MeetingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        logger.warning(f"[Transcription] Session {session_id} not found")
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.is_active = False
    session.ended_at = datetime.utcnow()
    
    # Update transcript if available - merge final transcripts
    active_data = active_sessions.get(session_id)
    if active_data:
        # Ensure final merge of all transcripts
        user_transcripts = active_data.get("user_transcripts", [])
        audience_transcripts = active_data.get("audience_transcripts", [])
        merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
        
        transcript_len = len(merged_transcript)
        buffer_len = len(active_data.get("transcript_buffer", ""))
        session.full_transcript = merged_transcript
        session.transcript = active_data.get("transcript_buffer", "")
        del active_sessions[session_id]
        logger.info(f"[Transcription] Session {session_id} stopped. Transcript length: {transcript_len}, buffer: {buffer_len}")
    else:
        logger.warning(f"[Transcription] Session {session_id} not in active_sessions")
    
    await db.commit()
    
    return {"status": "stopped", "session_id": session_id}


@router.get("/session/{session_id}", response_model=MeetingSessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get session details"""
    result = await db.execute(
        select(MeetingSession).where(MeetingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return MeetingSessionResponse(
        id=session.id,
        title=session.title,
        started_at=session.started_at,
        ended_at=session.ended_at,
        is_active=session.is_active,
        transcript=session.transcript
    )


@router.get("/transcript/{session_id}")
async def get_transcript(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get full transcript for a session"""
    result = await db.execute(
        select(MeetingSession).where(MeetingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "transcript": session.full_transcript or session.transcript or "",
        "title": session.title
    }


@router.get("/meetings")
async def list_meetings(
    db: AsyncSession = Depends(get_db)
):
    """List all meeting sessions. Returns empty list if database is empty. Returns dummy data only on errors."""
    try:
        # Try to get meetings from database
        result = await db.execute(
            select(MeetingSession).order_by(MeetingSession.started_at.desc())
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
            
            logger.info(f"[Transcription] Returning {len(meetings)} meetings from database")
            return {"meetings": meetings, "count": len(meetings), "source": "database"}
        else:
            # Database is empty, return empty list (empty is a valid response)
            logger.info("[Transcription] Database is empty, returning empty meetings list")
            return {"meetings": [], "count": 0, "source": "database"}
    except Exception as e:
        logger.error(f"[Transcription] Error fetching meetings: {e}", exc_info=True)
        # On error, return empty list
        return {"meetings": [], "count": 0, "source": "error"}


@router.websocket("/ws/{session_id}")
async def websocket_transcription(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time audio transcription"""
    logger.info(f"[Transcription] WebSocket connection opened for session {session_id}")
    await websocket.accept()
    
    if session_id not in active_sessions:
        logger.warning(f"[Transcription] WebSocket connection rejected - session {session_id} not found")
        await websocket.close(code=1008, reason="Session not found")
        return
    
    # Initialize variables outside try block for finally access
    full_transcript = ""
    pcm_buffer = bytearray()  # Store PCM data instead of WebM
    webm_buffer = bytearray()  # Buffer WebM chunks before conversion
    buffer_size_threshold = 32000  # ~2 seconds of audio at 16kHz (PCM: 16kHz * 2 bytes * 1 second)
    webm_buffer_min_size = 16384  # Minimum 16KB before attempting conversion (lower threshold for faster processing)
    webm_buffer_max_size = 131072  # Maximum 128KB - convert when we reach this to avoid memory issues
    total_user_bytes = 0
    user_chunk_count = 0
    last_conversion_attempt = 0  # Track last conversion attempt to avoid too frequent attempts
    
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
                webm_bytes = data["bytes"]
                user_chunk_count += 1
                total_user_bytes += len(webm_bytes)
                
                # Accumulate WebM chunks in buffer
                webm_buffer.extend(webm_bytes)
                
                # Continuous real-time logging - log every chunk
                if user_chunk_count == 1:
                    logger.info(f"[Audio Capture] 🎙️ User microphone capture started - Chunk #{user_chunk_count}: {len(webm_bytes)} bytes | WebM Buffer: {len(webm_buffer)} bytes | Total: {total_user_bytes} bytes")
                else:
                    # Log every chunk at INFO level for continuous visibility
                    logger.info(f"[Audio Capture] 🎙️ Chunk #{user_chunk_count}: {len(webm_bytes)} bytes | WebM Buffer: {len(webm_buffer)} bytes | PCM Buffer: {len(pcm_buffer)} bytes | Total: {total_user_bytes} bytes")
                
                # Convert WebM buffer to PCM when we have enough data
                # MediaRecorder sends WebM fragments that need to be accumulated to form valid WebM streams
                # Try converting more frequently with smaller buffers to get User transcripts faster
                should_convert = (
                    len(webm_buffer) >= webm_buffer_min_size and
                    (user_chunk_count - last_conversion_attempt >= 5 or len(webm_buffer) >= webm_buffer_max_size)
                )
                
                if should_convert:
                    last_conversion_attempt = user_chunk_count
                    # Keep smaller overlap for faster processing - 8KB should be enough for continuity
                    overlap_size = 8192
                    if len(webm_buffer) > overlap_size:
                        # Convert most of the buffer, keep last 8KB for WebM continuity
                        convert_size = len(webm_buffer) - overlap_size
                        webm_data_to_convert = bytes(webm_buffer[:convert_size])
                        # Keep the last 8KB in buffer for continuity
                        webm_buffer = webm_buffer[convert_size:]
                    else:
                        # If buffer is smaller than overlap, convert it all if we have minimum size
                        if len(webm_buffer) >= webm_buffer_min_size:
                            webm_data_to_convert = bytes(webm_buffer)
                            webm_buffer.clear()
                        else:
                            webm_data_to_convert = None
                    
                    if webm_data_to_convert:
                        logger.info(f"[Transcription] 🔄 Attempting WebM to PCM conversion - Buffer size: {len(webm_data_to_convert)} bytes")
                        # Convert accumulated WebM chunks to PCM
                        pcm_chunk = await transcription_service.convert_webm_to_pcm(webm_data_to_convert)
                        if pcm_chunk:
                            logger.info(f"[Transcription] ✅ WebM conversion successful! PCM size: {len(pcm_chunk)} bytes")
                            # Accumulate PCM data (PCM can be safely concatenated)
                            pcm_buffer.extend(pcm_chunk)
                            
                            # Transcribe when PCM buffer reaches threshold
                            if len(pcm_buffer) >= buffer_size_threshold:
                                chunk_to_transcribe = bytes(pcm_buffer)
                                buffer_size = len(chunk_to_transcribe)
                                pcm_buffer.clear()
                                
                                logger.info(f"[Transcription] 📝 Processing User audio chunk for transcription - Size: {buffer_size} bytes (PCM)")
                                # Transcribe PCM audio chunk
                                transcript = await transcription_service.transcribe_audio_chunk(chunk_to_transcribe, audio_format='pcm')
                                if transcript:
                                    logger.info(f"[Transcription] ✅ User Transcript: {transcript[:100]}...")
                                else:
                                    logger.info(f"[Transcription] ⚠️ No transcript generated for this chunk")
                                
                                if transcript and transcript.strip():
                                    # Get current timestamp
                                    timestamp = asyncio.get_event_loop().time()
                                    
                                    # Store transcript with timestamp in user_transcripts
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
                                    
                                    # Send transcript back to client with speaker label
                                    try:
                                        await websocket.send_json({
                                            "type": "transcript",
                                            "speaker": "User",
                                            "text": transcript,
                                            "full_transcript": active_sessions[session_id]["full_transcript"] if session_id in active_sessions else ""
                                        })
                                        logger.info(f"[Transcription] ✅ Sent User transcript to client: {transcript[:50]}...")
                                    except (WebSocketDisconnect, RuntimeError):
                                        break
                        else:
                            logger.debug(f"[Transcription] ⚠️ WebM conversion failed for {len(webm_data_to_convert)} bytes - will retry with more data")
                    # Note: If conversion fails, buffer will continue accumulating and we'll try again
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
        if webm_buffer and len(webm_buffer) > 1000:
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
                transcript = await transcription_service.transcribe_audio_chunk(bytes(pcm_buffer), audio_format='pcm')
                if transcript and transcript.strip():
                    timestamp = asyncio.get_event_loop().time()
                    if session_id in active_sessions:
                        active_data = active_sessions[session_id]
                        active_data["user_transcripts"].append((timestamp, transcript))
                        # Merge all transcripts
                        user_transcripts = active_data.get("user_transcripts", [])
                        audience_transcripts = active_data.get("audience_transcripts", [])
                        merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                        active_data["full_transcript"] = merged_transcript
            except:
                pass
        
        # Update database with final transcript
        # Check again before accessing to avoid race condition
        if session_id in active_sessions:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(MeetingSession).where(MeetingSession.id == session_id)
                )
                session = result.scalar_one_or_none()
                if session and session_id in active_sessions:
                    active_data = active_sessions.get(session_id)
                    if active_data:
                        # Final merge of all transcripts
                        user_transcripts = active_data.get("user_transcripts", [])
                        audience_transcripts = active_data.get("audience_transcripts", [])
                        merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                        transcript_len = len(merged_transcript)
                        session.full_transcript = merged_transcript
                        session.transcript = active_data.get("transcript_buffer", "")
                        await db.commit()
                        logger.info(f"[Transcription] User microphone WebSocket closed for session {session_id}. Final transcript length: {transcript_len}")
            
            # Don't delete session here - it may still be used by system audio WebSocket
            # Session will be cleaned up by /stop endpoint


@router.websocket("/ws-system/{session_id}")
async def websocket_system_audio_transcription(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time system audio transcription"""
    logger.info(f"[Transcription] System audio WebSocket connection opened for session {session_id}")
    await websocket.accept()
    
    if session_id not in active_sessions:
        logger.warning(f"[Transcription] System audio WebSocket connection rejected - session {session_id} not found")
        await websocket.close(code=1008, reason="Session not found")
        return
    
    # Initialize variables
    full_transcript = ""
    audio_buffer = bytearray()
    buffer_size_threshold = 32000  # ~2 seconds of audio at 16kHz
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
                        
                        logger.info(f"[Transcription] 📝 Processing system audio chunk for transcription - Size: {buffer_size} bytes")
                        # Transcribe audio chunk (system audio is raw PCM)
                        transcript = await transcription_service.transcribe_audio_chunk(chunk_to_transcribe, audio_format='pcm')
                        if transcript:
                            logger.info(f"[Transcription] ✅ Transcript: {transcript[:100]}...")
                        else:
                            logger.info(f"[Transcription] ⚠️ No transcript generated for this chunk")
                        
                        if transcript and transcript.strip():
                            # Get current timestamp
                            timestamp = asyncio.get_event_loop().time()
                            
                            # Store transcript with timestamp in audience_transcripts
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
                            
                            # Send transcript back to client with speaker label
                            try:
                                await websocket.send_json({
                                    "type": "transcript",
                                    "speaker": "Audience",
                                    "text": transcript,
                                    "full_transcript": active_sessions[session_id]["full_transcript"] if session_id in active_sessions else ""
                                })
                                logger.info(f"[Transcription] ✅ Sent Audience transcript to client: {transcript[:50]}...")
                            except (WebSocketDisconnect, RuntimeError):
                                break
            except Exception as e:
                logger.error(f"[Transcription] Error in system audio capture: {e}", exc_info=True)
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"System audio capture error: {str(e)}"
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
                transcript = await transcription_service.transcribe_audio_chunk(bytes(audio_buffer), audio_format='pcm')
                if transcript and transcript.strip():
                    timestamp = asyncio.get_event_loop().time()
                    if session_id in active_sessions:
                        active_data = active_sessions[session_id]
                        active_data["audience_transcripts"].append((timestamp, transcript))
                        # Merge all transcripts
                        user_transcripts = active_data.get("user_transcripts", [])
                        audience_transcripts = active_data.get("audience_transcripts", [])
                        merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                        active_data["full_transcript"] = merged_transcript
            except:
                pass
        
        # Update database with final transcript
        if session_id in active_sessions:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(MeetingSession).where(MeetingSession.id == session_id)
                )
                session = result.scalar_one_or_none()
                if session and session_id in active_sessions:
                    active_data = active_sessions.get(session_id)
                    if active_data:
                        # Final merge of all transcripts
                        user_transcripts = active_data.get("user_transcripts", [])
                        audience_transcripts = active_data.get("audience_transcripts", [])
                        merged_transcript = merge_transcripts_with_labels(user_transcripts, audience_transcripts)
                        transcript_len = len(merged_transcript)
                        session.full_transcript = merged_transcript
                        session.transcript = active_data.get("transcript_buffer", "")
                        await db.commit()
                        logger.info(f"[Transcription] System audio WebSocket closed for session {session_id}. Final transcript length: {transcript_len}")
            
            # Don't delete session here - it may still be used by user microphone WebSocket
            # Session will be cleaned up by /stop endpoint

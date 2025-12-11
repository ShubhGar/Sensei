"""
Real-time transcription service using Whisper or Deepgram
"""
import asyncio
import io
import wave
import numpy as np
import subprocess
import tempfile
from typing import Optional, Callable, AsyncGenerator
import os
import logging
import warnings
from dotenv import load_dotenv

# Suppress Pydantic V1 compatibility warning with Python 3.14
# The warning comes from deepgram's internal use of Pydantic V1
warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater",
    category=UserWarning
)

logger = logging.getLogger(__name__)

try:
    import whisper
except ImportError:
    whisper = None

try:
    from deepgram import DeepgramClient, PrerecordedOptions, FileSource
except ImportError:
    DeepgramClient = None
    PrerecordedOptions = None
    FileSource = None

load_dotenv()


class TranscriptionService:
    """Service for real-time audio transcription"""
    
    def __init__(self):
        self.use_deepgram = os.getenv("USE_DEEPGRAM", "false").lower() == "true"
        self.deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
        self.local_model = None
        self._transcription_warning_logged = False
        
        if not self.use_deepgram:
            # Load local Whisper model
            if whisper:
                model_name = os.getenv("LOCAL_WHISPER_MODEL", "base")
                try:
                    logger.info(f"Loading Whisper model: {model_name}")
                    self.local_model = whisper.load_model(model_name)
                    logger.info(f"Whisper model '{model_name}' loaded successfully")
                except Exception as e:
                    logger.warning(f"Could not load Whisper model: {e}")
                    logger.warning("Falling back to Deepgram if available")
                    self.use_deepgram = True
            else:
                logger.warning("Whisper not available, using Deepgram")
                self.use_deepgram = True
        
        if self.use_deepgram and self.deepgram_api_key and DeepgramClient:
            try:
                self.deepgram_client = DeepgramClient(self.deepgram_api_key)
                logger.info("Deepgram client initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize Deepgram: {e}")
                self.deepgram_client = None
        else:
            self.deepgram_client = None
    
    async def convert_webm_to_pcm(self, webm_data: bytes) -> Optional[bytes]:
        """Convert WebM audio chunk to PCM format
        
        Args:
            webm_data: WebM audio bytes from browser
            
        Returns:
            PCM audio bytes (16-bit, 16kHz, mono) or None if conversion fails
        """
        if len(webm_data) == 0:
            return None
            
        try:
            # Use FFmpeg with more lenient settings for fragmented WebM
            # MediaRecorder sends WebM fragments that may not have complete headers
            # Try matroska format first (more lenient), then webm as fallback
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'matroska,webm',  # Try both formats, more lenient
                '-err_detect', 'ignore_err',  # Ignore errors and continue processing
                '-fflags', '+genpts+discardcorrupt+igndts+ignidx',  # Generate PTS, discard corrupt frames, ignore DTS and index
                '-flags', '+global_header',  # Allow global header
                '-avoid_negative_ts', 'make_zero',  # Handle timestamp issues
                '-analyzeduration', '1000000',  # Analyze up to 1 second for stream info
                '-probesize', '1000000',  # Probe up to 1MB for stream info
                '-i', 'pipe:0',  # Read from stdin
                '-f', 's16le',   # 16-bit signed little-endian PCM
                '-acodec', 'pcm_s16le',
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',      # Mono channel
                '-loglevel', 'error',  # Suppress ffmpeg output
                '-nostdin',  # Don't read from stdin after input
                'pipe:1'         # Write to stdout
            ]
            
            # Run ffmpeg with pipe input in executor
            def run_ffmpeg():
                try:
                    process = subprocess.Popen(
                        ffmpeg_cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    # Write WebM data to stdin and close it
                    stdout, stderr = process.communicate(input=webm_data, timeout=30)
                    
                    # Check if we got any output even if return code is non-zero
                    # Sometimes FFmpeg returns non-zero but still produces output
                    if len(stdout) > 0:
                        return stdout
                    
                    if process.returncode != 0:
                        error_msg = stderr.decode('utf-8', errors='ignore') if stderr else f"FFmpeg returned {process.returncode}"
                        # Log but don't raise - we'll return None instead
                        logger.debug(f"[Whisper] FFmpeg returned non-zero but no output: {error_msg[:200]}")
                        return None
                    
                    return stdout
                except subprocess.TimeoutExpired:
                    logger.warning(f"[Whisper] FFmpeg conversion timed out for {len(webm_data)} byte chunk")
                    return None
                except Exception as e:
                    logger.debug(f"[Whisper] FFmpeg process error: {e}")
                    return None
            
            loop = asyncio.get_event_loop()
            pcm_data = await loop.run_in_executor(None, run_ffmpeg)
            
            if not pcm_data or len(pcm_data) == 0:
                # Don't log as error - this is expected for some fragmented WebM chunks
                logger.debug(f"[Whisper] FFmpeg conversion produced no output for {len(webm_data)} byte WebM chunk")
                return None
            
            logger.debug(f"[Whisper] Converted WebM to PCM - Input: {len(webm_data)} bytes, Output: {len(pcm_data)} bytes")
            return pcm_data
                    
        except FileNotFoundError:
            logger.error("[Whisper] FFmpeg not found. Please install ffmpeg: brew install ffmpeg")
            return None
        except Exception as e:
            # Don't log as error - fragmented WebM conversion failures are expected
            logger.debug(f"[Whisper] Error during WebM conversion: {e}")
            return None
    
    async def transcribe_audio_chunk(self, audio_data: bytes, language: Optional[str] = None, audio_format: Optional[str] = None) -> str:
        """Transcribe a single audio chunk
        
        Args:
            audio_data: Audio bytes (can be WebM/Opus from browser or raw PCM from system)
            language: Language code (optional)
            audio_format: Audio format hint (optional, e.g., 'webm' or 'pcm')
        """
        if self.use_deepgram and self.deepgram_client:
            return await self._transcribe_deepgram(audio_data, language, audio_format)
        elif self.local_model:
            # Whisper expects raw PCM (int16), so if it's WebM, we need to convert
            return await self._transcribe_whisper(audio_data, language, audio_format)
        else:
            # Only log warning once to avoid spam
            if not self._transcription_warning_logged:
                logger.warning("No transcription service available - audio is being captured but not transcribed. Configure Deepgram or Whisper to enable transcription.")
                self._transcription_warning_logged = True
            return ""
    
    async def _transcribe_deepgram(self, audio_data: bytes, language: Optional[str] = None, audio_format: Optional[str] = None) -> str:
        """Transcribe using Deepgram API
        
        Args:
            audio_data: Audio bytes (can be WebM/Opus from browser or raw PCM)
            language: Language code (optional)
            audio_format: Audio format hint (optional, e.g., 'webm' or 'pcm')
        """
        if not self.deepgram_client or not PrerecordedOptions:
            return ""
        
        try:
            payload: FileSource = {
                "buffer": audio_data,
            }
            
            options = PrerecordedOptions(
                model="nova-2",
                language=language or "en",
                punctuate=True,
                diarize=True,  # Speaker diarization
            )
            
            # Deepgram can auto-detect format, but we can specify if needed
            # For WebM from browser, it will auto-detect
            # For raw PCM from system audio, it should also auto-detect
            
            response = self.deepgram_client.listen.rest.v("1").transcribe_file(payload, options)
            
            if response.results and response.results.channels:
                transcript = response.results.channels[0].alternatives[0].transcript
                return transcript
            return ""
        except Exception as e:
            logger.error(f"Deepgram transcription error: {e}", exc_info=True)
            return ""
    
    async def _transcribe_whisper(self, audio_data: bytes, language: Optional[str] = None, audio_format: Optional[str] = None) -> str:
        """Transcribe using local Whisper model
        
        Args:
            audio_data: Audio bytes (can be WebM/Opus from browser or raw PCM from system)
            language: Language code (optional)
            audio_format: Audio format hint (optional, e.g., 'webm' or 'pcm')
        """
        if not self.local_model:
            return ""
        
        try:
            # Detect if audio is WebM/Opus (from browser) or PCM (from system)
            is_webm = audio_format == 'webm' or (len(audio_data) >= 4 and audio_data[:4] == b'\x1a\x45\xdf\xa3')
            
            if is_webm:
                # Convert WebM/Opus to PCM using the shared conversion method
                logger.debug(f"[Whisper] Converting WebM audio to PCM - Input size: {len(audio_data)} bytes")
                audio_data = await self.convert_webm_to_pcm(audio_data)
                if not audio_data or len(audio_data) == 0:
                    logger.warning("[Whisper] WebM to PCM conversion failed or produced empty output")
                    return ""
            
            # Convert bytes to numpy array (PCM int16 format)
            if not audio_data or len(audio_data) == 0:
                return ""
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Run transcription in executor to avoid blocking
            # Whisper transcribe() takes audio as first arg and keyword arguments
            loop = asyncio.get_event_loop()
            
            # Create a lambda to properly pass keyword arguments
            def transcribe_audio():
                if language:
                    return self.local_model.transcribe(audio_np, language=language)
                else:
                    return self.local_model.transcribe(audio_np)
            
            result = await loop.run_in_executor(None, transcribe_audio)
            
            transcript = result.get("text", "").strip()
            if transcript:
                logger.debug(f"[Whisper] Transcription result: {transcript[:50]}...")
            return transcript
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}", exc_info=True)
            return ""
    
    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        callback: Optional[Callable[[str, float], None]] = None
    ) -> AsyncGenerator[str, None]:
        """Transcribe audio stream in real-time"""
        buffer = b""
        chunk_duration = 1.0  # Process 1 second chunks
        threshold = 16000 * 2  # 16kHz, 16-bit samples = 32000 bytes
        
        async for chunk in audio_stream:
            buffer += chunk
            
            # Process when buffer reaches threshold
            # Process in chunks to avoid losing data if buffer exceeds threshold
            while len(buffer) >= threshold:
                chunk_to_process = buffer[:threshold]
                buffer = buffer[threshold:]
                
                transcript = await self.transcribe_audio_chunk(chunk_to_process)
                if transcript:
                    if callback:
                        callback(transcript, asyncio.get_event_loop().time())
                    yield transcript
        
        # Process remaining buffer
        if buffer:
            transcript = await self.transcribe_audio_chunk(buffer)
            if transcript:
                if callback:
                    callback(transcript, asyncio.get_event_loop().time())
                yield transcript


class AudioCaptureService:
    """Service for capturing system audio"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.is_recording = False
        self.audio_queue = asyncio.Queue()
    
    async def start_capture(self) -> AsyncGenerator[bytes, None]:
        """Start capturing system audio"""
        try:
            import pyaudio
        except ImportError:
            logger.error("PyAudio not available. Audio capture requires PyAudio installation.")
            return
        
        p = pyaudio.PyAudio()
        
        # Try to find default input device
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_recording = True
            total_bytes_captured = 0
            chunk_count = 0
            
            logger.info(f"[Audio Capture] Started system audio capture - Sample rate: {self.sample_rate}Hz, Channels: {self.channels}, Chunk size: {self.chunk_size}")
            
            try:
                while self.is_recording:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    chunk_count += 1
                    total_bytes_captured += len(data)
                    
                    # Continuous real-time logging - log every chunk
                    if chunk_count == 1:
                        logger.info(f"[Audio Capture] 🎤 System audio capture started - Chunk #{chunk_count}: {len(data)} bytes | Total: {total_bytes_captured} bytes")
                    else:
                        # Log every chunk at INFO level for continuous visibility
                        logger.info(f"[Audio Capture] 🎤 Chunk #{chunk_count}: {len(data)} bytes | Total: {total_bytes_captured} bytes | Buffer: {len(data)} bytes")
                    
                    yield data
            finally:
                logger.info(f"[Audio Capture] Stopped system audio capture - Total chunks: {chunk_count}, Total bytes: {total_bytes_captured}")
                stream.stop_stream()
                stream.close()
                p.terminate()
        except Exception as e:
            logger.error(f"[Audio Capture] Audio capture error: {e}", exc_info=True)
            raise
    
    def stop_capture(self):
        """Stop capturing audio"""
        self.is_recording = False

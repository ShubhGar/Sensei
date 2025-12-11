"""
Real-time transcription service using faster-whisper
Note: VAD (Voice Activity Detection) is disabled as it requires onnxruntime,
which is not yet available for Python 3.14
"""
import asyncio
import numpy as np
import subprocess
import re
from typing import Optional, Callable, AsyncGenerator
import os
from dotenv import load_dotenv
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

# Note: VAD is disabled - requires onnxruntime which doesn't support Python 3.14 yet

load_dotenv()


class PersistentFFmpegPipe:
    """Simplified FFmpeg conversion - optimized for speed"""
    
    def __init__(self):
        # No persistent process needed - use simple per-chunk conversion
        # but optimized for minimal overhead
        pass
    
    async def convert_chunk(self, webm_data: bytes) -> Optional[bytes]:
        """Convert WebM data to PCM - optimized fast conversion"""
        if not webm_data or len(webm_data) == 0:
            return None
        
        # Simplified FFmpeg command for speed
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'webm',
            '-i', 'pipe:0',
            '-f', 's16le',
            '-ar', '16000',
            '-ac', '1',
            '-loglevel', 'error',
            '-nostdin',
            'pipe:1'
        ]
        
        def run_ffmpeg():
            try:
                process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate(input=webm_data, timeout=5)
                
                if process.returncode == 0 and len(stdout) > 0:
                    return stdout
                return None
            except subprocess.TimeoutExpired:
                return None
            except Exception:
                return None
        
        loop = asyncio.get_event_loop()
        pcm_data = await loop.run_in_executor(None, run_ffmpeg)
        
        return pcm_data if pcm_data and len(pcm_data) > 0 else None
    
    async def start(self):
        """No-op for compatibility"""
        pass
    
    async def stop(self):
        """No-op for compatibility"""
        pass


class TranscriptionService:
    """Service for real-time audio transcription using faster-whisper
    Note: VAD is disabled as onnxruntime is not available for Python 3.14
    """
    
    # Sliding buffer configuration: 1-2 seconds at 16kHz
    # 1 second = 16000 samples = 32000 bytes (16-bit)
    # 2 seconds = 32000 samples = 64000 bytes (16-bit)
    SLIDING_BUFFER_SIZE = 32000  # 1 second at 16kHz = 32000 bytes
    SLIDING_BUFFER_OVERLAP = 16000  # 0.5 second overlap = 16000 bytes
    MAX_BUFFER_SIZE = int(os.getenv("MAX_TRANSCRIPTION_BUFFER_SIZE", "10485760"))  # 10MB default
    
    def __init__(self):
        self.local_model = None
        self.vad_model = None
        self.ffmpeg_pipe = PersistentFFmpegPipe()
        self._transcription_warning_logged = False
        self._lock = asyncio.Lock()
        
        logger.info("Initializing faster-whisper transcription service (VAD disabled - onnxruntime not available for Python 3.14)")
        
        # Load faster-whisper model (use small.en or distil-small.en for speed)
        if WhisperModel:
            model_name = os.getenv("LOCAL_WHISPER_MODEL", "distil-small.en")
            device = os.getenv("WHISPER_DEVICE", "cpu")  # cpu, cuda, auto
            compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8, int8_float16, int16, float16, float32
            
            try:
                logger.info(f"Loading faster-whisper model | Model: {model_name} | Device: {device} | Compute: {compute_type}")
                self.local_model = WhisperModel(
                    model_name,
                    device=device,
                    compute_type=compute_type
                )
                logger.info(f"faster-whisper model loaded successfully | Model: {model_name}")
            except Exception as e:
                logger.error(
                    f"Failed to load faster-whisper model | Model: {model_name} | "
                    f"Error: {type(e).__name__}: {str(e)}",
                    exc_info=True
                )
                self.local_model = None
        else:
            logger.error(
                "faster-whisper not available | Package not installed | "
                "Install with: pip install faster-whisper"
            )
            self.local_model = None
        
        if not self.local_model:
            logger.error("No transcription service available | faster-whisper model failed to load")
    
    async def convert_webm_to_pcm(self, webm_data: bytes) -> Optional[bytes]:
        """Convert WebM audio chunk to PCM format using persistent pipe
        
        Args:
            webm_data: WebM audio bytes from browser
            
        Returns:
            PCM audio bytes (16-bit, 16kHz, mono) or None if conversion fails
        """
        if len(webm_data) == 0:
            return None
        
        # WebM/Matroska files start with EBML header: 0x1A 0x45 0xDF 0xA3
        WEBM_HEADER = b'\x1a\x45\xdf\xa3'
        
        # Check if data starts with WebM header, if not try to find it
        if not webm_data.startswith(WEBM_HEADER):
            header_pos = webm_data.find(WEBM_HEADER)
            if header_pos > 0:
                logger.debug(f"WebM header found at position {header_pos}, trimming prefix")
                webm_data = webm_data[header_pos:]
            elif header_pos == -1:
                logger.warning(
                    f"WebM data does not contain EBML header | "
                    f"First 16 bytes: {webm_data[:16].hex()} | "
                    f"Size: {len(webm_data)} bytes"
                )
                return None
        
        try:
            # Use persistent FFmpeg pipe
            pcm_data = await self.ffmpeg_pipe.convert_chunk(webm_data)
            
            if not pcm_data or len(pcm_data) == 0:
                logger.debug(f"FFmpeg conversion produced no output | Input size: {len(webm_data)} bytes")
                return None
            
            logger.debug(
                f"WebM to PCM conversion successful | Input: {len(webm_data)} bytes | "
                f"Output: {len(pcm_data)} bytes | Ratio: {len(pcm_data)/len(webm_data):.2f}x"
            )
            return pcm_data
        except FileNotFoundError:
            logger.error(
                "FFmpeg not found | Please install ffmpeg | "
                "Install command: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
            )
            return None
        except Exception as e:
            logger.warning(
                f"Error during WebM conversion | Input size: {len(webm_data)} bytes | "
                f"Error: {type(e).__name__}: {str(e)}"
            )
            return None
    
    
    async def transcribe_audio_chunk(self, audio_data: bytes, language: Optional[str] = None, audio_format: Optional[str] = None) -> str:
        """Transcribe a single audio chunk
        
        Args:
            audio_data: Audio bytes (can be WebM/Opus from browser or raw PCM from system)
            language: Language code (optional, defaults to 'en' for English only)
            audio_format: Audio format hint (optional, e.g., 'webm' or 'pcm')
        """
        if not audio_data or len(audio_data) == 0:
            logger.debug("Empty audio data provided, skipping transcription")
            return ""
        
        # Force English language only
        language = language or "en"
        
        # Use faster-whisper if available
        if self.local_model:
            logger.debug(
                f"Starting transcription | Audio size: {len(audio_data)} bytes | "
                f"Format: {audio_format or 'unknown'} | Language: {language}"
            )
            return await self._transcribe_faster_whisper(audio_data, language, audio_format)
        
        # No service available
        async with self._lock:
            if not self._transcription_warning_logged:
                logger.warning(
                    "No transcription service available | Audio is being captured but not transcribed | "
                    "faster-whisper model not loaded"
                )
                self._transcription_warning_logged = True
        return ""
    
    
    async def _transcribe_faster_whisper(self, audio_data: bytes, language: Optional[str] = None, audio_format: Optional[str] = None) -> str:
        """Transcribe using faster-whisper model
        
        Args:
            audio_data: Audio bytes (can be WebM/Opus from browser or PCM from system)
            language: Language code (optional)
            audio_format: Audio format hint (optional, e.g., 'webm' or 'pcm')
        """
        if not self.local_model:
            return ""
        
        try:
            # Detect if audio is WebM/Opus (from browser) or PCM (from system)
            is_webm = audio_format == 'webm' or (len(audio_data) >= 4 and audio_data[:4] == b'\x1a\x45\xdf\xa3')
            
            if is_webm:
                logger.debug(f"Converting WebM audio to PCM | Input size: {len(audio_data)} bytes")
                audio_data = await self.convert_webm_to_pcm(audio_data)
                if not audio_data or len(audio_data) == 0:
                    logger.warning("WebM to PCM conversion failed or produced empty output")
                    return ""
            
            # Convert bytes to numpy array (PCM int16 format)
            if not audio_data or len(audio_data) == 0:
                return ""
            
            # Validate audio data length (must be even for int16)
            if len(audio_data) % 2 != 0:
                logger.warning(
                    f"Audio data length is not even, truncating | Original length: {len(audio_data)} bytes"
                )
                audio_data = audio_data[:-1]
            
            if len(audio_data) == 0:
                return ""
            
            try:
                # Convert to float32 and normalize to [-1.0, 1.0] range
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                if len(audio_np) == 0:
                    logger.debug("Empty audio array after conversion")
                    return ""
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Error converting audio data to numpy array | Error: {type(e).__name__}: {str(e)} | "
                    f"Audio data length: {len(audio_data)} bytes"
                )
                return ""
            
            # Calculate audio duration
            audio_duration = len(audio_np) / 16000.0  # 16kHz sample rate
            logger.debug(
                f"Audio duration | Duration: {audio_duration:.2f}s | Samples: {len(audio_np)}"
            )
            
            # Run transcription in executor
            loop = asyncio.get_event_loop()
            
            def transcribe_audio():
                try:
                    logger.info(
                        f"Starting faster-whisper transcription | Language: {language or 'auto'} | "
                        f"Duration: {audio_duration:.2f}s | Samples: {len(audio_np)}"
                    )
                    
                    # faster-whisper transcribe options - optimized for low latency
                    segments, info = self.local_model.transcribe(
                        audio_np,
                        language="en",  # Force English
                        beam_size=1,  # Low latency
                        temperature=0.0,
                        condition_on_previous_text=False,
                        word_timestamps=False,
                        vad_filter=False,  # Disabled: requires onnxruntime (not available for Python 3.14)
                    )
                    
                    logger.info(
                        f"faster-whisper transcription completed | Detected language: {info.language} | "
                        f"Probability: {info.language_probability:.2f}"
                    )
                    
                    # Collect transcript text from segments
                    transcript_parts = []
                    segment_count = 0
                    for segment in segments:
                        segment_count += 1
                        if segment.text and segment.text.strip():
                            transcript_parts.append(segment.text.strip())
                            logger.info(
                                f"Segment {segment_count} | Text: {segment.text.strip()[:50]} | "
                                f"Start: {segment.start:.2f}s | End: {segment.end:.2f}s"
                            )
                        else:
                            logger.info(
                                f"Segment {segment_count} | Empty/whitespace | "
                                f"Start: {segment.start:.2f}s | End: {segment.end:.2f}s | "
                                f"Raw text: {repr(segment.text[:30]) if segment.text else 'None'}"
                            )
                    
                    if segment_count == 0:
                        logger.debug(
                            f"No segments returned from faster-whisper | "
                            f"Duration: {audio_duration:.2f}s"
                        )
                    elif len(transcript_parts) == 0:
                        logger.warning(
                            f"Found {segment_count} segments but all were empty/whitespace | "
                            f"Duration: {audio_duration:.2f}s"
                        )
                    
                    transcript = " ".join(transcript_parts)
                    return transcript
                except Exception as e:
                    logger.error(
                        f"Error in transcribe_audio function | Error: {type(e).__name__}: {str(e)}",
                        exc_info=True
                    )
                    raise
            
            logger.debug("Running faster-whisper transcription in executor")
            transcript = await loop.run_in_executor(None, transcribe_audio)
            logger.debug(f"Transcription executor completed | Result available: {transcript is not None}")
            
            if not transcript or not transcript.strip():
                logger.warning("Transcription returned empty result")
                return ""
            
            transcript = transcript.strip()
            
            logger.info(
                f"Transcription successful | Text length: {len(transcript)} chars | "
                f"Preview: {transcript[:100]}"
            )
            
            return transcript
        except Exception as e:
            logger.error(
                f"faster-whisper transcription error | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return ""
    
    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        callback: Optional[Callable[[str, float], None]] = None
    ) -> AsyncGenerator[str, None]:
        """Transcribe audio stream in real-time using sliding buffer (1-2 seconds with overlap)"""
        buffer = b""
        
        async for chunk in audio_stream:
            buffer += chunk
            
            # Enforce buffer size limit to prevent memory issues
            if len(buffer) > self.MAX_BUFFER_SIZE:
                logger.warning(
                    f"Buffer exceeded max size, truncating | Current: {len(buffer)} bytes | "
                    f"Max: {self.MAX_BUFFER_SIZE} bytes"
                )
                buffer = buffer[-self.MAX_BUFFER_SIZE:]
            
            # Process when buffer reaches 1 second (with sliding window)
            while len(buffer) >= self.SLIDING_BUFFER_SIZE:
                # Take 1-2 seconds for processing
                chunk_size = min(len(buffer), self.SLIDING_BUFFER_SIZE * 2)  # Up to 2 seconds
                chunk_to_process = buffer[:chunk_size]
                
                # Slide buffer forward with overlap (keep last 0.5 seconds)
                buffer = buffer[chunk_size - self.SLIDING_BUFFER_OVERLAP:]
                
                transcript = await self.transcribe_audio_chunk(chunk_to_process, language='en')
                if transcript:
                    if callback:
                        callback(transcript, asyncio.get_event_loop().time())
                    yield transcript
        
        # Process remaining buffer
        if buffer and len(buffer) >= self.SLIDING_BUFFER_SIZE // 2:  # Process if at least 0.5 seconds
            transcript = await self.transcribe_audio_chunk(buffer, language='en')
            if transcript:
                if callback:
                    callback(transcript, asyncio.get_event_loop().time())
                yield transcript
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.ffmpeg_pipe.stop()


class AudioCaptureService:
    """Service for capturing system audio"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.is_recording = False
        self.audio_queue = asyncio.Queue()
        self._pyaudio = None
        self._stream = None
        self._ffmpeg_process = None  # Store FFmpeg process for cleanup
        # Allow fallback to default input device if system audio device not found
        self.allow_fallback = os.getenv("AUDIO_ALLOW_FALLBACK", "true").lower() == "true"
        # Manual device selection via environment variable (device index or name)
        self.manual_device = os.getenv("AUDIO_DEVICE", None)
        # Preferred capture method: 'pyaudio' or 'ffmpeg'
        self.capture_method = os.getenv("AUDIO_CAPTURE_METHOD", "ffmpeg").lower()  # Default to ffmpeg for better macOS support
    
    def _find_system_audio_device(self, p):
        """Find a system audio capture device (e.g., BlackHole)
        
        Returns:
            Device index if found, None otherwise
        """
        device_index = None
        device_name = None
        
        # List of common system audio device names (case-insensitive)
        # Includes virtual audio drivers and routing software
        system_audio_keywords = [
            'blackhole',
            'loopback',  # Rogue Amoeba Loopback
            'soundflower',
            'soundflowerbed',
            'virtual audio',
            'multi-output device',
            'aggregate device',
            'audio hijack',  # Rogue Amoeba Audio Hijack virtual devices
            'background music',  # Background Music app
            'soundflower (2ch)',
            'soundflower (16ch)',
            'vb-audio',  # VB-Audio Virtual Cable
            'virtual cable',
            'wasapi loopback',  # Windows WASAPI loopback
            'pulse loopback',  # Linux PulseAudio loopback
        ]
        
        # Check for manual device selection first
        if self.manual_device:
            try:
                # Try as device index
                if self.manual_device.isdigit():
                    device_index = int(self.manual_device)
                    if device_index < p.get_device_count():
                        info = p.get_device_info_by_index(device_index)
                        if info['maxInputChannels'] > 0:
                            logger.info(
                                f"Using manually specified device | Index: {device_index} | "
                                f"Name: {info['name']}"
                            )
                            return device_index
                        else:
                            logger.warning(
                                f"Manually specified device {device_index} has no input channels"
                            )
                else:
                    # Try as device name (partial match)
                    device_name_lower = self.manual_device.lower()
                    for i in range(p.get_device_count()):
                        try:
                            info = p.get_device_info_by_index(i)
                            if info['maxInputChannels'] > 0:
                                if device_name_lower in info['name'].lower():
                                    logger.info(
                                        f"Using manually specified device | Index: {i} | "
                                        f"Name: {info['name']}"
                                    )
                                    return i
                        except Exception:
                            continue
                    logger.warning(
                        f"Manually specified device '{self.manual_device}' not found"
                    )
            except Exception as e:
                logger.warning(
                    f"Error using manually specified device '{self.manual_device}': {e}"
                )
        
        logger.info("Scanning for system audio capture devices...")
        available_devices = []
        
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                # Check if device has input channels
                if info['maxInputChannels'] > 0:
                    device_name = info['name']
                    available_devices.append((i, device_name))
                    
                    # Check if device name matches system audio keywords
                    name_lower = device_name.lower()
                    for keyword in system_audio_keywords:
                        if keyword in name_lower:
                            logger.info(
                                f"Found system audio device | Index: {i} | Name: {device_name} | "
                                f"Input channels: {info['maxInputChannels']} | "
                                f"Sample rate: {info['defaultSampleRate']}"
                            )
                            device_index = i
                            break
                    
                    if device_index is not None:
                        break
            except Exception as e:
                logger.debug(f"Error getting device info for index {i}: {e}")
                continue
        
        if device_index is None:
            logger.warning(
                f"No system audio device found. Available input devices:\n" +
                "\n".join([f"  {idx}: {name}" for idx, name in available_devices])
            )
            logger.warning(
                "To capture system audio on macOS, you can use one of these methods:\n"
                "1. BlackHole (free): brew install blackhole-2ch\n"
                "2. Soundflower (free, older): https://github.com/mattingalls/Soundflower\n"
                "3. Loopback (paid): https://rogueamoeba.com/loopback/\n"
                "4. Audio Hijack (paid): https://rogueamoeba.com/loopback/\n"
                "\n"
                "After installing, create a Multi-Output Device in Audio MIDI Setup that includes\n"
                "the virtual audio device, then set it as your system output.\n"
                "\n"
                "You can also manually specify a device by setting AUDIO_DEVICE environment variable\n"
                "to the device index or name (partial match)."
            )
        else:
            logger.info(f"Using system audio device: {device_name} (index {device_index})")
        
        return device_index
    
    async def _start_capture_ffmpeg(self) -> AsyncGenerator[bytes, None]:
        """Start capturing system audio using FFmpeg (works on macOS without BlackHole)"""
        import platform
        
        # Detect OS and use appropriate FFmpeg input
        system = platform.system().lower()
        ffmpeg_input = None
        input_format = None
        ffmpeg_process = None
        
        try:
            if system == "darwin":  # macOS
                # Try to find BlackHole or other virtual audio device first
                # List available avfoundation devices
                try:
                    list_cmd = ['ffmpeg', '-f', 'avfoundation', '-list_devices', 'true', '-i', '']
                    list_process = subprocess.run(
                        list_cmd,
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        timeout=5
                    )
                    stderr_output = list_process.stderr.decode('utf-8', errors='ignore')
                    
                    # Look for BlackHole or other virtual audio devices in the output
                    blackhole_found = False
                    device_name = None
                    for line in stderr_output.split('\n'):
                        line_lower = line.lower()
                        if any(keyword in line_lower for keyword in ['blackhole', 'loopback', 'soundflower', 'virtual']):
                            # Extract device index (usually appears as [index] device_name)
                            match = re.search(r'\[(\d+)\]\s+(.+)', line)
                            if match:
                                device_index = match.group(1)
                                device_name = match.group(2).strip()
                                if 'blackhole' in line_lower or 'loopback' in line_lower:
                                    ffmpeg_input = f":{device_index}"
                                    blackhole_found = True
                                    logger.info(f"Found virtual audio device: {device_name} (index {device_index})")
                                    break
                except Exception as e:
                    logger.debug(f"Could not list avfoundation devices: {e}")
                
                # If no virtual device found, try to use system audio capture
                if not blackhole_found:
                    # On macOS, capturing system audio directly is tricky
                    # :0 with avfoundation typically captures microphone, not system audio
                    # For true system audio, we need BlackHole or screen recording permissions
                    # Try :0 but warn that it might not work for system audio
                    ffmpeg_input = ":0"
                    logger.warning(
                        "No virtual audio device (BlackHole) found. Attempting to use default audio device.\n"
                        "Note: This may capture microphone audio, not system audio.\n"
                        "For true system audio capture, please install BlackHole: brew install blackhole-2ch\n"
                        "Then create a Multi-Output Device in Audio MIDI Setup."
                    )
                
                input_format = "avfoundation"
                logger.info(f"Using FFmpeg with avfoundation to capture macOS system audio | Input: {ffmpeg_input}")
            elif system == "linux":
                # Use pulseaudio loopback (if available)
                ffmpeg_input = "pulse"
                input_format = "pulse"
                logger.info("Using FFmpeg with pulseaudio to capture Linux system audio")
            elif system == "windows":
                # Use wasapi loopback
                ffmpeg_input = "default"
                input_format = "wasapi"
                logger.info("Using FFmpeg with WASAPI to capture Windows system audio")
            else:
                raise RuntimeError(f"FFmpeg system audio capture not supported on {system}")
            
            # Build FFmpeg command
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', input_format,
                '-i', ffmpeg_input,
                '-f', 's16le',  # 16-bit signed little-endian PCM
                '-ar', str(self.sample_rate),  # Sample rate
                '-ac', str(self.channels),  # Channels
                '-loglevel', 'error',  # Suppress verbose output
                '-nostdin',  # Non-interactive
                'pipe:1'  # Output to stdout
            ]
            
            logger.info(f"Starting FFmpeg system audio capture | Command: {' '.join(ffmpeg_cmd)}")
            
            # Start FFmpeg process
            ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=self.chunk_size
            )
            self._ffmpeg_process = ffmpeg_process  # Store for cleanup
            
            self.is_recording = True
            total_bytes_captured = 0
            chunk_count = 0
            
            logger.info(
                f"Started FFmpeg system audio capture | Sample rate: {self.sample_rate}Hz | "
                f"Channels: {self.channels} | Chunk size: {self.chunk_size} bytes"
            )
            
            try:
                loop = asyncio.get_event_loop()
                
                while self.is_recording:
                    # Read audio data from FFmpeg stdout (non-blocking)
                    def read_chunk():
                        return ffmpeg_process.stdout.read(self.chunk_size)
                    
                    data = await loop.run_in_executor(None, read_chunk)
                    
                    if not data:
                        # Check if process has terminated
                        if ffmpeg_process.poll() is not None:
                            stderr_output = b""
                            try:
                                stderr_output = ffmpeg_process.stderr.read()
                            except:
                                pass
                            if stderr_output:
                                error_text = stderr_output.decode('utf-8', errors='ignore')
                                logger.error(f"FFmpeg process terminated | stderr: {error_text}")
                            else:
                                logger.warning("FFmpeg process terminated unexpectedly")
                            break
                        # No data available, wait a bit
                        await asyncio.sleep(0.01)
                        continue
                    
                    chunk_count += 1
                    total_bytes_captured += len(data)
                    
                    # Log first chunk and then every 100 chunks at INFO level, others at DEBUG
                    if chunk_count == 1:
                        logger.info(
                            f"FFmpeg system audio capture started | Chunk #{chunk_count} | "
                            f"Size: {len(data)} bytes | Total: {total_bytes_captured} bytes"
                        )
                    elif chunk_count % 100 == 0:
                        logger.info(
                            f"FFmpeg system audio capture progress | Chunk #{chunk_count} | "
                            f"Size: {len(data)} bytes | Total: {total_bytes_captured} bytes"
                        )
                    else:
                        logger.debug(
                            f"FFmpeg system audio chunk | Chunk #{chunk_count} | "
                            f"Size: {len(data)} bytes | Total: {total_bytes_captured} bytes"
                        )
                    
                    yield data
            finally:
                logger.info(
                    f"Stopped FFmpeg system audio capture | Total chunks: {chunk_count} | "
                    f"Total bytes: {total_bytes_captured}"
                )
                if ffmpeg_process:
                    try:
                        ffmpeg_process.terminate()
                        # Wait for process to terminate (with timeout)
                        try:
                            ffmpeg_process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            logger.warning("FFmpeg process did not terminate, forcing kill")
                            ffmpeg_process.kill()
                            ffmpeg_process.wait()
                    except Exception as e:
                        logger.warning(
                            f"Error terminating FFmpeg process | Error: {type(e).__name__}: {str(e)}"
                        )
        except FileNotFoundError:
            error_msg = (
                "FFmpeg not found | System audio capture requires FFmpeg | "
                "Install with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            logger.error(
                f"FFmpeg audio capture error | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            if ffmpeg_process:
                try:
                    ffmpeg_process.terminate()
                    ffmpeg_process.wait(timeout=1)
                except:
                    try:
                        ffmpeg_process.kill()
                    except:
                        pass
            raise
    
    async def start_capture(self) -> AsyncGenerator[bytes, None]:
        """Start capturing system audio with proper resource cleanup"""
        # Use FFmpeg if specified, otherwise use PyAudio
        if self.capture_method == "ffmpeg":
            async for chunk in self._start_capture_ffmpeg():
                yield chunk
            return
        
        # PyAudio-based capture (original implementation)
        try:
            import pyaudio
        except ImportError:
            error_msg = (
                "PyAudio not available | Audio capture requires PyAudio installation | "
                "Install with: pip install pyaudio | "
                "Alternatively, set AUDIO_CAPTURE_METHOD=ffmpeg to use FFmpeg instead"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        p = pyaudio.PyAudio()
        self._pyaudio = p
        stream = None
        
        try:
            # Find system audio device (e.g., BlackHole)
            device_index = self._find_system_audio_device(p)
            device_name = "system audio device"
            use_default = False
            
            if device_index is None:
                if self.allow_fallback:
                    # Fall back to default input device
                    try:
                        default_device = p.get_default_input_device_info()
                        device_index = default_device['index']
                        device_name = default_device['name']
                        use_default = True
                        logger.warning(
                            f"No system audio device (BlackHole) found. Falling back to default input device: {device_name}\n"
                            f"Note: This will capture from your microphone, not system audio.\n"
                            f"To capture true system audio, either:\n"
                            f"1. Install BlackHole: brew install blackhole-2ch\n"
                            f"2. Set AUDIO_CAPTURE_METHOD=ffmpeg to use FFmpeg (works without BlackHole on macOS)"
                        )
                    except Exception as e:
                        error_msg = (
                            f"Failed to get default input device: {str(e)}\n"
                            "No system audio device found and default input device is unavailable.\n"
                            "Try setting AUDIO_CAPTURE_METHOD=ffmpeg to use FFmpeg instead."
                        )
                        logger.error(error_msg)
                        raise RuntimeError(error_msg) from e
                else:
                    error_msg = (
                        "No system audio capture device found. Please install and configure BlackHole:\n"
                        "1. Install: brew install blackhole-2ch\n"
                        "2. Create Multi-Output Device in Audio MIDI Setup\n"
                        "3. Include BlackHole in Multi-Output Device\n"
                        "4. Set system output to Multi-Output Device\n\n"
                        "Alternatively, set AUDIO_CAPTURE_METHOD=ffmpeg to use FFmpeg (works without BlackHole on macOS)\n"
                        "or set AUDIO_ALLOW_FALLBACK=true to use default input device."
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
            
            # Open stream with the selected device
            try:
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=self.chunk_size
                )
                self._stream = stream
                device_type = "default input" if use_default else "system audio"
                logger.info(
                    f"Opened {device_type} stream | Device: {device_name} (index {device_index}) | "
                    f"Sample rate: {self.sample_rate}Hz | Channels: {self.channels}"
                )
            except Exception as e:
                error_msg = (
                    f"Failed to open audio device '{device_name}' (index {device_index}): {str(e)}\n"
                    "Make sure the device is available and not in use by another application.\n"
                    "Try setting AUDIO_CAPTURE_METHOD=ffmpeg to use FFmpeg instead."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e
            
            self.is_recording = True
            total_bytes_captured = 0
            chunk_count = 0
            
            logger.info(
                f"Started system audio capture | Sample rate: {self.sample_rate}Hz | "
                f"Channels: {self.channels} | Chunk size: {self.chunk_size} bytes"
            )
            
            try:
                while self.is_recording:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    chunk_count += 1
                    total_bytes_captured += len(data)
                    
                    # Log first chunk and then every 100 chunks at INFO level, others at DEBUG
                    if chunk_count == 1:
                        logger.info(
                            f"System audio capture started | Chunk #{chunk_count} | "
                            f"Size: {len(data)} bytes | Total: {total_bytes_captured} bytes"
                        )
                    elif chunk_count % 100 == 0:
                        logger.info(
                            f"System audio capture progress | Chunk #{chunk_count} | "
                            f"Size: {len(data)} bytes | Total: {total_bytes_captured} bytes"
                        )
                    else:
                        logger.debug(
                            f"System audio chunk | Chunk #{chunk_count} | "
                            f"Size: {len(data)} bytes | Total: {total_bytes_captured} bytes"
                        )
                    
                    yield data
            finally:
                logger.info(
                    f"Stopped system audio capture | Total chunks: {chunk_count} | "
                    f"Total bytes: {total_bytes_captured}"
                )
                if stream:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception as e:
                        logger.warning(
                            f"Error closing audio stream | Error: {type(e).__name__}: {str(e)}"
                        )
                if p:
                    try:
                        p.terminate()
                    except Exception as e:
                        logger.warning(
                            f"Error terminating PyAudio | Error: {type(e).__name__}: {str(e)}"
                        )
        except Exception as e:
            logger.error(
                f"Audio capture error | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            # Ensure cleanup even on error
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if p:
                try:
                    p.terminate()
                except Exception:
                    pass
            raise
        finally:
            self._pyaudio = None
            self._stream = None
    
    def stop_capture(self):
        """Stop capturing audio"""
        self.is_recording = False
        # Also try to clean up resources if they exist
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None
        if self._ffmpeg_process:
            try:
                self._ffmpeg_process.terminate()
                try:
                    self._ffmpeg_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._ffmpeg_process.kill()
                    self._ffmpeg_process.wait()
            except Exception:
                pass
            self._ffmpeg_process = None

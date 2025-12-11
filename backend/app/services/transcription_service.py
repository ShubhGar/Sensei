"""
Real-time transcription service using Whisper
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
    import whisper
except ImportError:
    whisper = None

load_dotenv()


class TranscriptionService:
    """Service for real-time audio transcription using Whisper"""
    
    # Configurable thresholds (can be overridden via environment variables)
    SILENCE_THRESHOLD_MAX = float(os.getenv("SILENCE_THRESHOLD_MAX", "0.05"))
    SILENCE_THRESHOLD_RMS = float(os.getenv("SILENCE_THRESHOLD_RMS", "0.02"))
    MIN_AUDIO_DURATION = float(os.getenv("MIN_AUDIO_DURATION", "1.0"))
    MAX_BUFFER_SIZE = int(os.getenv("MAX_TRANSCRIPTION_BUFFER_SIZE", "10485760"))  # 10MB default
    FFMPEG_TIMEOUT = int(os.getenv("FFMPEG_TIMEOUT", "10"))  # 10 seconds default
    
    # Hallucination patterns (can be extended)
    # Disabled - too aggressive, rejecting valid speech
    HALLUCINATION_PATTERNS = []
    
    def __init__(self):
        self.local_model = None
        self._transcription_warning_logged = False
        self._lock = asyncio.Lock()  # Thread-safe lock for shared state
        
        logger.info("Initializing Whisper transcription service")
        
        # Load Whisper model
        if whisper:
            model_name = os.getenv("LOCAL_WHISPER_MODEL", "base")
            try:
                logger.info(f"Loading Whisper model | Model: {model_name}")
                self.local_model = whisper.load_model(model_name)
                logger.info(f"Whisper model loaded successfully | Model: {model_name}")
            except Exception as e:
                logger.error(
                    f"Failed to load Whisper model | Model: {model_name} | "
                    f"Error: {type(e).__name__}: {str(e)}",
                    exc_info=True
                )
                self.local_model = None
        else:
            logger.error(
                "Whisper not available | Package not installed | "
                "Install with: pip install openai-whisper"
            )
            self.local_model = None
        
        if not self.local_model:
            logger.error("No transcription service available | Whisper model failed to load")
    
    async def convert_webm_to_pcm(self, webm_data: bytes) -> Optional[bytes]:
        """Convert WebM audio chunk to PCM format
        
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
            # Try to find WebM header in the data
            header_pos = webm_data.find(WEBM_HEADER)
            if header_pos > 0:
                logger.debug(f"WebM header found at position {header_pos}, trimming prefix")
                webm_data = webm_data[header_pos:]
            elif header_pos == -1:
                # No WebM header found - this might be a cluster fragment
                # Try to prepend a minimal WebM header structure
                # However, this is complex - better to skip and wait for header chunk
                logger.warning(
                    f"WebM data does not contain EBML header | "
                    f"First 16 bytes: {webm_data[:16].hex()} | "
                    f"Size: {len(webm_data)} bytes"
                )
                return None
            
        try:
            # Use FFmpeg with settings optimized for fragmented WebM from MediaRecorder
            # MediaRecorder sends fragmented WebM: first chunk has initialization, subsequent are clusters
            # Use 'webm' format specifically for better fragmented WebM support
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'webm',  # Use webm format specifically for fragmented WebM
                '-err_detect', 'ignore_err',
                '-fflags', '+genpts+discardcorrupt+igndts+ignidx+flush_packets',
                '-avoid_negative_ts', 'make_zero',
                '-analyzeduration', '5000000',  # Increased to better handle accumulated fragments
                '-probesize', '5000000',  # Increased to better handle accumulated fragments
                '-i', 'pipe:0',
                '-f', 's16le',
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-af', 'aresample=resampler=soxr:precision=28:cheby=1',
                '-loglevel', 'error',
                '-nostdin',
                'pipe:1'
            ]
            
            def run_ffmpeg():
                try:
                    with subprocess.Popen(
                        ffmpeg_cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    ) as process:
                        stdout, stderr = process.communicate(input=webm_data, timeout=self.FFMPEG_TIMEOUT)
                        
                        if len(stdout) > 0:
                            return stdout
                        
                        if process.returncode != 0:
                            error_msg = stderr.decode('utf-8', errors='ignore') if stderr else f"FFmpeg returned {process.returncode}"
                            logger.warning(
                                f"FFmpeg conversion failed | Return code: {process.returncode} | "
                                f"Error: {error_msg[:200]} | Input size: {len(webm_data)} bytes"
                            )
                            return None
                        
                        return stdout
                except subprocess.TimeoutExpired:
                    logger.warning(
                        f"FFmpeg conversion timed out | Input size: {len(webm_data)} bytes | "
                        f"Timeout: {self.FFMPEG_TIMEOUT}s"
                    )
                    return None
                except Exception as e:
                    logger.warning(
                        f"FFmpeg process error | Input size: {len(webm_data)} bytes | "
                        f"Error: {type(e).__name__}: {str(e)}"
                    )
                    return None
            
            loop = asyncio.get_event_loop()
            pcm_data = await loop.run_in_executor(None, run_ffmpeg)
            
            if not pcm_data or len(pcm_data) == 0:
                logger.warning(
                    f"FFmpeg conversion produced no output | Input size: {len(webm_data)} bytes"
                )
                return None
            
            logger.info(
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
        
        # Use Whisper if available
        if self.local_model:
            logger.debug(
                f"Starting transcription | Audio size: {len(audio_data)} bytes | "
                f"Format: {audio_format or 'unknown'} | Language: {language}"
            )
            return await self._transcribe_whisper(audio_data, language, audio_format)
        
        # No service available
        async with self._lock:
            if not self._transcription_warning_logged:
                logger.warning(
                    "No transcription service available | Audio is being captured but not transcribed | "
                    "Whisper model not loaded"
                )
                self._transcription_warning_logged = True
        return ""
    
    def _is_hallucination(self, transcript: str) -> bool:
        """Check if transcript matches known hallucination patterns or repetitive patterns"""
        if not transcript or len(transcript.strip()) == 0:
            return False
        
        transcript_lower = transcript.lower()
        transcript_clean = transcript.strip()
        
        # Check against known English hallucination patterns (substring match)
        for pattern in self.HALLUCINATION_PATTERNS:
            if pattern.lower() in transcript_lower:
                logger.info(
                    f"Rejecting transcript - hallucination pattern match | Pattern: {pattern} | "
                    f"Transcript preview: {transcript[:100]}"
                )
                return True
        
        # Detect phrase/sentence-level repetition
        # Disabled - too aggressive, rejecting valid speech patterns
        # Split by sentence delimiters
        # sentences = re.split(r'[.!?。！？]\s*', transcript_clean)
        # sentences = [s.strip() for s in sentences if s.strip()]
        # 
        # if len(sentences) > 1:
        #     # Normalize sentences for comparison (lowercase, remove extra whitespace)
        #     normalized_sentences = [re.sub(r'\s+', ' ', s.lower().strip()) for s in sentences]
        #     
        #     # Count sentence occurrences
        #     sentence_counts = {}
        #     for sent in normalized_sentences:
        #         if len(sent) > 5:  # Only consider sentences longer than 5 chars
        #             sentence_counts[sent] = sentence_counts.get(sent, 0) + 1
        #     
        #     # If the same sentence appears 2+ times, it's likely a hallucination
        #     for sent, count in sentence_counts.items():
        #         if count >= 2:
        #             logger.info(f"[TranscriptionService] Rejecting transcript - repeated sentence ({count} times): '{sent[:80]}...'")
        #             return True
        
        # Detect phrase-level repetition (3+ word phrases)
        # Split into words
        words = re.findall(r'\S+', transcript_clean)
        
        if len(words) == 0:
            return False
        
        # Check for repeated phrases (3-6 words long)
        # Disabled - too aggressive, rejecting valid speech patterns
        # phrase_lengths = [3, 4, 5, 6]
        # for phrase_len in phrase_lengths:
        #     if len(words) < phrase_len * 2:  # Need at least 2 occurrences
        #         continue
        #     
        #     phrases = {}
        #     for i in range(len(words) - phrase_len + 1):
        #         phrase = ' '.join(words[i:i+phrase_len]).lower()
        #         # Normalize phrase (remove punctuation differences)
        #         phrase_normalized = re.sub(r'[^\w\s]', '', phrase)
        #         if len(phrase_normalized.strip()) > 0:
        #             phrases[phrase_normalized] = phrases.get(phrase_normalized, 0) + 1
        #     
        #     # If a phrase appears 2+ times, it's suspicious
        #     for phrase, count in phrases.items():
        #         if count >= 2 and len(phrase.split()) >= 3:  # At least 3 words, repeated 2+ times
        #             logger.info(f"[TranscriptionService] Rejecting transcript - repeated phrase ({count} times): '{phrase[:80]}...'")
        #             return True
        
        # Check if the same word/phrase is repeated many times
        # Count occurrences of each unique word
        word_counts = {}
        for word in words:
            # Normalize word (remove common punctuation, but keep Unicode letters/characters)
            normalized = re.sub(r'[،,.\-_\s]+', '', word).lower()
            if normalized and len(normalized) > 0:
                word_counts[normalized] = word_counts.get(normalized, 0) + 1
        
        # If we have very few unique words but many total words, it's likely repetitive
        unique_words = len([w for w in word_counts.values() if w > 0])
        total_words = len(words)
        
        # Threshold: if more than 90% of words are the same, it's likely a hallucination (relaxed from 70%)
        # Only check for very extreme cases
        if unique_words > 0 and total_words > 10:  # Increased minimum word count
            repetition_ratio = max(word_counts.values()) / total_words
            if repetition_ratio > 0.9:  # Increased threshold from 0.7 to 0.9
                logger.info(
                    f"Rejecting transcript - high repetition ratio | Ratio: {repetition_ratio:.2f} | "
                    f"Unique words: {unique_words}/{total_words} | Transcript preview: {transcript[:100]}"
                )
                return True
        
        # Check for excessive repetition of short words/phrases (2-4 characters)
        # This catches patterns like "أهي" repeated many times
        # Made more lenient - only reject if same word appears 20+ times (increased from 10)
        for word, count in word_counts.items():
            if len(word) <= 4 and count >= 20:  # Short word repeated 20+ times (increased from 10)
                logger.info(
                    f"Rejecting transcript - excessive short word repetition | Word: '{word}' | "
                    f"Count: {count} | Transcript preview: {transcript[:100]}"
                )
                return True
        
        # Check for exact repetition of the same sequence (e.g., "word, word, word" pattern)
        # Look for patterns where the same word appears consecutively many times
        consecutive_repeats = 1
        max_consecutive = 1
        prev_word = None
        
        for word in words:
            normalized = re.sub(r'[،,.\-_\s]+', '', word).lower()
            if normalized and normalized == prev_word:
                consecutive_repeats += 1
                max_consecutive = max(max_consecutive, consecutive_repeats)
            else:
                consecutive_repeats = 1
            prev_word = normalized
        
        # If the same word appears 15+ times consecutively, it's likely noise (increased from 8)
        # This allows for natural repetition like "hello, hello, hello" in greetings
        if max_consecutive >= 15:  # Increased from 8 to allow more natural repetition
            logger.info(
                f"Rejecting transcript - excessive consecutive repetition | "
                f"Max consecutive: {max_consecutive} | Transcript preview: {transcript[:100]}"
            )
            return True
        
        return False
    
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
            
            # Check if audio is long enough
            audio_duration = len(audio_np) / 16000.0  # 16kHz sample rate
            logger.debug(
                f"Audio duration check | Duration: {audio_duration:.2f}s | "
                f"Samples: {len(audio_np)} | Min required: {self.MIN_AUDIO_DURATION}s"
            )
            
            if audio_duration < self.MIN_AUDIO_DURATION:
                logger.debug(
                    f"Audio chunk too short, skipping | Duration: {audio_duration:.2f}s | "
                    f"Min required: {self.MIN_AUDIO_DURATION}s"
                )
                return ""
            
            # Check if audio has any meaningful signal (not just silence or noise)
            audio_max = np.abs(audio_np).max()
            audio_rms = np.sqrt(np.mean(audio_np**2))
            audio_std = np.std(audio_np)
            
            logger.debug(
                f"Audio analysis | Max: {audio_max:.4f} | RMS: {audio_rms:.4f} | "
                f"Std: {audio_std:.4f} | Duration: {audio_duration:.2f}s"
            )
            
            # Silence detection using configurable thresholds
            if audio_max < self.SILENCE_THRESHOLD_MAX or audio_rms < self.SILENCE_THRESHOLD_RMS:
                logger.debug(
                    f"Audio appears to be silence/noise, skipping | Max: {audio_max:.4f} | "
                    f"RMS: {audio_rms:.4f} | Thresholds: max={self.SILENCE_THRESHOLD_MAX}, "
                    f"rms={self.SILENCE_THRESHOLD_RMS}"
                )
                return ""
            
            # Check if audio is mostly noise
            if audio_std < 0.02 and audio_max < 0.1:
                logger.debug(
                    f"Audio appears to be low-level noise, skipping | Std: {audio_std:.4f} | "
                    f"Max: {audio_max:.4f}"
                )
                return ""
            
            # Normalize audio to improve transcription quality
            if audio_max > self.SILENCE_THRESHOLD_MAX and audio_max < 0.3:
                normalization_factor = min(0.7 / audio_max, 3.0)
                audio_np = audio_np * normalization_factor
                logger.debug(
                    f"Audio normalized | Factor: {normalization_factor:.2f} | "
                    f"Original max: {audio_max:.4f} | New max: {np.abs(audio_np).max():.4f}"
                )
            
            # Run transcription in executor
            loop = asyncio.get_event_loop()
            
            def transcribe_audio():
                try:
                    logger.info(
                        f"Starting Whisper transcription | Language: {language or 'auto'} | "
                        f"Duration: {audio_duration:.2f}s | Samples: {len(audio_np)}"
                    )
                    
                    transcribe_kwargs = {
                        "temperature": 0.0,
                        "beam_size": 5,
                        "best_of": 5,
                        "condition_on_previous_text": False,
                        "compression_ratio_threshold": 2.4,
                        "logprob_threshold": -1.0,
                        "no_speech_threshold": 0.5,
                        "word_timestamps": False,
                        "language": "en",  # Always force English language
                    }
                    
                    result = self.local_model.transcribe(audio_np, **transcribe_kwargs)
                    logger.debug(
                        f"Whisper transcription completed | Result type: {type(result).__name__}"
                    )
                    
                    if isinstance(result, dict):
                        if "segments" in result:
                            logger.debug(f"Transcription segments: {len(result['segments'])}")
                        if "language" in result:
                            logger.debug(f"Detected language: {result['language']}")
                    
                    return result
                except Exception as e:
                    logger.error(
                        f"Error in transcribe_audio function | Error: {type(e).__name__}: {str(e)}",
                        exc_info=True
                    )
                    raise
            
            logger.debug("Running Whisper transcription in executor")
            result = await loop.run_in_executor(None, transcribe_audio)
            logger.debug(f"Transcription executor completed | Result available: {result is not None}")
            
            if not result:
                logger.warning("Transcription returned empty result")
                return ""
            
            transcript = result.get("text", "").strip() if isinstance(result, dict) else ""
            
            # Check if Whisper detected that there's no speech
            if isinstance(result, dict):
                no_speech_prob = result.get("no_speech_prob", 0.0)
                language_prob = result.get("language_prob", 0.0) if "language_prob" in result else None
                avg_logprob = result.get("avg_logprob", -float('inf')) if "avg_logprob" in result else None
                
                if no_speech_prob > 0.5:
                    logger.debug(
                        f"Rejecting transcript - no speech detected | no_speech_prob: {no_speech_prob:.2f} | "
                        f"Transcript preview: {transcript[:50]}"
                    )
                    return ""
                
                if avg_logprob is not None and avg_logprob < -1.5:
                    logger.debug(
                        f"Rejecting transcript - low confidence | avg_logprob: {avg_logprob:.2f} | "
                        f"Transcript preview: {transcript[:50]}"
                    )
                    return ""
                
                # Validate transcript for hallucination patterns
                if transcript and self._is_hallucination(transcript):
                    logger.info(
                        f"Rejecting transcript - hallucination detected | Transcript preview: {transcript[:50]} | "
                        f"Audio stats: max={audio_max:.4f}, RMS={audio_rms:.4f}, std={audio_std:.4f}, "
                        f"no_speech_prob={no_speech_prob:.2f}"
                    )
                    return ""
                
                # Log confidence metrics
                if transcript:
                    lang_prob_str = f"{language_prob:.2f}" if language_prob is not None else "N/A"
                    logger.info(
                        f"Transcription successful | no_speech_prob: {no_speech_prob:.2f} | "
                        f"language_prob: {lang_prob_str} | Text length: {len(transcript)} chars | "
                        f"Preview: {transcript[:100]}"
                    )
                else:
                    logger.warning(
                        f"Transcription returned empty text | Result keys: {list(result.keys())} | "
                        f"Segments: {len(result.get('segments', []))}"
                    )
            else:
                if transcript:
                    logger.info(
                        f"Transcription successful | Text length: {len(transcript)} chars | "
                        f"Preview: {transcript[:100]}"
                    )
                else:
                    logger.warning(
                        f"Transcription returned empty text | Result type: {type(result).__name__}"
                    )
            
            return transcript
        except Exception as e:
            logger.error(
                f"Whisper transcription error | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return ""
    
    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        callback: Optional[Callable[[str, float], None]] = None
    ) -> AsyncGenerator[str, None]:
        """Transcribe audio stream in real-time with buffer size limits"""
        buffer = b""
        chunk_duration = 1.0  # Process 1 second chunks
        threshold = 16000 * 2  # 16kHz, 16-bit samples = 32000 bytes
        
        async for chunk in audio_stream:
            buffer += chunk
            
            # Enforce buffer size limit to prevent memory issues
            if len(buffer) > self.MAX_BUFFER_SIZE:
                logger.warning(
                    f"Buffer exceeded max size, truncating | Current: {len(buffer)} bytes | "
                    f"Max: {self.MAX_BUFFER_SIZE} bytes"
                )
                buffer = buffer[-self.MAX_BUFFER_SIZE:]
            
            # Process when buffer reaches threshold
            while len(buffer) >= threshold:
                chunk_to_process = buffer[:threshold]
                buffer = buffer[threshold:]
                
                transcript = await self.transcribe_audio_chunk(chunk_to_process, language='en')
                if transcript:
                    if callback:
                        callback(transcript, asyncio.get_event_loop().time())
                    yield transcript
        
        # Process remaining buffer
        if buffer:
            transcript = await self.transcribe_audio_chunk(buffer, language='en')
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
        self._pyaudio = None
        self._stream = None
        # Allow fallback to default input device if system audio device not found
        self.allow_fallback = os.getenv("AUDIO_ALLOW_FALLBACK", "true").lower() == "true"
        # Manual device selection via environment variable (device index or name)
        self.manual_device = os.getenv("AUDIO_DEVICE", None)
        # Preferred capture method: 'pyaudio' or 'ffmpeg'
        self.capture_method = os.getenv("AUDIO_CAPTURE_METHOD", "pyaudio").lower()
    
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
                "4. Audio Hijack (paid): https://rogueamoeba.com/audiohijack/\n"
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
    
    async def start_capture(self) -> AsyncGenerator[bytes, None]:
        """Start capturing system audio with proper resource cleanup"""
        try:
            import pyaudio
        except ImportError:
            error_msg = (
                "PyAudio not available | Audio capture requires PyAudio installation | "
                "Install with: pip install pyaudio"
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
                            f"To capture true system audio, install BlackHole: brew install blackhole-2ch"
                        )
                    except Exception as e:
                        error_msg = (
                            f"Failed to get default input device: {str(e)}\n"
                            "No system audio device found and default input device is unavailable."
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
                        "Alternatively, set AUDIO_ALLOW_FALLBACK=true to use default input device."
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
                    "Make sure the device is available and not in use by another application."
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

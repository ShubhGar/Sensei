"""
Assembly AI real-time transcription service
Provides high-accuracy speech-to-text with speaker diarization
"""
import asyncio
import json
import os
import websockets
from typing import Optional, Callable, AsyncGenerator
from dotenv import load_dotenv
from app.utils.logger import get_logger

logger = get_logger(__name__)
load_dotenv()


class AssemblyAIService:
    """Assembly AI real-time transcription service"""
    
    def __init__(self):
        self.api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
        self.base_url = "wss://api.assemblyai.com/v2/realtime/ws"
        self.sample_rate = 16000
        self.websocket = None
        self.is_connected = False
        self.transcript_callback: Optional[Callable] = None
        
        if not self.api_key:
            logger.warning("AssemblyAI API key not configured. Set ASSEMBLYAI_API_KEY in .env file")
        else:
            logger.info("AssemblyAI service initialized")
    
    async def connect(self, transcript_callback: Optional[Callable] = None):
        """
        Connect to Assembly AI real-time WebSocket
        
        Args:
            transcript_callback: Optional callback function(text: str, is_final: bool) for transcript updates
        """
        if not self.api_key:
            raise ValueError("AssemblyAI API key not configured")
        
        self.transcript_callback = transcript_callback
        
        # Assembly AI WebSocket URL with API key
        url = f"{self.base_url}?sample_rate={self.sample_rate}"
        headers = {"Authorization": self.api_key}
        
        try:
            logger.info(f"Connecting to AssemblyAI WebSocket: {url}")
            self.websocket = await websockets.connect(url, extra_headers=headers)
            self.is_connected = True
            logger.info("✅ Connected to AssemblyAI WebSocket")
            
            # Configure the session with enhanced settings for better accuracy
            config = {
                "sample_rate": self.sample_rate,
                "word_boost": [
                    # Company and product names
                    "PayU", "Sensei", "JIRA", "API", "SDK", 
                    "checkoutpro", "CheckoutPro", "checkout pro", "Checkout Pro",
                    "checkout", "Checkout", "SDK", "sdk",
                    "PayU", "payu", "PayU India", "PayU India",
                    # Platform names
                    "Android", "iOS", "React Native", "Flutter",
                    # Technical terms
                    "merchant", "payment", "transaction", "integration",
                    "Bharatkosh", "bharatkosh", "UPI", "upi",
                    "3DS", "3ds", "MFA", "mfa", "TPAP", "tpap",
                    # Wallet and SDK terms
                    "wallet", "Wallet", "wallet SDK", "Wallet SDK", "wallet SDK DOC", "Wallet SDK DOC",
                    "Mia", "mia", "Mia wallet", "Mia Wallet",
                    # Common names
                    "Akash", "akash",
                    # Common phrases
                    "what is the status", "what's the status", "status of", "did you finish", "did you finished",
                    "when are you planning", "planning to finish", "ETA", "eta"
                ],  # Boost domain-specific terms for better recognition
                "speaker_labels": False,  # Disable speaker diarization to avoid false speaker separation
                "punctuate": True,  # Add punctuation
                "format_text": True,  # Format text properly
                "auto_punctuation": True,  # Auto-add punctuation
                "disfluencies": False,  # Remove "um", "uh" etc.
                "filter_profanity": False  # Keep all words for technical discussions
            }
            await self.websocket.send(json.dumps(config))
            logger.info("AssemblyAI session configured")
            
        except Exception as e:
            logger.error(f"Failed to connect to AssemblyAI: {type(e).__name__}: {str(e)}", exc_info=True)
            self.is_connected = False
            raise
    
    async def send_audio(self, audio_data: bytes):
        """
        Send audio data to Assembly AI for transcription
        
        Args:
            audio_data: PCM audio data (16-bit, 16kHz, mono)
        """
        if not self.is_connected or not self.websocket:
            logger.warning("AssemblyAI WebSocket not connected")
            return
        
        try:
            # Assembly AI expects base64-encoded audio
            import base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            message = json.dumps({"audio_data": audio_base64})
            await self.websocket.send(message)
        except Exception as e:
            logger.error(f"Error sending audio to AssemblyAI: {type(e).__name__}: {str(e)}", exc_info=True)
            raise
    
    async def receive_transcripts(self) -> AsyncGenerator[dict, None]:
        """
        Receive transcript messages from Assembly AI
        
        Yields:
            dict with keys: text, is_final, confidence, words, speaker
        """
        if not self.is_connected or not self.websocket:
            logger.warning("AssemblyAI WebSocket not connected")
            return
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("message_type")
                    
                    if message_type == "SessionBegins":
                        logger.info("AssemblyAI session began")
                        yield {"type": "session_begins", "data": data}
                    
                    elif message_type == "PartialTranscript":
                        text = data.get("text", "")
                        confidence = data.get("confidence", 0.0)
                        yield {
                            "type": "partial",
                            "text": text,
                            "is_final": False,
                            "confidence": confidence
                        }
                        if self.transcript_callback:
                            self.transcript_callback(text, is_final=False)
                    
                    elif message_type == "FinalTranscript":
                        text = data.get("text", "")
                        confidence = data.get("confidence", 0.0)
                        words = data.get("words", [])
                        speaker = data.get("speaker", None)
                        
                        yield {
                            "type": "final",
                            "text": text,
                            "is_final": True,
                            "confidence": confidence,
                            "words": words,
                            "speaker": speaker
                        }
                        if self.transcript_callback:
                            self.transcript_callback(text, is_final=True, speaker=speaker)
                    
                    elif message_type == "SessionTerminated":
                        logger.info("AssemblyAI session terminated")
                        yield {"type": "session_terminated", "data": data}
                        break
                    
                    elif message_type == "Error":
                        error = data.get("error", "Unknown error")
                        logger.error(f"AssemblyAI error: {error}")
                        yield {"type": "error", "error": error}
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse AssemblyAI message: {e}")
                except Exception as e:
                    logger.error(f"Error processing AssemblyAI message: {type(e).__name__}: {str(e)}", exc_info=True)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("AssemblyAI WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error receiving from AssemblyAI: {type(e).__name__}: {str(e)}", exc_info=True)
            self.is_connected = False
            raise
    
    async def terminate_session(self):
        """Terminate the Assembly AI session"""
        if self.websocket and self.is_connected:
            try:
                await self.websocket.send(json.dumps({"terminate_session": True}))
                logger.info("Sent terminate signal to AssemblyAI")
            except Exception as e:
                logger.warning(f"Error terminating AssemblyAI session: {e}")
    
    async def close(self):
        """Close the WebSocket connection"""
        if self.websocket:
            try:
                await self.terminate_session()
                await self.websocket.close()
                logger.info("AssemblyAI WebSocket closed")
            except Exception as e:
                logger.warning(f"Error closing AssemblyAI WebSocket: {e}")
            finally:
                self.websocket = None
                self.is_connected = False
    
    def is_available(self) -> bool:
        """Check if Assembly AI is configured and available"""
        return bool(self.api_key and self.api_key.strip())


# Global instance
assemblyai_service = AssemblyAIService()


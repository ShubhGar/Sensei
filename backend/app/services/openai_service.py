"""
OpenAI service for AI-powered processing
"""
import os
from typing import Optional, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from app.utils.logger import get_logger

# Try to import OpenAI exceptions (may vary by SDK version)
try:
    from openai import APIError, RateLimitError
except ImportError:
    try:
        from openai.error import APIError, RateLimitError
    except ImportError:
        # Fallback: define placeholder classes if not available
        class APIError(Exception):
            pass
        class RateLimitError(APIError):
            pass

load_dotenv()
logger = get_logger(__name__)


class OpenAIService:
    """Service for OpenAI AI processing"""
    
    def __init__(self, enabled: bool = True):
        """
        Initialize OpenAI service
        
        Args:
            enabled: Whether OpenAI service is enabled (can be disabled via flag)
        """
        self.enabled = enabled
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.fallback_model = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-3.5-turbo")
        
        if not self.enabled:
            self.client = None
            logger.info("OpenAI service disabled via flag")
            return
        
        # Initialize client if API key is available
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                # Warn if using deprecated model
                if "turbo-preview" in self.model.lower():
                    logger.warning(
                        f"Deprecated model detected | Model: {self.model} | "
                        f"Action: Update OPENAI_MODEL to 'gpt-4o' or 'gpt-4-turbo' in .env file"
                    )
                logger.info(
                    f"OpenAI service initialized | Model: {self.model} | "
                    f"Fallback model: {self.fallback_model}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to initialize OpenAI client | Error: {type(e).__name__}: {str(e)}",
                    exc_info=True
                )
                self.client = None
        else:
            self.client = None
            logger.warning("OpenAI API key not found | OpenAI service unavailable")
    
    def is_available(self) -> bool:
        """Check if OpenAI service is available and enabled"""
        return self.enabled and self.client is not None
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Generate text using OpenAI model
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            response_format: Response format (e.g., {"type": "json_object"})
            
        Returns:
            Generated text
            
        Raises:
            Exception: If service is not available or generation fails
        """
        if not self.is_available():
            raise Exception("OpenAI service is not available or disabled")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
        if response_format:
            params["response_format"] = response_format
        
        try:
            response = self.client.chat.completions.create(**params)
            return response.choices[0].message.content
        except (RateLimitError, APIError) as e:
            error_msg = str(e)
            error_code = getattr(e, 'status_code', None) or getattr(e, 'code', None)
            
            # Check if it's a quota/billing error
            if "insufficient_quota" in error_msg.lower() or "quota" in error_msg.lower() or "billing" in error_msg.lower():
                raise Exception(f"OpenAI quota exceeded. Please check your OpenAI billing and plan details. Error: {error_msg}")
            
            # Check if it's a rate limit error
            if isinstance(e, RateLimitError) or (error_code == 429) or "429" in error_msg or "rate limit" in error_msg.lower():
                raise Exception(f"OpenAI rate limit exceeded. Please wait a moment and try again. Error: {error_msg}")
            
            # Check if it's a model not found error - try fallback
            if (error_code == 404) or "404" in error_msg or "model_not_found" in error_msg.lower() or "does not exist" in error_msg.lower():
                logger.warning(
                    f"OpenAI model not found | Primary model: {self.model} | "
                    f"Trying fallback: {self.fallback_model} | Error: {error_msg}"
                )
                if self.model != self.fallback_model:
                    params["model"] = self.fallback_model
                    try:
                        response = self.client.chat.completions.create(**params)
                        return response.choices[0].message.content
                    except Exception as fallback_error:
                        fallback_msg = str(fallback_error)
                        if "insufficient_quota" in fallback_msg.lower() or "quota" in fallback_msg.lower():
                            raise Exception(f"OpenAI quota exceeded on fallback model. Please check your OpenAI billing.")
                        if isinstance(fallback_error, RateLimitError) or "429" in fallback_msg:
                            raise Exception(f"OpenAI rate limit exceeded on fallback model. Please wait and try again.")
                        raise Exception(f"OpenAI primary and fallback models failed: {fallback_msg}")
                else:
                    raise Exception(f"OpenAI model not found: {error_msg}")
            else:
                raise Exception(f"OpenAI API error: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            # Check for quota/billing errors in generic exceptions
            if "insufficient_quota" in error_msg.lower() or ("quota" in error_msg.lower() and "429" in error_msg) or "billing" in error_msg.lower():
                raise Exception(f"OpenAI quota exceeded. Please check your OpenAI billing. Error: {error_msg}")
            # Check for rate limit in generic exception
            if "429" in error_msg or "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower():
                raise Exception(f"OpenAI rate limit exceeded. Please wait and try again. Error: {error_msg}")
            # Check for model not found
            if "404" in error_msg or "model_not_found" in error_msg.lower() or "does not exist" in error_msg.lower():
                logger.warning(
                    f"OpenAI model not found | Primary model: {self.model} | "
                    f"Trying fallback: {self.fallback_model} | Error: {error_msg}"
                )
                if self.model != self.fallback_model:
                    params["model"] = self.fallback_model
                    try:
                        response = self.client.chat.completions.create(**params)
                        return response.choices[0].message.content
                    except Exception as fallback_error:
                        fallback_msg = str(fallback_error)
                        if "insufficient_quota" in fallback_msg.lower() or ("quota" in fallback_msg.lower() and "429" in fallback_msg):
                            raise Exception(f"OpenAI quota exceeded on fallback model. Please check your OpenAI billing.")
                        if "429" in fallback_msg or "rate limit" in fallback_msg.lower():
                            raise Exception(f"OpenAI rate limit exceeded on fallback model. Please wait and try again.")
                        raise Exception(f"OpenAI primary and fallback models failed: {fallback_msg}")
                else:
                    raise Exception(f"OpenAI model not found: {error_msg}")
            raise Exception(f"OpenAI error: {error_msg}")


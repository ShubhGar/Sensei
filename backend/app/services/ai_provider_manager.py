"""
AI Provider Manager - Manages switching between OpenAI and Bedrock providers
"""
import os
from typing import Optional
from dotenv import load_dotenv
from app.utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

# Import services conditionally
try:
    from app.services.openai_service import OpenAIService
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAIService = None

try:
    from app.services.bedrock_service import BedrockService
    BEDROCK_AVAILABLE = True
except ImportError:
    BEDROCK_AVAILABLE = False
    BedrockService = None


class AIProviderManager:
    """Manages AI providers (OpenAI and Bedrock) with configurable switching"""
    
    def __init__(
        self,
        use_bedrock: Optional[bool] = None,
        enable_openai: Optional[bool] = None,
        enable_bedrock: Optional[bool] = None
    ):
        """
        Initialize AI Provider Manager
        
        Args:
            use_bedrock: Primary provider preference (True=Bedrock, False=OpenAI, None=auto from env)
            enable_openai: Enable/disable OpenAI service (None=auto from env)
            enable_bedrock: Enable/disable Bedrock service (None=auto from env)
        """
        # Determine provider preference
        if use_bedrock is None:
            self.use_bedrock = os.getenv("USE_BEDROCK", "false").lower() == "true"
        else:
            self.use_bedrock = use_bedrock
        
        # Determine service enablement flags
        if enable_openai is None:
            self.enable_openai = os.getenv("ENABLE_OPENAI", "true").lower() == "true"
        else:
            self.enable_openai = enable_openai
            
        if enable_bedrock is None:
            self.enable_bedrock = os.getenv("ENABLE_BEDROCK", "true").lower() == "true"
        else:
            self.enable_bedrock = enable_bedrock
        
        # Initialize services
        self.openai_service = None
        self.bedrock_service = None
        
        # Initialize OpenAI service
        if self.enable_openai and OPENAI_AVAILABLE:
            try:
                self.openai_service = OpenAIService(enabled=True)
                if not self.openai_service.is_available():
                    logger.warning("OpenAI service initialized but not available (missing API key)")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI service: {e}", exc_info=True)
        elif self.enable_openai and not OPENAI_AVAILABLE:
            logger.warning("OpenAI requested but openai package not installed")
        elif not self.enable_openai:
            logger.info("OpenAI service disabled via flag")
        
        # Initialize Bedrock service
        if self.enable_bedrock and BEDROCK_AVAILABLE:
            try:
                self.bedrock_service = BedrockService()
                if not self.bedrock_service.client:
                    logger.warning("Bedrock service initialized but client not available (check credentials)")
            except Exception as e:
                logger.error(f"Failed to initialize Bedrock service: {e}", exc_info=True)
        elif self.enable_bedrock and not BEDROCK_AVAILABLE:
            logger.warning("Bedrock requested but boto3 not installed")
        elif not self.enable_bedrock:
            logger.info("Bedrock service disabled via flag")
        
        # Determine primary provider
        self.primary_provider = self._determine_primary_provider()
        
        # Log initialization
        self._log_initialization()
    
    def _determine_primary_provider(self) -> str:
        """Determine which provider to use as primary"""
        if self.use_bedrock and self.bedrock_service and self.bedrock_service.client:
            return "bedrock"
        elif self.openai_service and self.openai_service.is_available():
            return "openai"
        elif self.bedrock_service and self.bedrock_service.client:
            return "bedrock"
        else:
            return "none"
    
    def _log_initialization(self):
        """Log provider initialization status"""
        providers = []
        if self.openai_service and self.openai_service.is_available():
            providers.append(f"OpenAI ({self.openai_service.model})")
        if self.bedrock_service and self.bedrock_service.client:
            providers.append(f"Bedrock ({self.bedrock_service.model_id})")
        
        if not providers:
            logger.error("No AI providers available! Check configuration and credentials.")
            return
        
        primary_info = f"Primary: {self.primary_provider.upper()}"
        fallback_info = f"Fallback: {'enabled' if len(providers) > 1 else 'none'}"
        
        logger.info(
            f"AI Provider Manager initialized | {primary_info} | "
            f"Available: {', '.join(providers)} | {fallback_info}"
        )
    
    def get_primary_provider(self) -> str:
        """Get the name of the primary provider"""
        return self.primary_provider
    
    def is_openai_available(self) -> bool:
        """Check if OpenAI is available"""
        return self.openai_service is not None and self.openai_service.is_available()
    
    def is_bedrock_available(self) -> bool:
        """Check if Bedrock is available"""
        return self.bedrock_service is not None and self.bedrock_service.client is not None
    
    def has_any_provider(self) -> bool:
        """Check if any provider is available"""
        return self.is_openai_available() or self.is_bedrock_available()
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None
    ) -> str:
        """
        Generate text using the appropriate provider with fallback
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Temperature for generation
            max_tokens: Maximum tokens
            response_format: Response format
            
        Returns:
            Generated text
            
        Raises:
            Exception: If no providers are available or all fail
        """
        # Try primary provider first
        if self.primary_provider == "bedrock" and self.is_bedrock_available():
            try:
                return await self.bedrock_service.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format
                )
            except Exception as e:
                error_msg = str(e)
                # Check if it's an access/permission error
                if "AccessDeniedException" in error_msg or "not authorized" in error_msg.lower() or "Marketplace" in error_msg:
                    logger.warning(
                        f"Bedrock access denied, falling back to OpenAI | Error: {error_msg}"
                    )
                    if self.is_openai_available():
                        return await self.openai_service.generate_text(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            response_format=response_format
                        )
                    else:
                        raise Exception(f"Bedrock access denied and OpenAI not available: {error_msg}")
                else:
                    # Re-raise other errors
                    raise
        
        elif self.primary_provider == "openai" and self.is_openai_available():
            try:
                return await self.openai_service.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format
                )
            except Exception as e:
                error_msg = str(e)
                logger.warning(
                    f"OpenAI failed, falling back to Bedrock | Error: {error_msg}"
                )
                if self.is_bedrock_available():
                    return await self.bedrock_service.generate_text(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format=response_format
                    )
                else:
                    raise Exception(f"OpenAI failed and Bedrock not available: {error_msg}")
        
        else:
            raise Exception("No AI providers available. Check configuration and credentials.")


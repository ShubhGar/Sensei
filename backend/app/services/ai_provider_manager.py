"""
AI Provider Manager - Manages switching between OpenAI and Bedrock providers
Supports ensemble mode for improved accuracy by using both providers
"""
import os
import json
from typing import Optional, Tuple
import asyncio
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
        enable_bedrock: Optional[bool] = None,
        use_ensemble: Optional[bool] = None
    ):
        """
        Initialize AI Provider Manager
        
        Args:
            use_bedrock: Primary provider preference (True=Bedrock, False=OpenAI, None=auto from env)
            enable_openai: Enable/disable OpenAI service (None=auto from env)
            enable_bedrock: Enable/disable Bedrock service (None=auto from env)
            use_ensemble: Use ensemble mode (both providers in parallel) for improved accuracy (None=auto from env)
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
        
        # Determine ensemble mode
        if use_ensemble is None:
            self.use_ensemble = os.getenv("USE_ENSEMBLE_MODE", "false").lower() == "true"
        else:
            self.use_ensemble = use_ensemble
        
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
        
        # Validate ensemble mode requirements
        if self.use_ensemble:
            if not (self.is_openai_available() and self.is_bedrock_available()):
                logger.warning(
                    "Ensemble mode requested but both providers not available. "
                    "Falling back to single provider mode."
                )
                self.use_ensemble = False
        
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
        mode_info = "Ensemble Mode: ENABLED" if self.use_ensemble else f"Fallback: {'enabled' if len(providers) > 1 else 'none'}"
        
        logger.info(
            f"AI Provider Manager initialized | {primary_info} | "
            f"Available: {', '.join(providers)} | {mode_info}"
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
    
    def _merge_ensemble_responses(
        self,
        openai_response: str,
        bedrock_response: str
    ) -> str:
        """
        Intelligently merge responses from both providers for better accuracy
        
        Strategy:
        1. If responses are very similar, use the longer/more detailed one
        2. If responses differ significantly, combine key points from both
        3. Prefer more structured/complete responses
        
        Args:
            openai_response: Response from OpenAI
            bedrock_response: Response from Bedrock
            
        Returns:
            Merged response
        """
        # If responses are very similar (high overlap), use the longer one
        openai_lower = openai_response.lower().strip()
        bedrock_lower = bedrock_response.lower().strip()
        
        # Calculate similarity (simple word overlap)
        openai_words = set(openai_lower.split())
        bedrock_words = set(bedrock_lower.split())
        
        if len(openai_words) > 0 and len(bedrock_words) > 0:
            overlap = len(openai_words & bedrock_words)
            total_unique = len(openai_words | bedrock_words)
            similarity = overlap / total_unique if total_unique > 0 else 0
            
            # If very similar (>80% overlap), use the longer/more detailed response
            if similarity > 0.8:
                if len(openai_response) > len(bedrock_response):
                    logger.debug("Ensemble: Responses very similar, using OpenAI (longer)")
                    return openai_response
                else:
                    logger.debug("Ensemble: Responses very similar, using Bedrock (longer)")
                    return bedrock_response
        
        # If responses differ, combine them intelligently
        # For structured content (JSON, lists), try to merge
        if openai_response.strip().startswith('{') and bedrock_response.strip().startswith('{'):
            # Both are JSON - prefer the more complete one
            try:
                openai_json = json.loads(openai_response)
                bedrock_json = json.loads(bedrock_response)
                
                # Merge JSON objects, preferring non-empty values
                merged = {}
                all_keys = set(openai_json.keys()) | set(bedrock_json.keys())
                for key in all_keys:
                    openai_val = openai_json.get(key)
                    bedrock_val = bedrock_json.get(key)
                    
                    # Prefer non-empty, more detailed values
                    if openai_val and bedrock_val:
                        # If both exist, prefer the longer/more detailed one
                        if isinstance(openai_val, str) and isinstance(bedrock_val, str):
                            merged[key] = openai_val if len(openai_val) > len(bedrock_val) else bedrock_val
                        elif isinstance(openai_val, list) and isinstance(bedrock_val, list):
                            # Merge lists, removing duplicates
                            combined = openai_val + bedrock_val
                            # Simple deduplication for list of strings
                            if all(isinstance(x, str) for x in combined):
                                merged[key] = list(dict.fromkeys(combined))  # Preserves order
                            else:
                                merged[key] = openai_val if len(openai_val) > len(bedrock_val) else bedrock_val
                        else:
                            merged[key] = openai_val if openai_val else bedrock_val
                    else:
                        merged[key] = openai_val or bedrock_val
                
                logger.debug("Ensemble: Merged JSON responses from both providers")
                return json.dumps(merged, indent=2)
            except:
                # If JSON parsing fails, fall through to text merging
                pass
        
        # For text responses, combine key points
        # Use OpenAI as base (typically more structured) and add unique points from Bedrock
        logger.debug("Ensemble: Combining text responses from both providers")
        
        # Simple strategy: Use OpenAI response, append unique insights from Bedrock
        bedrock_unique = []
        bedrock_sentences = bedrock_response.split('.')
        openai_lower_words = set(openai_lower.split())
        
        for sentence in bedrock_sentences:
            sentence_words = set(sentence.lower().split())
            # If sentence has significant new content (>30% new words), include it
            if len(sentence_words) > 0:
                new_words = sentence_words - openai_lower_words
                if len(new_words) / len(sentence_words) > 0.3:
                    bedrock_unique.append(sentence.strip())
        
        if bedrock_unique:
            combined = f"{openai_response}\n\nAdditional insights:\n" + ". ".join(bedrock_unique[:3])  # Limit to top 3 unique points
            return combined
        
        # If no significant differences, use OpenAI (typically more consistent)
        return openai_response
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None
    ) -> str:
        """
        Generate text using the appropriate provider with fallback or ensemble mode
        
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
        # Ensemble mode: Use both providers in parallel and merge results
        if self.use_ensemble and self.is_openai_available() and self.is_bedrock_available():
            logger.info("Ensemble mode: Running both OpenAI and Bedrock in parallel")
            
            async def get_openai_response():
                try:
                    return await self.openai_service.generate_text(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format=response_format
                    )
                except Exception as e:
                    logger.warning(f"Ensemble: OpenAI failed: {e}")
                    return None
            
            async def get_bedrock_response():
                try:
                    return await self.bedrock_service.generate_text(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format=response_format
                    )
                except Exception as e:
                    logger.warning(f"Ensemble: Bedrock failed: {e}")
                    return None
            
            # Run both in parallel
            openai_result, bedrock_result = await asyncio.gather(
                get_openai_response(),
                get_bedrock_response(),
                return_exceptions=False
            )
            
            # If both succeeded, merge them
            if openai_result and bedrock_result:
                logger.info("Ensemble: Both providers succeeded, merging responses")
                return self._merge_ensemble_responses(openai_result, bedrock_result)
            
            # If only one succeeded, use it
            if openai_result:
                logger.info("Ensemble: Only OpenAI succeeded, using OpenAI response")
                return openai_result
            
            if bedrock_result:
                logger.info("Ensemble: Only Bedrock succeeded, using Bedrock response")
                return bedrock_result
            
            # Both failed
            raise Exception("Ensemble mode: Both OpenAI and Bedrock failed")
        
        # Single provider mode (existing fallback logic)
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



"""
AI service for summarization, MOM generation, and insights
"""
import os
from typing import List, Optional, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
import json
import asyncio
import re
from app.utils.logger import get_logger

logger = get_logger(__name__)

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

# Import BedrockService conditionally to avoid errors if boto3 is not installed
try:
    from app.services.bedrock_service import BedrockService
    BEDROCK_AVAILABLE = True
except ImportError:
    BEDROCK_AVAILABLE = False
    BedrockService = None


class AIService:
    """Service for AI-powered processing"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.fallback_model = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-3.5-turbo")
        self.use_bedrock = os.getenv("USE_BEDROCK", "false").lower() == "true"
        
        # Warn if using deprecated model
        if "turbo-preview" in self.model.lower():
            logger.warning(
                f"Deprecated model detected | Model: {self.model} | "
                f"Action: Update OPENAI_MODEL to 'gpt-4o' or 'gpt-4-turbo' in .env file"
            )
        
        # Initialize clients
        # Always initialize OpenAI client if API key is available (for fallback)
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        
        if self.use_bedrock and BEDROCK_AVAILABLE:
            self.bedrock_service = BedrockService()
            bedrock_model = getattr(self.bedrock_service, 'model_id', 'unknown')
            logger.info(
                f"AI service initialized | Provider: AWS Bedrock | Model: {bedrock_model} | "
                f"Fallback: OpenAI enabled"
            )
        else:
            self.bedrock_service = None
            if self.use_bedrock and not BEDROCK_AVAILABLE:
                logger.warning(
                    "Bedrock requested but unavailable | USE_BEDROCK=true but boto3 not installed | "
                    "Falling back to OpenAI"
                )
            else:
                logger.info(
                    f"AI service initialized | Provider: OpenAI | Model: {self.model} | "
                    f"Fallback model: {self.fallback_model}"
                )
    
    async def _call_ai(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """Unified async method to call either OpenAI or Bedrock"""
        if self.use_bedrock and self.bedrock_service:
            # Use Bedrock with fallback to OpenAI on permission errors
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
                        f"Bedrock access denied, falling back to OpenAI | Error: {error_msg} | "
                        f"Error type: {type(e).__name__}"
                    )
                    if self.client:
                        # Fall back to OpenAI
                        messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ]
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
                        except (RateLimitError, APIError) as openai_error:
                            error_msg_openai = str(openai_error)
                            error_code = getattr(openai_error, 'status_code', None) or getattr(openai_error, 'code', None)
                            
                            # Check if it's a quota/billing error (429 with insufficient_quota)
                            if "insufficient_quota" in error_msg_openai.lower() or "quota" in error_msg_openai.lower() or "billing" in error_msg_openai.lower():
                                raise Exception(f"OpenAI quota exceeded. Please check your OpenAI billing and plan details. You may need to add credits or upgrade your plan. Error: {error_msg_openai}")
                            
                            # Check if it's a rate limit error (429)
                            if isinstance(openai_error, RateLimitError) or (error_code == 429) or "429" in error_msg_openai or "rate limit" in error_msg_openai.lower():
                                raise Exception(f"OpenAI rate limit exceeded. Please wait a moment and try again. Error: {error_msg_openai}")
                            
                            # Check if it's a model not found error (404)
                            if (error_code == 404) or "404" in error_msg_openai or "model_not_found" in error_msg_openai.lower() or "does not exist" in error_msg_openai.lower():
                                logger.warning(
                                    f"OpenAI model not found | Primary model: {self.model} | "
                                    f"Trying fallback: {self.fallback_model} | Error: {error_msg_openai}"
                                )
                                # Try with fallback model
                                if self.model != self.fallback_model:
                                    params["model"] = self.fallback_model
                                    try:
                                        response = self.client.chat.completions.create(**params)
                                        return response.choices[0].message.content
                                    except (RateLimitError, APIError) as fallback_error:
                                        fallback_code = getattr(fallback_error, 'status_code', None) or getattr(fallback_error, 'code', None)
                                        fallback_msg = str(fallback_error)
                                        if "insufficient_quota" in fallback_msg.lower() or "quota" in fallback_msg.lower() or "billing" in fallback_msg.lower():
                                            raise Exception(f"OpenAI quota exceeded on fallback model. Please check your OpenAI billing and plan details.")
                                        if isinstance(fallback_error, RateLimitError) or (fallback_code == 429):
                                            raise Exception(f"OpenAI rate limit exceeded on fallback model. Please wait and try again.")
                                        raise Exception(f"Bedrock access denied and both OpenAI models failed: {fallback_msg}")
                                    except Exception as fallback_error:
                                        raise Exception(f"Bedrock access denied and both OpenAI models failed: {str(fallback_error)}")
                                else:
                                    raise Exception(f"Bedrock access denied and OpenAI model not found: {error_msg}")
                            else:
                                raise Exception(f"Bedrock access denied and OpenAI error: {openai_error}")
                        except Exception as openai_error:
                            error_msg_openai = str(openai_error)
                            # Check if it's a quota/billing error first
                            if "insufficient_quota" in error_msg_openai.lower() or ("quota" in error_msg_openai.lower() and "429" in error_msg_openai) or "billing" in error_msg_openai.lower():
                                raise Exception(f"OpenAI quota exceeded. Please check your OpenAI billing and plan details. You may need to add credits or upgrade your plan. Error: {error_msg_openai}")
                            # Check for rate limit in generic exception
                            if "429" in error_msg_openai or "rate limit" in error_msg_openai.lower() or "too many requests" in error_msg_openai.lower():
                                raise Exception(f"OpenAI rate limit exceeded. Please wait a moment and try again. Error: {error_msg_openai}")
                            # Check if it's a model not found error (404)
                            if "404" in error_msg_openai or "model_not_found" in error_msg_openai.lower() or "does not exist" in error_msg_openai.lower():
                                logger.warning(
                                    f"OpenAI model not found | Primary model: {self.model} | "
                                    f"Trying fallback: {self.fallback_model} | Error: {error_msg_openai}"
                                )
                                # Try with fallback model
                                if self.model != self.fallback_model:
                                    params["model"] = self.fallback_model
                                    try:
                                        response = self.client.chat.completions.create(**params)
                                        return response.choices[0].message.content
                                    except Exception as fallback_error:
                                        fallback_msg = str(fallback_error)
                                        if "insufficient_quota" in fallback_msg.lower() or ("quota" in fallback_msg.lower() and "429" in fallback_msg) or "billing" in fallback_msg.lower():
                                            raise Exception(f"OpenAI quota exceeded on fallback model. Please check your OpenAI billing and plan details.")
                                        if "429" in fallback_msg or "rate limit" in fallback_msg.lower():
                                            raise Exception(f"OpenAI rate limit exceeded on fallback model. Please wait and try again.")
                                        raise Exception(f"Bedrock access denied and both OpenAI models failed: {fallback_msg}")
                                else:
                                    raise Exception(f"Bedrock access denied and OpenAI model not found: {error_msg}")
                            else:
                                raise Exception(f"Bedrock access denied and OpenAI error: {openai_error}")
                    else:
                        raise Exception(f"Bedrock access denied and OpenAI not available: {error_msg}")
                else:
                    # Re-raise other errors
                    raise
        
        elif self.client:
            # Use OpenAI (synchronous call, but we're in async context)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
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
                
                # Check if it's a quota/billing error (429 with insufficient_quota)
                if "insufficient_quota" in error_msg.lower() or "quota" in error_msg.lower() or "billing" in error_msg.lower():
                    raise Exception(f"OpenAI quota exceeded. Please check your OpenAI billing and plan details. You may need to add credits or upgrade your plan. Error: {error_msg}")
                
                # Check if it's a rate limit error (429)
                if isinstance(e, RateLimitError) or (error_code == 429) or "429" in error_msg or "rate limit" in error_msg.lower():
                    raise Exception(f"OpenAI rate limit exceeded. Please wait a moment and try again. Error: {error_msg}")
                
                # Check if it's a model not found error (404)
                if (error_code == 404) or "404" in error_msg or "model_not_found" in error_msg.lower() or "does not exist" in error_msg.lower():
                    logger.warning(
                        f"OpenAI model not found | Primary model: {self.model} | "
                        f"Trying fallback: {self.fallback_model} | Error: {error_msg}"
                    )
                    # Try with fallback model
                    if self.model != self.fallback_model:
                        params["model"] = self.fallback_model
                        try:
                            response = self.client.chat.completions.create(**params)
                            return response.choices[0].message.content
                        except (RateLimitError, APIError) as fallback_error:
                            fallback_code = getattr(fallback_error, 'status_code', None) or getattr(fallback_error, 'code', None)
                            fallback_msg = str(fallback_error)
                            if "insufficient_quota" in fallback_msg.lower() or "quota" in fallback_msg.lower() or "billing" in fallback_msg.lower():
                                raise Exception(f"OpenAI quota exceeded on fallback model. Please check your OpenAI billing and plan details.")
                            if isinstance(fallback_error, RateLimitError) or (fallback_code == 429):
                                raise Exception(f"OpenAI rate limit exceeded on fallback model. Please wait and try again.")
                            raise Exception(f"Both primary model '{self.model}' and fallback model '{self.fallback_model}' failed: {fallback_error}")
                        except Exception as fallback_error:
                            fallback_msg = str(fallback_error)
                            if "insufficient_quota" in fallback_msg.lower() or ("quota" in fallback_msg.lower() and "429" in fallback_msg) or "billing" in fallback_msg.lower():
                                raise Exception(f"OpenAI quota exceeded on fallback model. Please check your OpenAI billing and plan details.")
                            if "429" in fallback_msg or "rate limit" in fallback_msg.lower():
                                raise Exception(f"OpenAI rate limit exceeded on fallback model. Please wait and try again.")
                            raise Exception(f"Both primary model '{self.model}' and fallback model '{self.fallback_model}' failed: {fallback_error}")
                    else:
                        raise Exception(f"Model '{self.model}' not found and no fallback available: {error_msg}")
                else:
                    # Re-raise other errors
                    raise
            except Exception as e:
                error_msg = str(e)
                # Check if it's a quota/billing error first
                if "insufficient_quota" in error_msg.lower() or ("quota" in error_msg.lower() and "429" in error_msg) or "billing" in error_msg.lower():
                    raise Exception(f"OpenAI quota exceeded. Please check your OpenAI billing and plan details. You may need to add credits or upgrade your plan. Error: {error_msg}")
                # Check for rate limit in generic exception
                if "429" in error_msg or "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower():
                    raise Exception(f"OpenAI rate limit exceeded. Please wait a moment and try again. Error: {error_msg}")
                # Check if it's a model not found error (404)
                if "404" in error_msg or "model_not_found" in error_msg.lower() or "does not exist" in error_msg.lower():
                    logger.warning(
                        f"OpenAI model not found | Primary model: {self.model} | "
                        f"Trying fallback: {self.fallback_model} | Error: {error_msg}"
                    )
                    # Try with fallback model
                    if self.model != self.fallback_model:
                        params["model"] = self.fallback_model
                        try:
                            response = self.client.chat.completions.create(**params)
                            return response.choices[0].message.content
                        except Exception as fallback_error:
                            fallback_msg = str(fallback_error)
                            if "insufficient_quota" in fallback_msg.lower() or ("quota" in fallback_msg.lower() and "429" in fallback_msg) or "billing" in fallback_msg.lower():
                                raise Exception(f"OpenAI quota exceeded on fallback model. Please check your OpenAI billing and plan details.")
                            if "429" in fallback_msg or "rate limit" in fallback_msg.lower():
                                raise Exception(f"OpenAI rate limit exceeded on fallback model. Please wait and try again.")
                            raise Exception(f"Both primary model '{self.model}' and fallback model '{self.fallback_model}' failed: {fallback_error}")
                    else:
                        raise Exception(f"Model '{self.model}' not found and no fallback available: {error_msg}")
                else:
                    # Re-raise other errors
                    raise
        else:
            raise Exception("No AI service available")
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Safely parse JSON from AI response, handling markdown code blocks and control characters"""
        if not content or not content.strip():
            raise ValueError("Empty response from AI")
        
        # Remove markdown code blocks if present
        content = content.strip()
        if content.startswith("```"):
            # Remove opening ```json or ```
            content = re.sub(r'^```(?:json)?\s*\n', '', content)
            # Remove closing ```
            content = re.sub(r'\n```\s*$', '', content)
        
        # Remove control characters (except newlines and tabs)
        # But we'll handle newlines in string values separately
        content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', content)
        
        # Try to find JSON object in the content
        # Look for first { and last }
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content = content[start_idx:end_idx + 1]
        elif start_idx != -1:
            # If we found start but not end, try to find a reasonable end point
            # This handles truncated responses
            # Look for the last complete structure
            brace_count = 0
            last_valid_end = -1
            for i in range(start_idx, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        last_valid_end = i
                    elif brace_count < 0:
                        break
            
            if last_valid_end > start_idx:
                content = content[start_idx:last_valid_end + 1]
            else:
                # If we can't find a complete structure, try to close it
                # Count unclosed braces and add closing braces
                open_braces = content.count('{') - content.count('}')
                if open_braces > 0:
                    content = content + '}' * open_braces
        
        # Fix newlines in JSON string values - they need to be escaped
        # This is a more sophisticated approach: we'll try to escape newlines within string values
        # We'll use a regex to find string values and escape newlines within them
        def escape_newlines_in_strings(match):
            """Escape newlines, quotes, and backslashes in JSON string values"""
            string_content = match.group(1)
            # Escape backslashes first, then quotes, then newlines
            string_content = string_content.replace('\\', '\\\\')
            string_content = string_content.replace('"', '\\"')
            string_content = string_content.replace('\n', '\\n')
            string_content = string_content.replace('\r', '\\r')
            string_content = string_content.replace('\t', '\\t')
            return f'"{string_content}"'
        
        # Pattern to match JSON string values (content between quotes)
        # This is a simplified approach - we'll try to fix common cases
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Try to fix common issues
            # First, try to escape newlines in string values more carefully
            # We'll use a state machine approach to properly escape strings
            fixed_content = self._fix_json_strings(content)
            
            # Remove trailing commas before closing braces/brackets
            fixed_content = re.sub(r',\s*}', '}', fixed_content)
            fixed_content = re.sub(r',\s*]', ']', fixed_content)
            
            try:
                return json.loads(fixed_content)
            except json.JSONDecodeError as e2:
                # Log more context for debugging
                error_pos = getattr(e2, 'pos', None)
                if error_pos:
                    start_debug = max(0, error_pos - 100)
                    end_debug = min(len(fixed_content), error_pos + 100)
                    context = fixed_content[start_debug:end_debug]
                    raise ValueError(f"Invalid JSON response: {str(e2)}. Position: {error_pos}. Context: ...{context}...")
                else:
                    raise ValueError(f"Invalid JSON response: {str(e2)}. Content preview: {fixed_content[:500]}")
    
    def _fix_json_strings(self, content: str) -> str:
        """Fix JSON string values by properly escaping newlines and other special characters"""
        result = []
        i = 0
        in_string = False
        escape_next = False
        
        while i < len(content):
            char = content[i]
            
            if escape_next:
                # We're escaping the next character
                result.append(char)
                escape_next = False
                i += 1
                continue
            
            if char == '\\':
                # Escape character - next char is escaped
                result.append(char)
                escape_next = True
                i += 1
                continue
            
            if char == '"' and not escape_next:
                # Toggle string state
                in_string = not in_string
                result.append(char)
                i += 1
                continue
            
            if in_string:
                # We're inside a string - escape special characters
                if char == '\n':
                    result.append('\\n')
                elif char == '\r':
                    result.append('\\r')
                elif char == '\t':
                    result.append('\\t')
                elif char == '\b':
                    result.append('\\b')
                elif char == '\f':
                    result.append('\\f')
                elif ord(char) < 32:  # Other control characters
                    result.append(f'\\u{ord(char):04x}')
                else:
                    result.append(char)
            else:
                # Outside string - keep as is
                result.append(char)
            
            i += 1
        
        return ''.join(result)
    
    async def generate_mom(
        self,
        transcript: str,
        session_id: str,
        duration: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate Minutes of Meeting from transcript"""
        if not self.client and not self.bedrock_service:
            mom_data = self._generate_mom_fallback(transcript)
            mom_data["session_id"] = session_id
            mom_data["duration"] = duration
            return mom_data
        
        prompt = f"""Analyze the following meeting transcript and generate structured Minutes of Meeting (MOM).

Transcript:
{transcript}

Please provide:
1. A concise summary (2-3 paragraphs)
2. Key decisions made (list format)
3. Action items with owners and deadlines (if mentioned)
4. Key discussion points (bullet points)
5. List of attendees (if identifiable)

Format the response as JSON with the following structure:
{{
    "summary": "...",
    "decisions": [{{"decision": "...", "context": "..."}}],
    "action_items": [{{"task": "...", "owner": "...", "deadline": "...", "priority": "..."}}],
    "key_points": ["...", "..."],
    "attendees": ["...", "..."]
}}"""

        system_prompt = "You are an expert at analyzing meetings and generating structured minutes."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            mom_data = self._parse_json_response(content)
            mom_data["session_id"] = session_id
            mom_data["duration"] = duration
            return mom_data
        except Exception as e:
            logger.error(
                f"Error generating MOM | Session: {session_id} | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            mom_data = self._generate_mom_fallback(transcript)
            mom_data["session_id"] = session_id
            mom_data["duration"] = duration
            return mom_data
    
    def _generate_mom_fallback(self, transcript: str) -> Dict[str, Any]:
        """Fallback MOM generation (simple extraction)"""
        lines = transcript.split("\n")
        return {
            "summary": transcript[:500] + "..." if len(transcript) > 500 else transcript,
            "decisions": [],
            "action_items": [],
            "key_points": lines[:5],
            "attendees": [],
            "duration": None
        }
    
    async def generate_meeting_title(self, transcript: str) -> str:
        """Generate a concise, descriptive meeting title from transcript context"""
        if not transcript or not transcript.strip():
            return "Untitled Meeting"
        
        # If transcript is very short, use a simple fallback
        if len(transcript.strip()) < 50:
            return "Untitled Meeting"
        
        if not self.client and not self.bedrock_service:
            # Fallback: extract first meaningful sentence or phrase
            sentences = transcript.split('.')
            if sentences:
                first_sentence = sentences[0].strip()
                # Limit to 60 characters for title
                if len(first_sentence) > 60:
                    return first_sentence[:57] + "..."
                return first_sentence if first_sentence else "Untitled Meeting"
            return "Untitled Meeting"
        
        # Use a portion of the transcript for title generation (first 2000 chars should be enough)
        transcript_excerpt = transcript[:2000] if len(transcript) > 2000 else transcript
        
        prompt = f"""Based on the following meeting transcript, generate a concise and descriptive meeting title (maximum 80 characters).

The title should:
- Capture the main topic or purpose of the meeting
- Be professional and clear
- Not include dates, times, or generic words like "Meeting" unless necessary
- Focus on the key subject matter discussed

Transcript:
{transcript_excerpt}

Generate only the title, nothing else. Do not include quotes, prefixes, or explanations."""

        system_prompt = "You are an expert at analyzing meeting content and creating concise, descriptive titles."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=100
            )
            
            # Clean up the response - remove quotes, extra whitespace, etc.
            title = content.strip()
            # Remove surrounding quotes if present
            if title.startswith('"') and title.endswith('"'):
                title = title[1:-1]
            elif title.startswith("'") and title.endswith("'"):
                title = title[1:-1]
            
            # Limit to 80 characters
            if len(title) > 80:
                title = title[:77] + "..."
            
            # Ensure we have a valid title
            if not title or len(title.strip()) < 3:
                return "Untitled Meeting"
            
            return title.strip()
        except Exception as e:
            logger.warning(
                f"Error generating meeting title | Error: {type(e).__name__}: {str(e)} | "
                f"Using fallback",
                exc_info=True
            )
            # Fallback: extract first meaningful sentence or phrase
            sentences = transcript.split('.')
            if sentences:
                first_sentence = sentences[0].strip()
                if len(first_sentence) > 60:
                    return first_sentence[:57] + "..."
                return first_sentence if first_sentence else "Untitled Meeting"
            return "Untitled Meeting"
    
    async def generate_faqs(self, transcript: str, mom: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate FAQs from transcript and MOM"""
        if not self.client and not self.bedrock_service:
            return []
        
        prompt = f"""Based on the following meeting transcript and MOM, generate 3-5 frequently asked questions (FAQs) that might arise.

Transcript excerpt:
{transcript[:2000]}

MOM Summary:
{mom.get('summary', '')}

Generate FAQs in JSON format:
{{
    "faqs": [
        {{"question": "...", "answer": "...", "context": "..."}},
        ...
    ]
}}"""

        system_prompt = "You are an expert at generating relevant FAQs from meeting content."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=3072,  # Increased to reduce truncation
                response_format={"type": "json_object"}
            )
            
            faq_data = self._parse_json_response(content)
            return faq_data.get("faqs", [])
        except Exception as e:
            logger.error(
                f"Error generating FAQs | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return []
    
    async def generate_email_draft(
        self,
        mom: Dict[str, Any],
        recipients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate follow-up email draft from MOM"""
        if not self.client and not self.bedrock_service:
            return self._generate_email_draft_fallback(mom)
        
        prompt = f"""Generate a professional follow-up email based on the following meeting minutes.

MOM:
{json.dumps(mom, indent=2)}

Create an email that:
1. Summarizes key decisions
2. Lists action items with owners
3. Includes next steps
4. Is professional and concise

Format as JSON:
{{
    "to": ["..."],
    "subject": "...",
    "body": "...",
    "cc": [],
    "bcc": []
}}"""

        system_prompt = "You are an expert at writing professional meeting follow-up emails."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=3072,  # Increased to reduce truncation, especially for email body
                response_format={"type": "json_object"}
            )
            
            email_data = self._parse_json_response(content)
            
            if recipients:
                email_data["to"] = recipients
            
            return email_data
        except Exception as e:
            logger.error(
                f"Error generating email draft | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return self._generate_email_draft_fallback(mom)
    
    def _generate_email_draft_fallback(self, mom: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback email draft generation"""
        action_items_text = "\n".join([
            f"- {item.get('task', '')} (Owner: {item.get('owner', 'TBD')})"
            for item in mom.get("action_items", [])
        ])
        
        return {
            "to": [],
            "subject": "Meeting Follow-up",
            "body": f"""Hi Team,

Following up on our recent meeting.

Summary:
{mom.get('summary', 'N/A')}

Action Items:
{action_items_text if action_items_text else 'None identified'}

Best regards""",
            "cc": [],
            "bcc": []
        }
    
    async def detect_risks(
        self,
        transcript: str,
        action_items: List[Dict[str, Any]],
        emails: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """Detect potential risks and deadlines"""
        if not self.client and not self.bedrock_service:
            return []
        
        prompt = f"""Analyze the following information and identify potential risks, missed deadlines, or urgent items that need attention.

Meeting Transcript (excerpt):
{transcript[:1500]}

Action Items:
{json.dumps(action_items, indent=2)}

Identify risks such as:
- Missed or approaching deadlines
- Unclear ownership
- Conflicting priorities
- Resource constraints
- Communication gaps

Return as JSON array of risk descriptions:
{{"risks": ["...", "..."]}}"""

        system_prompt = "You are an expert at identifying project risks and deadline issues."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            risk_data = self._parse_json_response(content)
            return risk_data.get("risks", [])
        except Exception as e:
            logger.error(
                f"Error detecting risks | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return []
    
    async def summarize_email(self, email_content: str) -> str:
        """Summarize email content"""
        if not self.client and not self.bedrock_service:
            return email_content[:200] + "..."
        
        prompt = f"""Summarize the following email in 2-3 sentences, highlighting:
1. Main purpose/request
2. Urgency level
3. Required action (if any)

Email:
{email_content}"""

        system_prompt = "You are an expert at summarizing emails concisely."

        try:
            return await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=150
            )
        except Exception as e:
            logger.error(
                f"Error summarizing email | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return email_content[:200] + "..."
    
    async def summarize_mailbox(self, emails: List[Dict[str, Any]]) -> str:
        """Generate a 2-3 line summary of the entire mailbox"""
        if (not self.client and not self.bedrock_service) or not emails:
            return "Your mailbox contains various emails. Review unread messages and urgent items for immediate attention."
        
        # Create a summary of key emails
        email_summaries = []
        for email in emails[:10]:  # Use top 10 emails
            subject = email.get("subject", "")
            sender = email.get("sender", "")
            is_urgent = email.get("is_urgent", False)
            is_unread = not email.get("is_read", True)
            
            summary_line = f"From {sender}: {subject}"
            if is_urgent:
                summary_line += " [URGENT]"
            if is_unread:
                summary_line += " [UNREAD]"
            email_summaries.append(summary_line)
        
        email_context = "\n".join(email_summaries)
        
        prompt = f"""Based on the following mailbox overview, provide a concise 2-3 sentence summary of the mailbox state, highlighting:
1. Overall mailbox status (unread count, urgent items)
2. Key themes or priorities
3. Recommended actions

Mailbox Overview:
{email_context}

Total emails: {len(emails)}
Unread: {sum(1 for e in emails if not e.get('is_read', True))}
Urgent: {sum(1 for e in emails if e.get('is_urgent', False))}"""

        system_prompt = "You are an expert at analyzing email inboxes and providing concise, actionable summaries."

        try:
            return (await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=200
            )).strip()
        except Exception as e:
            logger.error(
                f"Error summarizing mailbox | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            unread_count = sum(1 for e in emails if not e.get("is_read", True))
            urgent_count = sum(1 for e in emails if e.get("is_urgent", False))
            return f"Your mailbox has {len(emails)} emails with {unread_count} unread messages. {urgent_count} urgent items require immediate attention."
    
    async def summarize_teams(self, messages: List[Dict[str, Any]]) -> str:
        """Generate a 2-3 line summary of Teams messages"""
        if (not self.client and not self.bedrock_service) or not messages:
            return "Your Teams activity shows various conversations. Check unread messages and urgent items for immediate attention."
        
        # Create a summary of key messages
        message_summaries = []
        for msg in messages[:10]:  # Use top 10 messages
            sender = msg.get("sender", "")
            content = msg.get("content", "")[:100]  # First 100 chars
            is_urgent = msg.get("is_urgent", False)
            is_unread = not msg.get("is_read", True)
            
            summary_line = f"From {sender}: {content}"
            if is_urgent:
                summary_line += " [URGENT]"
            if is_unread:
                summary_line += " [UNREAD]"
            message_summaries.append(summary_line)
        
        message_context = "\n".join(message_summaries)
        
        prompt = f"""Based on the following Teams activity overview, provide a concise 2-3 sentence summary of the Teams activity, highlighting:
1. Overall activity status (unread count, urgent items)
2. Key conversations or topics
3. Recommended actions

Teams Activity Overview:
{message_context}

Total messages: {len(messages)}
Unread: {sum(1 for m in messages if not m.get('is_read', True))}
Urgent: {sum(1 for m in messages if m.get('is_urgent', False))}"""

        system_prompt = "You are an expert at analyzing Teams conversations and providing concise, actionable summaries."

        try:
            return (await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=200
            )).strip()
        except Exception as e:
            logger.error(
                f"Error summarizing Teams | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            unread_count = sum(1 for m in messages if not m.get("is_read", True))
            urgent_count = sum(1 for m in messages if m.get("is_urgent", False))
            return f"Your Teams has {len(messages)} messages with {unread_count} unread. {urgent_count} urgent items require immediate attention."
    
    async def suggest_auto_reply(self, email_content: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Suggest automatic reply for email"""
        if not self.client and not self.bedrock_service:
            return {"suggested_reply": "Thank you for your email. I will review and respond shortly.", "confidence": 0.5}
        
        prompt = f"""Based on the following email, suggest an appropriate auto-reply if one is warranted.

Email:
{email_content}

Context: {context or "No additional context"}

Determine if an auto-reply is appropriate and suggest one. Return JSON:
{{
    "suggested_reply": "...",
    "confidence": 0.0-1.0,
    "reasoning": "..."
}}"""

        system_prompt = "You are an expert at crafting appropriate email auto-replies."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(
                f"Error suggesting auto-reply | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {"suggested_reply": "", "confidence": 0.0, "reasoning": "Error generating suggestion"}
    
    async def analyze_meeting_insights(
        self,
        transcript: str,
        mom: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze meeting for sentiment, topics, and engagement insights"""
        if not self.client and not self.bedrock_service:
            return {
                "sentiment": "neutral",
                "topics": [],
                "engagement_score": 0.5,
                "key_insights": []
            }
        
        prompt = f"""Analyze the following meeting transcript and MOM to extract insights.

Transcript:
{transcript[:3000]}

MOM Summary:
{mom.get('summary', '')}

Provide analysis in JSON format:
{{
    "sentiment": "positive|neutral|negative|mixed",
    "sentiment_score": 0.0-1.0,
    "topics": ["topic1", "topic2", ...],
    "engagement_score": 0.0-1.0,
    "key_insights": ["insight1", "insight2", ...],
    "participant_engagement": {{
        "high": ["participant1"],
        "medium": ["participant2"],
        "low": ["participant3"]
    }},
    "meeting_effectiveness": "high|medium|low",
    "recommendations": ["recommendation1", "recommendation2", ...]
}}"""

        system_prompt = "You are an expert at analyzing meetings for sentiment, engagement, and effectiveness."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(
                f"Error analyzing meeting insights | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "sentiment": "neutral",
                "topics": [],
                "engagement_score": 0.5,
                "key_insights": []
            }
    
    async def categorize_email(self, email_content: str, subject: str, sender: str) -> Dict[str, Any]:
        """Categorize email by type, priority, and action required"""
        if not self.client and not self.bedrock_service:
            return {
                "category": "general",
                "priority": "medium",
                "action_required": False,
                "urgency": "normal"
            }
        
        prompt = f"""Categorize the following email.

Subject: {subject}
From: {sender}
Content: {email_content[:2000]}

Provide categorization in JSON format:
{{
    "category": "meeting|action_item|information|question|approval|urgent|newsletter|spam",
    "priority": "low|medium|high|critical",
    "action_required": true|false,
    "urgency": "low|normal|high|urgent",
    "estimated_response_time": "minutes|hours|days|none",
    "suggested_tags": ["tag1", "tag2", ...],
    "reasoning": "..."
}}"""

        system_prompt = "You are an expert at categorizing and prioritizing emails."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(
                f"Error categorizing email | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "category": "general",
                "priority": "medium",
                "action_required": False,
                "urgency": "normal"
            }
    
    async def chat_assistant(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """AI chat assistant for answering questions about meetings, emails, etc."""
        if not self.client and not self.bedrock_service:
            return {
                "answer": "I'm sorry, AI services are not available at the moment.",
                "confidence": 0.0,
                "sources": []
            }
        
        # Build comprehensive context string with actual data
        context_str = ""
        if context:
            # Add meetings with details
            if context.get("meetings"):
                meetings = context["meetings"]
                context_str += f"\n\n=== RECENT MEETINGS ({len(meetings)} total) ===\n"
                for i, meeting in enumerate(meetings[:10], 1):  # Limit to 10 most recent
                    context_str += f"\nMeeting {i}: {meeting.get('title', 'Untitled')}\n"
                    if meeting.get("started_at"):
                        context_str += f"  Date: {meeting['started_at']}\n"
                    if meeting.get("mom_summary"):
                        context_str += f"  Summary: {meeting['mom_summary'][:300]}\n"
                    if meeting.get("mom_decisions"):
                        context_str += f"  Decisions: {len(meeting['mom_decisions'])} decisions made\n"
                        for decision in meeting['mom_decisions'][:3]:  # First 3 decisions
                            if isinstance(decision, dict):
                                context_str += f"    - {decision.get('decision', '')[:100]}\n"
                    if meeting.get("mom_action_items"):
                        context_str += f"  Action Items: {len(meeting['mom_action_items'])} items\n"
                        for item in meeting['mom_action_items'][:3]:  # First 3 action items
                            if isinstance(item, dict):
                                context_str += f"    - {item.get('task', '')[:100]} (Owner: {item.get('owner', 'Unassigned')})\n"
                    if meeting.get("transcript"):
                        context_str += f"  Transcript available: {len(meeting['transcript'])} characters\n"
            
            # Add emails with details
            if context.get("emails"):
                emails = context["emails"]
                context_str += f"\n\n=== RECENT EMAILS ({len(emails)} total) ===\n"
                for i, email in enumerate(emails[:10], 1):  # Limit to 10 most recent
                    context_str += f"\nEmail {i}:\n"
                    context_str += f"  Subject: {email.get('subject', 'No Subject')}\n"
                    if email.get("sender"):
                        context_str += f"  From: {email['sender']}\n"
                    if email.get("preview"):
                        context_str += f"  Preview: {email['preview'][:200]}\n"
                    if email.get("received_at"):
                        context_str += f"  Received: {email['received_at']}\n"
                    if not email.get("is_read", True):
                        context_str += f"  Status: UNREAD\n"
            
            # Add Teams messages with details
            if context.get("teams"):
                teams = context["teams"]
                context_str += f"\n\n=== RECENT TEAMS MESSAGES ({len(teams)} total) ===\n"
                for i, msg in enumerate(teams[:10], 1):  # Limit to 10 most recent
                    context_str += f"\nMessage {i}:\n"
                    if msg.get("sender"):
                        context_str += f"  From: {msg['sender']}\n"
                    if msg.get("content"):
                        context_str += f"  Content: {msg['content'][:200]}\n"
                    if msg.get("sent_at"):
                        context_str += f"  Sent: {msg['sent_at']}\n"
            
            # Add todos with details
            if context.get("todos"):
                todos = context["todos"]
                context_str += f"\n\n=== ACTIVE TODOS ({len(todos)} total) ===\n"
                for i, todo in enumerate(todos[:10], 1):  # Limit to 10 most recent
                    context_str += f"\nTodo {i}:\n"
                    context_str += f"  Title: {todo.get('title', 'Untitled')}\n"
                    if todo.get("description"):
                        context_str += f"  Description: {todo['description'][:200]}\n"
                    context_str += f"  Priority: {todo.get('priority', 'medium')}\n"
                    if todo.get("source_type"):
                        context_str += f"  Source: {todo['source_type']}\n"
        
        prompt = f"""You are an AI assistant helping users understand their meetings, emails, and work communications.

You have access to the following information:
{context_str}

User Question: {query}

Instructions:
- Use the provided context to answer the user's question accurately
- Reference specific meetings, emails, messages, or todos by name/title when relevant
- If the user asks about something not in the context, say so clearly
- Provide actionable insights when possible
- Be concise but thorough

Return JSON:
{{
    "answer": "Your detailed answer here...",
    "confidence": 0.0-1.0,
    "sources": ["source1", "source2", ...],
    "follow_up_questions": ["question1", "question2", ...],
    "action_items": ["action1", "action2", ...]
}}"""

        system_prompt = "You are a helpful AI assistant that helps users understand their work communications, meetings, and tasks."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(
                f"Error in chat assistant | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "answer": "I encountered an error processing your question. Please try again.",
                "confidence": 0.0,
                "sources": []
            }
    
    async def analyze_trends(
        self,
        meetings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze trends across multiple meetings"""
        # Default empty response with all required fields
        default_response = {
            "trends": [],
            "insights": [],
            "recommendations": [],
            "key_themes": [],
            "action_item_trends": None,
            "decision_patterns": None
        }
        
        # Check if AI service is available
        if (not self.client and not self.bedrock_service) or not meetings:
            return default_response
        
        # Prepare meeting summaries
        meeting_summaries = []
        for meeting in meetings[:10]:  # Limit to 10 most recent
            mom = meeting.get("mom", {})
            if isinstance(mom, str):
                try:
                    mom = json.loads(mom)
                except:
                    mom = {}
            
            summary = {
                "title": meeting.get("title", "Untitled"),
                "date": meeting.get("started_at", ""),
                "summary": mom.get("summary", "")[:500] if isinstance(mom, dict) else "",
                "action_items_count": len(mom.get("action_items", [])) if isinstance(mom, dict) else 0,
                "decisions_count": len(mom.get("decisions", [])) if isinstance(mom, dict) else 0
            }
            meeting_summaries.append(summary)
        
        # If no valid meeting summaries, return default
        if not meeting_summaries:
            return default_response
        
        prompt = f"""Analyze trends across the following meetings:

{json.dumps(meeting_summaries, indent=2)}

Identify patterns, trends, and insights. Return JSON:
{{
    "trends": [
        {{"trend": "...", "description": "...", "impact": "high|medium|low"}}
    ],
    "insights": ["insight1", "insight2", ...],
    "recommendations": ["recommendation1", "recommendation2", ...],
    "key_themes": ["theme1", "theme2", ...],
    "action_item_trends": "...",
    "decision_patterns": "..."
}}"""

        system_prompt = "You are an expert at analyzing patterns and trends across multiple meetings."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=3072,
                response_format={"type": "json_object"}
            )
            
            result = self._parse_json_response(content)
            # Ensure all required fields are present
            return {
                "trends": result.get("trends", []),
                "insights": result.get("insights", []),
                "recommendations": result.get("recommendations", []),
                "key_themes": result.get("key_themes", []),
                "action_item_trends": result.get("action_item_trends"),
                "decision_patterns": result.get("decision_patterns")
            }
        except Exception as e:
            logger.error(
                f"Error analyzing trends | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return default_response
    
    async def semantic_search(
        self,
        query: str,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Perform semantic search across documents using AI"""
        if not self.client and not self.bedrock_service or not documents:
            return []
        
        # Prepare document summaries
        doc_summaries = []
        for i, doc in enumerate(documents[:20]):  # Limit to 20 documents
            doc_text = doc.get("text", doc.get("content", doc.get("snippet", "")))[:500]
            doc_summaries.append({
                "id": doc.get("id", str(i)),
                "title": doc.get("title", "Untitled"),
                "text": doc_text
            })
        
        prompt = f"""Given the following search query and documents, rank the documents by relevance to the query.

Search Query: {query}

Documents:
{json.dumps(doc_summaries, indent=2)}

Return JSON with ranked results:
{{
    "results": [
        {{"id": "doc_id", "relevance_score": 0.0-1.0, "reasoning": "..."}},
        ...
    ]
}}"""

        system_prompt = "You are an expert at semantic search and document ranking."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result_data = self._parse_json_response(content)
            ranked_results = result_data.get("results", [])
            
            # Map back to original documents with scores
            scored_docs = []
            for result in ranked_results:
                doc_id = result.get("id")
                for doc in documents:
                    if str(doc.get("id", "")) == str(doc_id):
                        doc["relevance_score"] = result.get("relevance_score", 0.0)
                        doc["relevance_reasoning"] = result.get("reasoning", "")
                        scored_docs.append(doc)
                        break
            
            return sorted(scored_docs, key=lambda x: x.get("relevance_score", 0.0), reverse=True)
        except Exception as e:
            logger.error(
                f"Error in semantic search | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return documents  # Return original order on error
    
    async def generate_todos_from_email(
        self,
        email_subject: str,
        email_body: str,
        email_priority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate actionable todos from email content using AI"""
        if not self.client and not self.bedrock_service:
            # Fallback: return a single todo based on subject
            return [{
                "title": email_subject[:100] if email_subject else "Email action required",
                "description": email_body[:500] if email_body else None,
                "priority": self._map_email_priority_to_todo(email_priority)
            }]
        
        # Clean HTML from email body for better AI processing
        import re
        # Remove HTML tags
        clean_body = re.sub(r'<[^>]+>', '', email_body) if email_body else ""
        # Remove extra whitespace
        clean_body = re.sub(r'\s+', ' ', clean_body).strip()
        
        # Limit body length to avoid token limits
        body_excerpt = clean_body[:3000] if len(clean_body) > 3000 else clean_body
        
        prompt = f"""Analyze the following email and extract actionable todo items that need to be completed.

Email Subject: {email_subject}
Email Body: {body_excerpt}

Instructions:
- Extract only actionable items (tasks that require action, not just informational content)
- Each todo should be specific and actionable
- If the email is purely informational with no action items, return an empty list
- Prioritize todos based on urgency and importance mentioned in the email
- Map email priority to todo priority: CRITICAL -> critical, MEDIUM -> high/medium, LOW -> low/medium

Return JSON format:
{{
    "todos": [
        {{
            "title": "Short, actionable title (max 100 chars)",
            "description": "Detailed description of what needs to be done (optional)",
            "priority": "low|medium|high|critical"
        }},
        ...
    ]
}}"""

        system_prompt = "You are an expert at extracting actionable tasks from emails and converting them into todo items."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result = self._parse_json_response(content)
            todos = result.get("todos", [])
            
            # Ensure all todos have required fields and map priorities
            for todo in todos:
                if "priority" not in todo or not todo["priority"]:
                    todo["priority"] = self._map_email_priority_to_todo(email_priority)
                else:
                    # Normalize priority to lowercase
                    todo["priority"] = todo["priority"].lower()
                    # Validate priority
                    if todo["priority"] not in ["low", "medium", "high", "critical"]:
                        todo["priority"] = self._map_email_priority_to_todo(email_priority)
                
                # Ensure title exists
                if "title" not in todo or not todo["title"]:
                    todo["title"] = email_subject[:100] if email_subject else "Email action required"
            
            return todos
        except Exception as e:
            logger.error(
                f"Error generating todos from email | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            # Fallback: return a single todo
            return [{
                "title": email_subject[:100] if email_subject else "Email action required",
                "description": body_excerpt[:500] if body_excerpt else None,
                "priority": self._map_email_priority_to_todo(email_priority)
            }]
    
    def _map_email_priority_to_todo(self, email_priority: Optional[str]) -> str:
        """Map email priority to todo priority"""
        if not email_priority:
            return "medium"
        
        email_priority_upper = email_priority.upper()
        if email_priority_upper == "CRITICAL":
            return "critical"
        elif email_priority_upper == "HIGH" or email_priority_upper == "MEDIUM":
            return "high"
        elif email_priority_upper == "LOW":
            return "low"
        else:
            return "medium"



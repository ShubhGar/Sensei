"""
AI service for summarization, MOM generation, and insights
"""
import os
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import json
import asyncio
import re
from app.utils.logger import get_logger
from app.services.ai_provider_manager import AIProviderManager

load_dotenv()
logger = get_logger(__name__)


class AIService:
    """Service for AI-powered processing"""
    
    def __init__(
        self,
        use_bedrock: Optional[bool] = None,
        enable_openai: Optional[bool] = None,
        enable_bedrock: Optional[bool] = None,
        use_ensemble: Optional[bool] = None
    ):
        """
        Initialize AI Service
        
        Args:
            use_bedrock: Primary provider preference (True=Bedrock, False=OpenAI, None=auto from env)
            enable_openai: Enable/disable OpenAI service (None=auto from env, can be set to False to disable)
            enable_bedrock: Enable/disable Bedrock service (None=auto from env, can be set to False to disable)
            use_ensemble: Use ensemble mode (both providers in parallel) for improved accuracy (None=auto from env)
        """
        # Initialize provider manager
        self.provider_manager = AIProviderManager(
            use_bedrock=use_bedrock,
            enable_openai=enable_openai,
            enable_bedrock=enable_bedrock,
            use_ensemble=use_ensemble
        )
        
        # Expose provider info for backward compatibility
        self.use_bedrock = self.provider_manager.use_bedrock
        self.openai_service = self.provider_manager.openai_service
        self.bedrock_service = self.provider_manager.bedrock_service
        
        # For backward compatibility with existing code
        self.client = self.openai_service.client if self.openai_service else None
        self.model = self.openai_service.model if self.openai_service else None
        self.fallback_model = self.openai_service.fallback_model if self.openai_service else None
    
    async def _call_ai(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """Unified async method to call either OpenAI or Bedrock via provider manager"""
        return await self.provider_manager.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format
        )
    
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
                # Try one more fix: use regex to fix unescaped quotes in string values
                # Pattern: "key": "value with "unescaped quotes" more text"
                # We'll look for quotes that appear after a colon and space, within what looks like a string value
                fixed_content_v2 = self._fix_unescaped_quotes_regex(fixed_content)
                
                try:
                    return json.loads(fixed_content_v2)
                except json.JSONDecodeError as e3:
                    # Log more context for debugging
                    error_pos = getattr(e3, 'pos', None)
                    if error_pos:
                        start_debug = max(0, error_pos - 100)
                        end_debug = min(len(fixed_content_v2), error_pos + 100)
                        context = fixed_content_v2[start_debug:end_debug]
                        raise ValueError(f"Invalid JSON response: {str(e3)}. Position: {error_pos}. Context: ...{context}...")
                    else:
                        raise ValueError(f"Invalid JSON response: {str(e3)}. Content preview: {fixed_content_v2[:500]}")
    
    def _fix_json_strings(self, content: str) -> str:
        """Fix JSON string values by properly escaping newlines, quotes, and other special characters"""
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
            
            if char == '"':
                if in_string:
                    # We're inside a string - check if this quote should end the string
                    # Look ahead past whitespace to see what comes next
                    lookahead = i + 1
                    while lookahead < len(content) and content[lookahead] in ' \t\n\r':
                        lookahead += 1
                    
                    if lookahead < len(content):
                        next_char = content[lookahead]
                        # If next char is a JSON delimiter or another quote (new key), this ends the string
                        # Delimiters: : (for key-value), , (separator), } (object end), ] (array end)
                        # Also check for " which would start a new key
                        if next_char in [':', ',', '}', ']', '"']:
                            # This is the end of the string
                            in_string = False
                            result.append(char)
                        else:
                            # This is an unescaped quote within the string value - escape it
                            result.append('\\"')
                    else:
                        # End of content - this is the end of the string
                        in_string = False
                        result.append(char)
                else:
                    # Start of a new string
                    in_string = True
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
    
    def _fix_unescaped_quotes_regex(self, content: str) -> str:
        """Fix unescaped quotes in JSON string values using regex patterns"""
        # This method handles cases where quotes appear in the middle of string values
        # Pattern: "key": "value with "unescaped" quotes"
        # We need to escape quotes that are inside string values but not at the boundaries
        
        result = []
        i = 0
        in_string = False
        escape_next = False
        string_start = -1
        
        while i < len(content):
            char = content[i]
            
            if escape_next:
                result.append(char)
                escape_next = False
                i += 1
                continue
            
            if char == '\\':
                result.append(char)
                escape_next = True
                i += 1
                continue
            
            if char == '"':
                if not in_string:
                    # Starting a new string
                    in_string = True
                    string_start = i
                    result.append(char)
                else:
                    # We're inside a string - check if this should end it
                    # Look ahead to see what comes after whitespace
                    j = i + 1
                    while j < len(content) and content[j] in ' \t\n\r':
                        j += 1
                    
                    if j >= len(content):
                        # End of content - close the string
                        in_string = False
                        result.append(char)
                    elif content[j] in [':', ',', '}', ']', '"']:
                        # This quote is followed by a JSON delimiter or new key - it's the end of the string
                        in_string = False
                        result.append(char)
                    else:
                        # This quote is followed by a letter/number - it's an unescaped quote in the string
                        # Escape it
                        result.append('\\"')
                i += 1
                continue
            
            if in_string:
                # Inside string - escape control characters
                if char == '\n':
                    result.append('\\n')
                elif char == '\r':
                    result.append('\\r')
                elif char == '\t':
                    result.append('\\t')
                else:
                    result.append(char)
            else:
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
        if not self.provider_manager.has_any_provider():
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
        
        if not self.provider_manager.has_any_provider():
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
        if not self.provider_manager.has_any_provider():
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
        if not self.provider_manager.has_any_provider():
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
        if not self.provider_manager.has_any_provider():
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
        if not self.provider_manager.has_any_provider():
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
        if not self.provider_manager.has_any_provider():
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
        if not self.provider_manager.has_any_provider():
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
        if not self.provider_manager.has_any_provider():
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
        if not self.provider_manager.has_any_provider():
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
                # Separate completed and incomplete todos
                incomplete_todos = [t for t in todos if not t.get("is_completed", False)]
                completed_todos = [t for t in todos if t.get("is_completed", False)]
                
                if incomplete_todos:
                    context_str += f"\n\n=== ACTIVE TODOS ({len(incomplete_todos)} incomplete) ===\n"
                    for i, todo in enumerate(incomplete_todos[:20], 1):  # Show up to 20 incomplete todos
                        context_str += f"\nTodo {i}:\n"
                        context_str += f"  Title: {todo.get('title', 'Untitled')}\n"
                        if todo.get("description"):
                            context_str += f"  Description: {todo['description'][:200]}\n"
                        context_str += f"  Priority: {todo.get('priority', 'medium')}\n"
                        if todo.get("source_type"):
                            context_str += f"  Source: {todo['source_type']}\n"
                        if todo.get("created_at"):
                            context_str += f"  Created: {todo['created_at']}\n"
                
                if completed_todos:
                    context_str += f"\n\n=== COMPLETED TODOS ({len(completed_todos)} recent) ===\n"
                    for i, todo in enumerate(completed_todos[:10], 1):  # Show up to 10 recently completed
                        context_str += f"\nCompleted Todo {i}:\n"
                        context_str += f"  Title: {todo.get('title', 'Untitled')}\n"
                        if todo.get("description"):
                            context_str += f"  Description: {todo['description'][:200]}\n"
                        context_str += f"  Priority: {todo.get('priority', 'medium')}\n"
                        if todo.get("completed_at"):
                            context_str += f"  Completed: {todo['completed_at']}\n"
            else:
                context_str += f"\n\n=== TODOS ===\nNo todos found in the system."
            
            # Add JIRA issues with details
            if context.get("jira_issues"):
                jira_issues = context["jira_issues"]
                context_str += f"\n\n=== JIRA ISSUES ({len(jira_issues)} total) ===\n"
                # Sort by urgency score (highest first)
                sorted_issues = sorted(jira_issues, key=lambda x: x.get("urgency_score", 0), reverse=True)
                for i, issue in enumerate(sorted_issues[:20], 1):  # Show up to 20 most urgent issues
                    context_str += f"\nJIRA Issue {i}:\n"
                    context_str += f"  Key: {issue.get('key', 'N/A')}\n"
                    context_str += f"  Summary: {issue.get('summary', 'No summary')}\n"
                    if issue.get("status"):
                        context_str += f"  Status: {issue['status']}\n"
                    if issue.get("priority"):
                        context_str += f"  Priority: {issue['priority']}\n"
                    if issue.get("issue_type"):
                        context_str += f"  Type: {issue['issue_type']}\n"
                    if issue.get("description"):
                        context_str += f"  Description: {issue['description'][:200]}\n"
                    if issue.get("due_date"):
                        context_str += f"  Due Date: {issue['due_date']}\n"
                    if issue.get("urgency_score", 0) > 0:
                        context_str += f"  Urgency Score: {issue['urgency_score']}\n"
                    if issue.get("updated_at"):
                        context_str += f"  Last Updated: {issue['updated_at']}\n"
            else:
                context_str += f"\n\n=== JIRA ISSUES ===\nNo JIRA issues found in the system."
        
        prompt = f"""You are an AI assistant helping users understand their meetings, emails, Teams messages, todos, and JIRA issues.

You have access to the following information:
{context_str}

User Question: {query}

Instructions:
- Use the provided context to answer the user's question accurately
- Reference specific meetings, emails, Teams messages, todos, or JIRA issues by name/title/key when relevant
- If the user asks about todos, list ALL todos from the context (both active and completed if they ask for "all todos")
- If the user asks about JIRA issues, list relevant issues with their keys, statuses, priorities, and urgency scores
- When listing todos, organize them by priority (critical > high > medium > low) and show their titles, descriptions, and priorities
- When listing JIRA issues, prioritize by urgency score and status (show blocked/in-progress issues first)
- If the user asks about something not in the context, say so clearly
- Provide actionable insights when possible
- Be concise but thorough
- Cross-reference data sources when relevant (e.g., if a JIRA issue is mentioned in a meeting or email)
- If there are no todos/JIRA issues and the user asks about them, clearly state that there are none in the system

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
            
            parsed_response = self._parse_json_response(content)
            
            # Validate required fields
            if not parsed_response.get("answer"):
                logger.warning("AI response missing 'answer' field, using fallback")
                parsed_response["answer"] = "I received a response but it was incomplete. Please try rephrasing your question."
            
            if "confidence" not in parsed_response:
                parsed_response["confidence"] = 0.5  # Default confidence if missing
            
            return parsed_response
        except json.JSONDecodeError as e:
            logger.error(
                f"JSON parsing error in chat assistant | Error: {type(e).__name__}: {str(e)} | Content preview: {str(content)[:500] if 'content' in locals() else 'N/A'}",
                exc_info=True
            )
            return {
                "answer": "I encountered an error parsing the response. Please try rephrasing your question.",
                "confidence": 0.0,
                "sources": [],
                "follow_up_questions": ["Can you rephrase your question?", "What specific information are you looking for?"]
            }
        except ValueError as e:
            logger.error(
                f"Value error in chat assistant | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "answer": f"I encountered an error: {str(e)}. Please try again.",
                "confidence": 0.0,
                "sources": [],
                "follow_up_questions": ["Can you rephrase your question?"]
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Error in chat assistant | Error: {type(e).__name__}: {error_msg}",
                exc_info=True
            )
            # Provide more helpful error message
            if "quota" in error_msg.lower() or "billing" in error_msg.lower():
                error_response = "AI service quota exceeded. Please check your API billing settings."
            elif "rate limit" in error_msg.lower():
                error_response = "AI service rate limit exceeded. Please wait a moment and try again."
            elif "not available" in error_msg.lower() or "not configured" in error_msg.lower():
                error_response = "AI service is not available. Please check your configuration."
            else:
                error_response = f"I encountered an error processing your question: {error_msg[:200]}. Please try again."
            
            return {
                "answer": error_response,
                "confidence": 0.0,
                "sources": [],
                "follow_up_questions": ["Can you rephrase your question?", "What would you like to know about your todos, meetings, or emails?"]
            }
    
    async def analyze_trends(
        self,
        meetings_data: List[Dict[str, Any]] = None,
        emails_data: List[Dict[str, Any]] = None,
        teams_data: List[Dict[str, Any]] = None,
        todos_data: List[Dict[str, Any]] = None,
        jira_data: List[Dict[str, Any]] = None,
        meetings: List[Dict[str, Any]] = None  # Backward compatibility
    ) -> Dict[str, Any]:
        """Analyze trends across all available data sources (meetings, emails, teams, todos, JIRA)"""
        # Default empty response with all required fields
        default_response = {
            "trends": [],
            "insights": [],
            "recommendations": [],
            "key_themes": [],
            "action_item_trends": None,
            "decision_patterns": None
        }
        
        # Backward compatibility: if meetings parameter is provided, use it
        if meetings is not None and meetings_data is None:
            meetings_data = meetings
        
        # Normalize to empty lists if None
        meetings_data = meetings_data or []
        emails_data = emails_data or []
        teams_data = teams_data or []
        todos_data = todos_data or []
        jira_data = jira_data or []
        
        # Check if AI service is available and we have some data
        if not self.provider_manager.has_any_provider():
            return default_response
        
        if not meetings_data and not emails_data and not teams_data and not todos_data and not jira_data:
            return default_response
        
        # Prepare meeting summaries
        meeting_summaries = []
        for meeting in meetings_data[:10]:  # Limit to 10 most recent
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
        
        # Prepare data summaries for AI analysis
        data_summary = {
            "meetings": {
                "count": len(meeting_summaries),
                "summaries": meeting_summaries
            },
            "emails": {
                "count": len(emails_data),
                "recent_subjects": [e.get("subject", "")[:100] for e in emails_data[:10]],
                "high_importance_count": len([e for e in emails_data if e.get("importance") == "high"])
            },
            "teams_messages": {
                "count": len(teams_data),
                "recent_senders": list(set([t.get("sender", "") for t in teams_data[:20]]))
            },
            "todos": {
                "count": len(todos_data),
                "incomplete_count": len([t for t in todos_data if not t.get("is_completed", False)]),
                "high_priority_count": len([t for t in todos_data if t.get("priority", "").lower() in ["high", "critical"]])
            },
            "jira_issues": {
                "count": len(jira_data),
                "statuses": list(set([j.get("status", "") for j in jira_data])),
                "high_urgency_count": len([j for j in jira_data if j.get("urgency_score", 0) >= 70]),
                "recent_issues": [{"key": j.get("key", ""), "summary": j.get("summary", "")[:100], "status": j.get("status", "")} for j in jira_data[:10]]
            }
        }
        
        prompt = f"""Analyze trends and patterns across all available work data:

MEETINGS ({data_summary['meetings']['count']} meetings):
{json.dumps(meeting_summaries, indent=2) if meeting_summaries else "No meeting data"}

EMAILS ({data_summary['emails']['count']} emails):
- Recent subjects: {', '.join(data_summary['emails']['recent_subjects'][:5])}
- High importance: {data_summary['emails']['high_importance_count']}

TEAMS MESSAGES ({data_summary['teams_messages']['count']} messages):
- Active participants: {', '.join(data_summary['teams_messages']['recent_senders'][:5])}

TODOS ({data_summary['todos']['count']} todos):
- Incomplete: {data_summary['todos']['incomplete_count']}
- High priority: {data_summary['todos']['high_priority_count']}

JIRA ISSUES ({data_summary['jira_issues']['count']} issues):
- Statuses: {', '.join(data_summary['jira_issues']['statuses'][:5])}
- High urgency: {data_summary['jira_issues']['high_urgency_count']}
- Recent issues: {json.dumps(data_summary['jira_issues']['recent_issues'], indent=2) if data_summary['jira_issues']['recent_issues'] else 'None'}

Identify cross-platform patterns, trends, and insights across all these data sources. Look for:
- Common themes across meetings, emails, and Teams
- Action items and their completion status
- Priority patterns (high priority emails, urgent JIRA issues, high priority todos)
- Workload distribution and bottlenecks
- Communication patterns and collaboration trends

Return JSON:
{{
    "trends": [
        {{"trend": "...", "description": "...", "impact": "high|medium|low", "data_sources": ["meetings", "emails", ...]}}
    ],
    "insights": ["insight1", "insight2", ...],
    "recommendations": ["recommendation1", "recommendation2", ...],
    "key_themes": ["theme1", "theme2", ...],
    "action_item_trends": "...",
    "decision_patterns": "...",
    "workload_analysis": "...",
    "priority_patterns": "..."
}}"""

        system_prompt = "You are an expert at analyzing patterns and trends across multiple data sources including meetings, emails, Teams messages, todos, and JIRA issues. You identify cross-platform patterns and provide actionable insights."

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
        if not self.provider_manager.has_any_provider():
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
    
    async def analyze_email_sentiment(self, email_content: str, subject: str) -> Dict[str, Any]:
        """Analyze email sentiment (frustration, urgency, positive/negative)"""
        if not self.provider_manager.has_any_provider():
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.5,
                "urgency_detected": False,
                "frustration_detected": False,
                "tone": "neutral"
            }
        
        prompt = f"""Analyze the sentiment and emotional tone of the following email.

Subject: {subject}
Content: {email_content[:2000]}

Provide analysis in JSON format:
{{
    "sentiment": "positive|neutral|negative|frustrated|urgent",
    "sentiment_score": 0.0-1.0,
    "urgency_detected": true|false,
    "frustration_detected": true|false,
    "tone": "professional|casual|formal|friendly|stern|apologetic",
    "emotional_markers": ["marker1", "marker2", ...],
    "recommended_response_tone": "professional|empathetic|concise|detailed"
}}"""

        system_prompt = "You are an expert at analyzing email sentiment and emotional tone."

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
                f"Error analyzing email sentiment | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.5,
                "urgency_detected": False,
                "frustration_detected": False,
                "tone": "neutral"
            }
    
    async def score_email_priority(
        self,
        email_content: str,
        subject: str,
        sender: str,
        received_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Score email priority by importance (0-100)"""
        if not self.provider_manager.has_any_provider():
            return {
                "priority_score": 50,
                "priority_level": "medium",
                "factors": []
            }
        
        prompt = f"""Score the priority of this email on a scale of 0-100, where:
- 0-30: Low priority (informational, newsletters, non-urgent)
- 31-60: Medium priority (normal business communication)
- 61-80: High priority (action required, deadlines, important decisions)
- 81-100: Critical priority (urgent, blocking, executive communication, emergencies)

Also detect:
- "waiting_for_us": true if the sender is explicitly waiting for a response/action from us (e.g., "waiting for your response", "pending your approval", "need your input", "awaiting your feedback")
- "blocked_on_us": true if someone is blocked and waiting for us (e.g., "blocked on you", "waiting on you", "stuck waiting", "can't proceed without", "depends on you")

Subject: {subject}
From: {sender}
Content: {email_content[:2000]}
Received: {received_at or "Unknown"}

Return JSON:
{{
    "priority_score": 0-100,
    "priority_level": "low|medium|high|critical",
    "urgency_score": 0-100,
    "criticality_score": 0-100,
    "waiting_for_us": true/false,
    "blocked_on_us": true/false,
    "factors": ["factor1", "factor2", ...],
    "reasoning": "..."
}}"""

        system_prompt = "You are an expert at prioritizing emails based on importance, urgency, and business impact."

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
                f"Error scoring email priority | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "priority_score": 50,
                "priority_level": "medium",
                "urgency_score": 50,
                "criticality_score": 50,
                "waiting_for_us": False,
                "blocked_on_us": False,
                "factors": []
            }
    
    async def score_teams_message_priority(
        self,
        message_content: str,
        sender: str,
        sent_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Score Teams message priority by importance (0-100)"""
        if not self.provider_manager.has_any_provider():
            return {
                "priority_score": 50,
                "priority_level": "medium",
                "urgency_score": 50,
                "criticality_score": 50,
                "waiting_for_us": False,
                "blocked_on_us": False,
                "factors": []
            }
        
        prompt = f"""Score the priority of this Teams message on a scale of 0-100, where:
- 0-30: Low priority (informational, casual chat, non-urgent)
- 31-60: Medium priority (normal business communication)
- 61-80: High priority (action required, deadlines, important decisions)
- 81-100: Critical priority (urgent, blocking, @mentions, emergencies)

Also detect:
- "waiting_for_us": true if the sender is explicitly waiting for a response/action from us (e.g., "waiting for your response", "pending your approval", "need your input", "awaiting your feedback", "when can you", "can you please")
- "blocked_on_us": true if someone is blocked and waiting for us (e.g., "blocked on you", "waiting on you", "stuck waiting", "can't proceed without", "depends on you", "blocked by")

From: {sender}
Content: {message_content[:2000]}
Sent: {sent_at or "Unknown"}

Return JSON:
{{
    "priority_score": 0-100,
    "priority_level": "low|medium|high|critical",
    "urgency_score": 0-100,
    "criticality_score": 0-100,
    "waiting_for_us": true/false,
    "blocked_on_us": true/false,
    "factors": ["factor1", "factor2", ...],
    "reasoning": "..."
}}"""

        system_prompt = "You are an expert at prioritizing Teams messages based on importance, urgency, and business impact."

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
                f"Error scoring Teams message priority | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "priority_score": 50,
                "priority_level": "medium",
                "urgency_score": 50,
                "criticality_score": 50,
                "waiting_for_us": False,
                "blocked_on_us": False,
                "factors": []
            }
    
    async def summarize_teams_conversation(
        self,
        messages: List[Dict[str, Any]],
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate thread-level summary for Teams conversation"""
        if (not self.client and not self.bedrock_service) or not messages:
            return {
                "summary": "No summary available",
                "key_points": [],
                "action_items": [],
                "decisions": []
            }
        
        # Prepare conversation context
        conversation_text = []
        for msg in messages[:50]:  # Limit to 50 messages
            sender = msg.get("sender", "Unknown")
            content = msg.get("content", "")[:500]
            sent_at = msg.get("sent_at", "")
            conversation_text.append(f"[{sent_at}] {sender}: {content}")
        
        conversation_context = "\n".join(conversation_text)
        
        prompt = f"""Summarize the following Teams conversation thread.

Conversation:
{conversation_context}

Provide a comprehensive summary in JSON format:
{{
    "summary": "2-3 sentence summary of the conversation",
    "key_points": ["point1", "point2", ...],
    "action_items": [{{"task": "...", "owner": "...", "deadline": "..."}}],
    "decisions": ["decision1", "decision2", ...],
    "participants": ["participant1", "participant2", ...],
    "topic": "main topic discussed"
}}"""

        system_prompt = "You are an expert at summarizing Teams conversations and extracting key information."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result = self._parse_json_response(content)
            if thread_id:
                result["thread_id"] = thread_id
            return result
        except Exception as e:
            logger.error(
                f"Error summarizing Teams conversation | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "summary": "Error generating summary",
                "key_points": [],
                "action_items": [],
                "decisions": []
            }
    
    async def analyze_channel_activity(
        self,
        messages: List[Dict[str, Any]],
        channel_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze Teams channel activity for active discussions and blockers"""
        if (not self.client and not self.bedrock_service) or not messages:
            return {
                "active_discussions": [],
                "blockers": [],
                "activity_level": "low",
                "top_contributors": []
            }
        
        # Prepare channel context
        channel_text = []
        contributors = {}
        for msg in messages[:100]:  # Limit to 100 messages
            sender = msg.get("sender", "Unknown")
            content = msg.get("content", "")[:300]
            channel_text.append(f"{sender}: {content}")
            contributors[sender] = contributors.get(sender, 0) + 1
        
        channel_context = "\n".join(channel_text)
        top_contributors = sorted(contributors.items(), key=lambda x: x[1], reverse=True)[:5]
        
        prompt = f"""Analyze the following Teams channel activity.

Channel: {channel_name or "Unknown"}
Messages:
{channel_context}

Identify:
1. Active discussions (ongoing conversations)
2. Blockers (issues preventing progress)
3. Activity level (high/medium/low)
4. Key topics being discussed

Return JSON:
{{
    "active_discussions": [
        {{"topic": "...", "participants": ["..."], "message_count": N}}
    ],
    "blockers": [
        {{"issue": "...", "impact": "...", "suggested_action": "..."}}
    ],
    "activity_level": "high|medium|low",
    "top_contributors": ["contributor1", "contributor2", ...],
    "key_topics": ["topic1", "topic2", ...]
}}"""

        system_prompt = "You are an expert at analyzing Teams channel activity and identifying blockers."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result = self._parse_json_response(content)
            result["top_contributors"] = [name for name, _ in top_contributors]
            return result
        except Exception as e:
            logger.error(
                f"Error analyzing channel activity | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "active_discussions": [],
                "blockers": [],
                "activity_level": "low",
                "top_contributors": [name for name, _ in top_contributors]
            }
    
    async def analyze_mentions(
        self,
        messages: List[Dict[str, Any]],
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze @mentions in Teams messages"""
        if not messages:
            return {
                "mentions": [],
                "unanswered_mentions": [],
                "requires_response": []
            }
        
        mentions = []
        for msg in messages:
            content = msg.get("content", "")
            # Check for @mentions (improved pattern matching to handle names with spaces)
            if "@" in content:
                # Extract potential mentions - handle both @username and @First Last formats
                import re
                # Pattern 1: @username (single word)
                mention_pattern1 = r'@(\w+(?:\.\w+)*)'
                # Pattern 2: @First Last (two words with space)
                mention_pattern2 = r'@([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
                # Pattern 3: @FirstLast (camelCase)
                mention_pattern3 = r'@([A-Z][a-z]+[A-Z][a-z]+)'
                
                found_mentions = []
                found_mentions.extend(re.findall(mention_pattern1, content))
                found_mentions.extend(re.findall(mention_pattern2, content))
                found_mentions.extend(re.findall(mention_pattern3, content))
                
                for mention in found_mentions:
                    mentions.append({
                        "message_id": msg.get("message_id", ""),
                        "sender": msg.get("sender", ""),
                        "content": content[:200],
                        "mentioned": mention,
                        "sent_at": msg.get("sent_at", ""),
                        "is_read": msg.get("is_read", False)
                    })
        
        # If user_email provided, filter for mentions of that user
        # Also check for common name variations (e.g., "shubham.garg", "Shubham Garg", "shubham garg")
        if user_email:
            user_name = user_email.split("@")[0]
            # Extract first and last name if possible
            name_parts = user_name.split(".")
            first_name = name_parts[0].lower() if name_parts else ""
            last_name = name_parts[1].lower() if len(name_parts) > 1 else ""
            full_name_lower = f"{first_name} {last_name}".strip()
            
            user_mentions = []
            for m in mentions:
                mentioned_lower = m["mentioned"].lower()
                content_lower = m["content"].lower()
                # Check various name formats
                if (first_name in mentioned_lower or 
                    (first_name and last_name and (first_name in mentioned_lower and last_name in mentioned_lower)) or
                    full_name_lower in mentioned_lower or
                    user_name.lower() in mentioned_lower or
                    user_email.lower() in content_lower or
                    "shubham" in mentioned_lower or  # Direct check for "Shubham"
                    "shubham garg" in content_lower or  # Check full name in content
                    "shubham.garg" in content_lower):
                    user_mentions.append(m)
        else:
            user_mentions = mentions
        
        # Identify unanswered mentions (unread or recent)
        unanswered = [m for m in user_mentions if not m.get("is_read", True)]
        
        return {
            "mentions": mentions,
            "unanswered_mentions": unanswered,
            "requires_response": unanswered[:10]  # Top 10 requiring response
        }
    
    async def correlate_cross_platform(
        self,
        emails: List[Dict[str, Any]],
        teams_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Correlate Teams discussions with related emails"""
        if (not self.client and not self.bedrock_service) or (not emails and not teams_messages):
            return {
                "correlations": [],
                "related_items": []
            }
        
        # Prepare summaries
        email_summaries = []
        for email in emails[:20]:
            email_summaries.append({
                "id": email.get("id", ""),
                "subject": email.get("subject", ""),
                "sender": email.get("sender", ""),
                "preview": email.get("body_preview", "")[:200]
            })
        
        teams_summaries = []
        for msg in teams_messages[:20]:
            teams_summaries.append({
                "id": msg.get("message_id", ""),
                "sender": msg.get("sender", ""),
                "content": msg.get("content", "")[:200]
            })
        
        prompt = f"""Identify correlations between the following emails and Teams messages.
Find items that discuss the same topic, project, or issue.

Emails:
{json.dumps(email_summaries, indent=2)}

Teams Messages:
{json.dumps(teams_summaries, indent=2)}

Return JSON:
{{
    "correlations": [
        {{
            "type": "email-teams",
            "email_id": "...",
            "teams_id": "...",
            "topic": "...",
            "confidence": 0.0-1.0,
            "reasoning": "..."
        }}
    ],
    "related_items": [
        {{
            "items": ["email_id1", "teams_id1"],
            "topic": "...",
            "summary": "..."
        }}
    ]
}}"""

        system_prompt = "You are an expert at finding relationships between emails and Teams conversations."

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
                f"Error correlating cross-platform | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "correlations": [],
                "related_items": []
            }
    
    async def generate_daily_digest(
        self,
        emails: List[Dict[str, Any]],
        teams_messages: List[Dict[str, Any]],
        todos: List[Dict[str, Any]],
        meetings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate daily digest combining emails + Teams activity"""
        if not self.provider_manager.has_any_provider():
            return {
                "summary": "Daily digest unavailable",
                "highlights": [],
                "action_items": [],
                "urgent_items": []
            }
        
        # Prepare summaries
        email_summary = f"Emails: {len(emails)} total, {sum(1 for e in emails if not e.get('is_read', True))} unread"
        teams_summary = f"Teams: {len(teams_messages)} messages, {sum(1 for m in teams_messages if not m.get('is_read', True))} unread"
        todos_summary = f"Todos: {len(todos)} active, {sum(1 for t in todos if t.get('priority') == 'critical')} critical"
        meetings_summary = f"Meetings: {len(meetings)} recent"
        
        prompt = f"""Generate a comprehensive daily digest combining all work communications and activities.

{email_summary}
{teams_summary}
{todos_summary}
{meetings_summary}

Create a digest that:
1. Highlights the most important items
2. Lists urgent/action items
3. Identifies dependencies ("who you're waiting on")
4. Provides recommendations

Return JSON:
{{
    "summary": "Overall summary of the day",
    "highlights": ["highlight1", "highlight2", ...],
    "action_items": [
        {{"item": "...", "source": "email|teams|meeting", "priority": "..."}}
    ],
    "urgent_items": ["item1", "item2", ...],
    "dependencies": [
        {{"waiting_on": "...", "item": "...", "deadline": "..."}}
    ],
    "recommendations": ["recommendation1", "recommendation2", ...]
}}"""

        system_prompt = "You are an expert at creating comprehensive daily work digests."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=3072,
                response_format={"type": "json_object"}
            )
            
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(
                f"Error generating daily digest | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "summary": "Error generating digest",
                "highlights": [],
                "action_items": [],
                "urgent_items": []
            }
    
    async def predict_deadline_risks(
        self,
        todos: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        meetings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Predict deadline risks based on todos, emails, and meetings"""
        if not self.provider_manager.has_any_provider():
            return {
                "at_risk": [],
                "warnings": [],
                "recommendations": []
            }
        
        # Prepare context
        todos_context = []
        for todo in todos[:20]:
            todos_context.append({
                "title": todo.get("title", ""),
                "priority": todo.get("priority", "medium"),
                "created_at": todo.get("created_at", ""),
                "source": todo.get("source_type", "")
            })
        
        prompt = f"""Analyze the following todos and predict deadline risks.

Todos:
{json.dumps(todos_context, indent=2)}

Identify:
1. Items at risk of missing deadlines
2. Items that need attention soon
3. Dependencies that might cause delays

Return JSON:
{{
    "at_risk": [
        {{
            "item": "...",
            "risk_level": "high|medium|low",
            "reason": "...",
            "suggested_action": "..."
        }}
    ],
    "warnings": [
        {{
            "item": "...",
            "warning": "...",
            "deadline": "..."
        }}
    ],
    "recommendations": ["recommendation1", "recommendation2", ...]
}}"""

        system_prompt = "You are an expert at predicting deadline risks and project management."

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
                f"Error predicting deadline risks | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "at_risk": [],
                "warnings": [],
                "recommendations": []
            }
    
    async def suggest_teams_response(
        self,
        message_content: str,
        conversation_context: Optional[List[Dict[str, Any]]] = None,
        tone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Suggest polished Teams responses"""
        if not self.provider_manager.has_any_provider():
            return {
                "suggested_response": "Thank you for your message.",
                "tone": "professional",
                "confidence": 0.5
            }
        
        # Prepare conversation context
        context_text = ""
        if conversation_context:
            for msg in conversation_context[-5:]:  # Last 5 messages
                sender = msg.get("sender", "Unknown")
                content = msg.get("content", "")[:200]
                context_text += f"{sender}: {content}\n"
        
        prompt = f"""Suggest a polished, professional Teams response.

Message to respond to:
{message_content}

Conversation context:
{context_text or "No additional context"}

Tone preference: {tone or "professional"}

Return JSON:
{{
    "suggested_response": "...",
    "tone": "professional|casual|empathetic|concise",
    "confidence": 0.0-1.0,
    "alternatives": ["alternative1", "alternative2"]
}}"""

        system_prompt = "You are an expert at crafting professional Teams responses."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(
                f"Error suggesting Teams response | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "suggested_response": "",
                "tone": "professional",
                "confidence": 0.0
            }
    
    async def check_needs_jira(
        self,
        source_type: str,
        content: Dict[str, Any]
    ) -> bool:
        """Check if email or Teams message content needs a JIRA ticket created"""
        if not self.provider_manager.has_any_provider():
            # Fallback: simple keyword-based check
            text = ""
            if source_type == "email":
                text = f"{content.get('subject', '')} {content.get('body_preview', content.get('content', ''))}"
            else:  # teams
                text = content.get('content', '')
            
            # Simple keyword check for task-related content
            # First check for exclusion keywords (leave requests, greetings, etc.)
            exclusion_keywords = [
                'leave request', 'leave application', 'vacation', 'time off', 'holiday',
                'sick leave', 'personal leave', 'annual leave', 'casual leave',
                'applying for leave', 'requesting leave', 'need leave', 'taking leave',
                'leave approval', 'leave balance', 'leave days', 'leave policy',
                'hi', 'hello', 'hey', 'thanks', 'thank you', 'regards', 'best regards',
                'fyi', 'for your information', 'just to inform', 'just informing',
                'meeting invite', 'meeting invitation', 'calendar invite'
            ]
            text_lower = text.lower()
            
            # If it's clearly a leave request, ALWAYS return False (even if it mentions bug)
            # Check for leave-related keywords more strictly
            leave_keywords = ['leave request', 'leave application', 'vacation', 'time off', 'holiday',
                              'sick leave', 'personal leave', 'annual leave', 'casual leave',
                              'applying for leave', 'requesting leave', 'need leave', 'taking leave',
                              'leave approval', 'leave balance', 'leave days', 'applying leave',
                              'request leave', 'approve leave']
            # Check if any leave keyword appears (case-insensitive)
            if any(leave_keyword in text_lower for leave_keyword in leave_keywords):
                return False
            # Additional check: if the word "leave" appears with context words
            if 'leave' in text_lower:
                leave_context_words = ['request', 'application', 'approval', 'balance', 'days', 'taking', 'applying', 'requesting', 'need', 'vacation', 'holiday', 'sick', 'personal', 'annual', 'casual']
                if any(context_word in text_lower for context_word in leave_context_words):
                    return False
            
            # If it's clearly a simple greeting, return False
            greeting_keywords = ['hi', 'hello', 'hey', 'thanks', 'thank you', 'regards', 'best regards']
            if any(exclusion in text_lower for exclusion in exclusion_keywords):
                # But allow if it's also a bug report (e.g., "hi, we have a bug")
                if not any(keyword in text_lower for keyword in ['bug', 'issue', 'problem', 'defect', 'fix', 'error', 'broken']):
                    return False
            
            # Expanded keywords to catch task-related phrases
            task_keywords = [
                'bug', 'issue', 'task', 'feature', 'requirement', 'defect', 'problem', 
                'fix', 'implement', 'develop', 'create', 'build', 'work item', 'ticket',
                'need to fix', 'need to', 'take a look', 'can you', 'please fix', 'fix the',
                'production bug', 'production issue', 'sdk', 'checkout', 'checkoutpro',
                'observed', 'seeing', 'multiple', 'overlay', 'verification', 'calling multiple times',
                'screen getting loaded', 'notification', 'hinge', 'attached', 'reference'
            ]
            
            # Check for exact keyword matches and also phrase matches
            # Also check for bug report patterns
            has_bug_keywords = any(keyword in text_lower for keyword in task_keywords)
            has_bug_patterns = (
                'fix' in text_lower and ('bug' in text_lower or 'issue' in text_lower or 'problem' in text_lower) or
                'need' in text_lower and ('fix' in text_lower or 'look' in text_lower) or
                ('observed' in text_lower or 'seeing' in text_lower) and ('multiple' in text_lower or 'issue' in text_lower or 'problem' in text_lower) or
                'calling multiple times' in text_lower or
                'multiple screen' in text_lower or
                'multiple overlay' in text_lower or
                ('attached' in text_lower and ('video' in text_lower or 'reference' in text_lower or 'sample' in text_lower))
            )
            return has_bug_keywords or has_bug_patterns
        
        if source_type == "email":
            prompt = f"""Analyze this email and determine if it requires creating a JIRA ticket. 
An email needs a JIRA ticket if it contains:
- Bug reports or defect descriptions
- Feature requests or new requirements
- Task assignments or work items
- Technical issues that need tracking
- Development work requests
- Problems that need to be tracked and resolved

DO NOT create JIRA tickets for:
- General questions or information requests
- Meeting invitations or scheduling
- Status updates or notifications
- Casual conversations
- Thank you messages or acknowledgments
- Newsletter or marketing emails

Email Subject: {content.get('subject', 'No Subject')}
From: {content.get('sender', 'Unknown')}
Content: {content.get('body_preview', content.get('content', ''))[:2000]}

IMPORTANT: An email DEFINITELY needs a JIRA ticket if it contains ANY of the following:
- Bug reports: "observed", "seeing", "issue", "problem", "bug", "defect"
- Technical issues: "multiple screen", "overlay", "calling multiple times", "verification issue"
- Problem descriptions: "we had observed", "we are seeing", "our hinge is that"
- Attachments/references: "attached", "video", "sample", "reference" (especially with bug descriptions)
- Requests for investigation: "can you take a look", "need to fix", "please investigate"
- Development work: SDK, API, code, platform integration issues
- Production issues: "production bug", "production issue", "live issue"

DO NOT create JIRA tickets for:
- General questions or information requests
- Meeting invitations or scheduling
- Status updates or notifications
- Casual conversations
- Thank you messages or acknowledgments
- Newsletter or marketing emails

Return JSON:
{{
    "needs_jira": true/false,
    "reasoning": "brief explanation why it does or doesn't need a JIRA ticket",
    "issue_type": "Bug|Task|Story|Epic" (if needs_jira is true, otherwise null)
}}"""
        else:  # teams message
            prompt = f"""Analyze this Teams message and determine if it requires creating a JIRA ticket.
A message needs a JIRA ticket if it contains:
- Bug reports or defect descriptions
- Feature requests or new requirements
- Task assignments or work items
- Technical issues that need tracking
- Development work requests
- Problems that need to be tracked and resolved

DO NOT create JIRA tickets for:
- General questions or information requests
- Casual chat or greetings
- Status updates or acknowledgments
- Quick clarifications

From: {content.get('sender', 'Unknown')}
Content: {content.get('content', '')[:2000]}

Return JSON:
{{
    "needs_jira": true/false,
    "reasoning": "brief explanation why it does or doesn't need a JIRA ticket",
    "issue_type": "Bug|Task|Story|Epic" (if needs_jira is true, otherwise null)
}}"""

        system_prompt = "You are an expert at determining when work items need to be tracked in JIRA."

        try:
            result = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=256,
                response_format={"type": "json_object"}
            )
            
            parsed = self._parse_json_response(result)
            return parsed.get("needs_jira", False)
        except Exception as e:
            logger.warning(f"Error checking if content needs JIRA: {e}")
            # Fallback to keyword-based check
            text = ""
            if source_type == "email":
                text = f"{content.get('subject', '')} {content.get('body_preview', content.get('content', ''))}"
            else:
                text = content.get('content', '')
            task_keywords = ['bug', 'issue', 'task', 'feature', 'requirement', 'defect', 'problem', 'fix', 'implement', 'develop', 'create', 'build', 'work item', 'ticket']
            return any(keyword in text.lower() for keyword in task_keywords)
    
    async def generate_jira_content(
        self,
        source_type: str,
        content: Dict[str, Any]
    ) -> str:
        """Generate AI-formatted content optimized for JIRA conversion from email or message"""
        if not self.provider_manager.has_any_provider():
            # Fallback: return basic formatted text
            if source_type == "email":
                return f"Subject: {content.get('subject', 'No Subject')}\n\nFrom: {content.get('sender', 'Unknown')}\n\n{content.get('body_preview', content.get('content', ''))}"
            else:  # teams message
                return f"From: {content.get('sender', 'Unknown')}\n\n{content.get('content', '')}"
        
        if source_type == "email":
            prompt = f"""Transform the following email into a well-structured text format optimized for JIRA issue creation. 
Extract key information, action items, requirements, and context. Format it clearly with:
- Clear subject/title
- Key points and requirements
- Action items (if any)
- Priority indicators
- Relevant context

Email Subject: {content.get('subject', 'No Subject')}
From: {content.get('sender', 'Unknown')}
Date: {content.get('received_at', 'Unknown')}
Content: {content.get('body_preview', content.get('content', ''))}
Summary: {content.get('summary', '') if content.get('summary') else 'N/A'}
Urgency: {'Urgent' if content.get('is_urgent') else 'Normal'}
Importance: {content.get('importance', 'Normal')}

Generate a clear, structured text that captures all essential information for creating a JIRA issue."""
        else:  # teams message
            prompt = f"""Transform the following Teams message into a well-structured text format optimized for JIRA issue creation.
Extract key information, action items, requirements, and context. Format it clearly with:
- Clear topic/title
- Key points and requirements
- Action items (if any)
- Priority indicators
- Relevant context

From: {content.get('sender', 'Unknown')}
Channel: {content.get('channel_id', 'N/A')}
Date: {content.get('sent_at', 'Unknown')}
Content: {content.get('content', '')}
Summary: {content.get('summary', '') if content.get('summary') else 'N/A'}
Urgent: {'Yes' if content.get('is_urgent') else 'No'}

Generate a clear, structured text that captures all essential information for creating a JIRA issue."""

        system_prompt = "You are an expert at extracting and formatting information from communications into structured text optimized for project management tools like JIRA."

        try:
            formatted_content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=1024
            )
            return formatted_content.strip()
        except Exception as e:
            logger.error(
                f"Error generating JIRA content | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            # Fallback to basic formatting
            if source_type == "email":
                return f"Subject: {content.get('subject', 'No Subject')}\n\nFrom: {content.get('sender', 'Unknown')}\n\n{content.get('body_preview', content.get('content', ''))}"
            else:
                return f"From: {content.get('sender', 'Unknown')}\n\n{content.get('content', '')}"

    async def convert_to_jira(
        self,
        text: str,
        issue_type: str = "Task"
    ) -> Dict[str, Any]:
        """Convert text into Jira issue format"""
        if not self.provider_manager.has_any_provider():
            return {
                "title": text[:100],
                "description": text,
                "issue_type": issue_type
            }
        
        prompt = f"""Convert the following text into a Jira issue format.

Text:
{text[:2000]}

Issue Type: {issue_type}

Return JSON:
{{
    "title": "Issue title (max 255 chars)",
    "description": "Detailed description",
    "issue_type": "{issue_type}",
    "priority": "Highest|High|Medium|Low|Lowest",
    "labels": ["label1", "label2", ...],
    "components": ["component1", "component2", ...],
    "acceptance_criteria": ["criterion1", "criterion2", ...]
}}"""

        system_prompt = "You are an expert at converting text into Jira issue format."

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
                f"Error converting to Jira | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "title": text[:100],
                "description": text,
                "issue_type": issue_type
            }
    
    async def convert_to_confluence(
        self,
        text: str,
        page_type: str = "Documentation"
    ) -> Dict[str, Any]:
        """Convert text into Confluence page format"""
        if not self.provider_manager.has_any_provider():
            return {
                "title": text[:100],
                "content": text,
                "page_type": page_type
            }
        
        prompt = f"""Convert the following text into a Confluence page format.

Text:
{text[:2000]}

Page Type: {page_type}

Return JSON:
{{
    "title": "Page title",
    "content": "Formatted content (can include Confluence markup)",
    "page_type": "{page_type}",
    "labels": ["label1", "label2", ...],
    "sections": [
        {{"heading": "...", "content": "..."}}
    ]
}}"""

        system_prompt = "You are an expert at converting text into Confluence page format."

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
                f"Error converting to Confluence | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "title": text[:100],
                "content": text,
                "page_type": page_type
            }
    
    async def optimize_communication_tone(
        self,
        text: str,
        target_audience: str,
        desired_tone: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Optimize communication tone for target audience"""
        if not self.provider_manager.has_any_provider():
            return {
                "optimized_text": text,
                "tone": desired_tone,
                "changes": []
            }
        
        prompt = f"""Optimize the following communication for tone and audience.

Original text:
{text[:2000]}

Target audience: {target_audience}
Desired tone: {desired_tone}
Context: {context or "No additional context"}

Return JSON:
{{
    "optimized_text": "Optimized version of the text",
    "tone": "{desired_tone}",
    "changes": [
        {{"original": "...", "optimized": "...", "reason": "..."}}
    ],
    "tone_score": 0.0-1.0,
    "recommendations": ["recommendation1", "recommendation2", ...]
}}"""

        system_prompt = "You are an expert at optimizing communication tone for different audiences."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(
                f"Error optimizing tone | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "optimized_text": text,
                "tone": desired_tone,
                "changes": []
            }
    
    async def generate_smart_notifications(
        self,
        emails: List[Dict[str, Any]],
        teams_messages: List[Dict[str, Any]],
        todos: List[Dict[str, Any]],
        meetings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate smart notifications - only alert on truly important items"""
        if not self.provider_manager.has_any_provider():
            # Fallback: simple filtering - ensure all required fields are present
            urgent_emails = [e for e in emails if e.get("is_urgent", False)][:5]
            urgent_teams = [m for m in teams_messages if m.get("is_urgent", False)][:5]
            critical_todos = [t for t in todos if t.get("priority") == "critical"][:5]
            
            notifications = []
            for e in urgent_emails:
                notifications.append({
                    "type": "email",
                    "item_id": str(e.get("id", "")),
                    "priority": "high",
                    "reason": "Urgent email requiring immediate attention",
                    "action_required": True,
                    "urgency_score": 0.8,
                    "item": e
                })
            
            for m in urgent_teams:
                notifications.append({
                    "type": "teams",
                    "item_id": str(m.get("message_id", "") or m.get("id", "")),
                    "priority": "high",
                    "reason": "Urgent Teams message requiring immediate attention",
                    "action_required": True,
                    "urgency_score": 0.8,
                    "item": m
                })
            
            for t in critical_todos:
                notifications.append({
                    "type": "todo",
                    "item_id": str(t.get("id", "")),
                    "priority": "critical",
                    "reason": "Critical todo item with high priority",
                    "action_required": True,
                    "urgency_score": 0.9,
                    "item": t
                })
            
            return {
                "notifications": notifications,
                "total": len(notifications),
                "summary": f"{len(notifications)} urgent items requiring attention"
            }
        
        # Prepare summaries
        email_summaries = []
        for email in emails[:30]:
            email_summaries.append({
                "id": email.get("id", ""),
                "subject": email.get("subject", ""),
                "sender": email.get("sender", ""),
                "is_read": email.get("is_read", True),
                "is_urgent": email.get("is_urgent", False),
                "preview": email.get("body_preview", "")[:200]
            })
        
        teams_summaries = []
        for msg in teams_messages[:30]:
            teams_summaries.append({
                "id": msg.get("message_id", ""),
                "sender": msg.get("sender", ""),
                "is_read": msg.get("is_read", True),
                "is_urgent": msg.get("is_urgent", False),
                "content": msg.get("content", "")[:200]
            })
        
        todos_summaries = []
        for todo in todos[:30]:
            todos_summaries.append({
                "id": todo.get("id", ""),
                "title": todo.get("title", ""),
                "priority": todo.get("priority", "medium"),
                "is_completed": todo.get("is_completed", False)
            })
        
        prompt = f"""Analyze the following items and identify ONLY truly important items that warrant notifications.
Do NOT notify on routine, informational, or low-priority items.

Emails:
{json.dumps(email_summaries, indent=2)}

Teams Messages:
{json.dumps(teams_summaries, indent=2)}

Todos:
{json.dumps(todos_summaries, indent=2)}

Return JSON with only items that are:
- Urgent and require immediate action
- Critical deadlines or blockers
- Executive/important stakeholder communications
- Items the user is explicitly waiting on

Return JSON:
{{
    "notifications": [
        {{
            "type": "email|teams|todo",
            "item_id": "...",
            "priority": "critical|high",
            "reason": "Why this needs notification",
            "action_required": true|false,
            "urgency_score": 0.0-1.0
        }}
    ],
    "total": N,
    "summary": "Brief summary of notifications"
}}"""

        system_prompt = "You are an expert at filtering notifications to only show truly important items that require user attention."

        try:
            content = await self._call_ai(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result = self._parse_json_response(content)
            # Map back to full items
            notifications = []
            for notif in result.get("notifications", []):
                # Always convert item_id to string (AI might return it as integer)
                item_id_raw = notif.get("item_id", "")
                item_id = str(item_id_raw) if item_id_raw is not None else ""
                notif_type = notif.get("type", "")
                
                # Find the full item
                full_item = None
                if notif_type == "email":
                    full_item = next((e for e in emails if e.get("id") == item_id), None)
                elif notif_type == "teams":
                    full_item = next((m for m in teams_messages if m.get("message_id") == item_id or m.get("id") == item_id), None)
                elif notif_type == "todo":
                    full_item = next((t for t in todos if str(t.get("id")) == str(item_id)), None)
                
                # Ensure all required fields are present - item_id must be a string
                notification = {
                    "type": notif_type,
                    "item_id": item_id,  # Already converted to string above
                    "priority": notif.get("priority", "high"),
                    "reason": notif.get("reason", "Requires attention"),
                    "action_required": notif.get("action_required", True),
                    "urgency_score": notif.get("urgency_score"),
                    "item": full_item
                }
                
                if full_item or item_id:  # Only add if we have an item or item_id
                    notifications.append(notification)
            
            result["notifications"] = notifications
            result["total"] = len(notifications)
            if "summary" not in result:
                result["summary"] = f"{len(notifications)} important items require attention"
            return result
        except Exception as e:
            logger.error(
                f"Error generating smart notifications | Error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            # Fallback - ensure all required fields are present
            urgent_emails = [e for e in emails if e.get("is_urgent", False)][:5]
            urgent_teams = [m for m in teams_messages if m.get("is_urgent", False)][:5]
            critical_todos = [t for t in todos if t.get("priority") == "critical"][:5]
            
            notifications = []
            for e in urgent_emails:
                notifications.append({
                    "type": "email",
                    "item_id": str(e.get("id", "")),
                    "priority": "high",
                    "reason": "Urgent email requiring immediate attention",
                    "action_required": True,
                    "urgency_score": 0.8,
                    "item": e
                })
            
            for m in urgent_teams:
                notifications.append({
                    "type": "teams",
                    "item_id": str(m.get("message_id", "") or m.get("id", "")),
                    "priority": "high",
                    "reason": "Urgent Teams message requiring immediate attention",
                    "action_required": True,
                    "urgency_score": 0.8,
                    "item": m
                })
            
            for t in critical_todos:
                notifications.append({
                    "type": "todo",
                    "item_id": str(t.get("id", "")),
                    "priority": "critical",
                    "reason": "Critical todo item with high priority",
                    "action_required": True,
                    "urgency_score": 0.9,
                    "item": t
                })
            
            return {
                "notifications": notifications,
                "total": len(notifications),
                "summary": f"{len(notifications)} urgent items requiring attention"
            }



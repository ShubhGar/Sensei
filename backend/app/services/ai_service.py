"""
AI service for summarization, MOM generation, and insights
"""
import os
from typing import List, Optional, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()


class AIService:
    """Service for AI-powered processing"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
    
    async def generate_mom(
        self,
        transcript: str,
        session_id: str,
        duration: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate Minutes of Meeting from transcript"""
        if not self.client:
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

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing meetings and generating structured minutes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            mom_data = json.loads(content)
            mom_data["session_id"] = session_id
            mom_data["duration"] = duration
            return mom_data
        except Exception as e:
            print(f"Error generating MOM: {e}")
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
    
    async def generate_faqs(self, transcript: str, mom: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate FAQs from transcript and MOM"""
        if not self.client:
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

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at generating relevant FAQs from meeting content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            faq_data = json.loads(content)
            return faq_data.get("faqs", [])
        except Exception as e:
            print(f"Error generating FAQs: {e}")
            return []
    
    async def generate_email_draft(
        self,
        mom: Dict[str, Any],
        recipients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate follow-up email draft from MOM"""
        if not self.client:
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

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at writing professional meeting follow-up emails."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            email_data = json.loads(content)
            
            if recipients:
                email_data["to"] = recipients
            
            return email_data
        except Exception as e:
            print(f"Error generating email draft: {e}")
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
        if not self.client:
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

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at identifying project risks and deadline issues."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            risk_data = json.loads(content)
            return risk_data.get("risks", [])
        except Exception as e:
            print(f"Error detecting risks: {e}")
            return []
    
    async def summarize_email(self, email_content: str) -> str:
        """Summarize email content"""
        if not self.client:
            return email_content[:200] + "..."
        
        prompt = f"""Summarize the following email in 2-3 sentences, highlighting:
1. Main purpose/request
2. Urgency level
3. Required action (if any)

Email:
{email_content}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at summarizing emails concisely."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=150
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error summarizing email: {e}")
            return email_content[:200] + "..."
    
    async def summarize_mailbox(self, emails: List[Dict[str, Any]]) -> str:
        """Generate a 2-3 line summary of the entire mailbox"""
        if not self.client or not emails:
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

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing email inboxes and providing concise, actionable summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error summarizing mailbox: {e}")
            unread_count = sum(1 for e in emails if not e.get("is_read", True))
            urgent_count = sum(1 for e in emails if e.get("is_urgent", False))
            return f"Your mailbox has {len(emails)} emails with {unread_count} unread messages. {urgent_count} urgent items require immediate attention."
    
    async def summarize_teams(self, messages: List[Dict[str, Any]]) -> str:
        """Generate a 2-3 line summary of Teams messages"""
        if not self.client or not messages:
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

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing Teams conversations and providing concise, actionable summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error summarizing Teams: {e}")
            unread_count = sum(1 for m in messages if not m.get("is_read", True))
            urgent_count = sum(1 for m in messages if m.get("is_urgent", False))
            return f"Your Teams has {len(messages)} messages with {unread_count} unread. {urgent_count} urgent items require immediate attention."
    
    async def suggest_auto_reply(self, email_content: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Suggest automatic reply for email"""
        if not self.client:
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

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at crafting appropriate email auto-replies."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"Error suggesting auto-reply: {e}")
            return {"suggested_reply": "", "confidence": 0.0, "reasoning": "Error generating suggestion"}



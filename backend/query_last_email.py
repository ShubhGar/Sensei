#!/usr/bin/env python3
"""
Script to query the AI about the last email
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.ai_service import AIService
from app.integrations.email_integration import EmailIntegration
import json


async def query_last_email():
    """Query the AI about the last email"""
    try:
        # Initialize services
        ai_service = AIService()
        email_integration = EmailIntegration()
        
        print("Fetching emails from Outlook...")
        # Fetch emails
        emails = await email_integration.get_outlook_inbox(max_results=10, unread_only=False)
        
        if not emails:
            print("No emails found. Make sure you're authenticated with Outlook.")
            return
        
        # Get the most recent email (first in the list since they're sorted by receivedDateTime desc)
        last_email = emails[0]
        
        print(f"\nLast Email:")
        print(f"  Subject: {last_email.get('subject', 'No Subject')}")
        print(f"  From: {last_email.get('sender', 'Unknown')}")
        print(f"  Received: {last_email.get('received_at', 'Unknown')}")
        print(f"\nFetching AI analysis...")
        
        # Build context with emails
        context = {
            "emails": []
        }
        
        for email in emails[:5]:  # Include top 5 for context
            email_info = {
                "id": email.get("id", ""),
                "subject": email.get("subject", "No Subject"),
                "sender": email.get("sender", "") or email.get("sender_email", ""),
                "preview": email.get("body_preview", "") or email.get("body", "")[:500],
                "received_at": email.get("received_at", ""),
                "is_read": email.get("is_read", True),
                "importance": email.get("importance", "normal")
            }
            context["emails"].append(email_info)
        
        # Query the AI
        query = "What was my last email about? Please provide a detailed summary."
        response = await ai_service.chat_assistant(query=query, context=context)
        
        print("\n" + "="*60)
        print("AI Response:")
        print("="*60)
        print(response.get("answer", "No answer provided"))
        print("\n" + "="*60)
        
        if response.get("sources"):
            print("\nSources:")
            for source in response["sources"]:
                print(f"  - {source}")
        
        if response.get("confidence"):
            print(f"\nConfidence: {response.get('confidence', 0):.2%}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(query_last_email())


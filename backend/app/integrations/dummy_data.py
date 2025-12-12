"""
Dummy data generator for emails and Teams messages
Used as fallback when real data cannot be fetched
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random


def generate_dummy_emails(max_results: int = 50, unread_only: bool = False) -> List[Dict[str, Any]]:
    """Generate dummy email data"""
    dummy_emails = [
        {
            "id": "dummy-email-1",
            "subject": "Project Update: Q4 Planning Meeting",
            "body": "Hi team,\n\nI wanted to provide an update on our Q4 planning meeting scheduled for next week. Please review the attached agenda and let me know if you have any items to add.\n\nBest regards,\nSarah Johnson",
            "body_preview": "Hi team, I wanted to provide an update on our Q4 planning meeting scheduled for next week...",
            "sender": "Sarah Johnson",
            "sender_email": "sarah.johnson@example.com",
            "received_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "is_read": True,
            "importance": "normal",
            "has_attachments": True
        },
        {
            "id": "dummy-email-2",
            "subject": "URGENT: Action Required - Budget Approval",
            "body": "This is an urgent request for budget approval. The deadline is tomorrow at 5 PM. Please review the attached budget proposal and provide your feedback.\n\nThank you,\nMichael Chen",
            "body_preview": "This is an urgent request for budget approval. The deadline is tomorrow at 5 PM...",
            "sender": "Michael Chen",
            "sender_email": "michael.chen@example.com",
            "received_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "is_read": False,
            "importance": "high",
            "has_attachments": True
        },
        {
            "id": "dummy-email-3",
            "subject": "Re: Weekly Team Standup",
            "body": "Thanks for the update. I'll prepare the demo for the client meeting on Friday.\n\nOn Mon, Oct 15, 2024 at 10:00 AM, John Doe wrote:\n> Let's schedule our weekly standup for tomorrow at 9 AM.\n> Please come prepared with your updates.",
            "body_preview": "Thanks for the update. I'll prepare the demo for the client meeting on Friday...",
            "sender": "Emily Rodriguez",
            "sender_email": "emily.rodriguez@example.com",
            "received_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "is_read": False,
            "importance": "normal",
            "has_attachments": False
        },
        {
            "id": "dummy-email-4",
            "subject": "Approval Needed: Vendor Contract",
            "body": "Hello,\n\nI need your approval on the new vendor contract. Please review the terms and conditions in the attached document. This needs to be signed by end of week.\n\nRegards,\nDavid Kim",
            "body_preview": "Hello, I need your approval on the new vendor contract. Please review the terms...",
            "sender": "David Kim",
            "sender_email": "david.kim@example.com",
            "received_at": (datetime.now() - timedelta(hours=5)).isoformat(),
            "is_read": False,
            "importance": "high",
            "has_attachments": True
        },
        {
            "id": "dummy-email-5",
            "subject": "Meeting Notes: Product Review Session",
            "body": "Attached are the meeting notes from yesterday's product review session. Key decisions:\n1. Launch date moved to November 15th\n2. New feature prioritization approved\n3. Resource allocation confirmed\n\nPlease review and provide feedback.",
            "body_preview": "Attached are the meeting notes from yesterday's product review session...",
            "sender": "Lisa Wang",
            "sender_email": "lisa.wang@example.com",
            "received_at": (datetime.now() - timedelta(hours=8)).isoformat(),
            "is_read": True,
            "importance": "normal",
            "has_attachments": True
        },
        {
            "id": "dummy-email-6",
            "subject": "ASAP: Server Maintenance Window",
            "body": "URGENT: We need to schedule a server maintenance window ASAP. The system is experiencing performance issues. Please confirm your availability for tonight at 8 PM.\n\nThanks,\nIT Support Team",
            "body_preview": "URGENT: We need to schedule a server maintenance window ASAP...",
            "sender": "IT Support",
            "sender_email": "it-support@example.com",
            "received_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
            "is_read": False,
            "importance": "high",
            "has_attachments": False
        },
        {
            "id": "dummy-email-7",
            "subject": "Client Feedback: Project Alpha",
            "body": "Hi,\n\nThe client has provided feedback on Project Alpha. Overall, they're happy with the progress but have requested some changes. I've attached their detailed feedback document.\n\nLet's discuss in our next meeting.\n\nBest,\nRobert Taylor",
            "body_preview": "Hi, The client has provided feedback on Project Alpha. Overall, they're happy...",
            "sender": "Robert Taylor",
            "sender_email": "robert.taylor@example.com",
            "received_at": (datetime.now() - timedelta(hours=12)).isoformat(),
            "is_read": True,
            "importance": "normal",
            "has_attachments": True
        },
        {
            "id": "dummy-email-8",
            "subject": "Deadline Reminder: Quarterly Report",
            "body": "Friendly reminder that the quarterly report is due by end of day Friday. Please ensure all sections are completed and reviewed.\n\nIf you need an extension, please let me know as soon as possible.\n\nRegards,\nJennifer Martinez",
            "body_preview": "Friendly reminder that the quarterly report is due by end of day Friday...",
            "sender": "Jennifer Martinez",
            "sender_email": "jennifer.martinez@example.com",
            "received_at": (datetime.now() - timedelta(hours=3)).isoformat(),
            "is_read": False,
            "importance": "normal",
            "has_attachments": False
        },
        {
            "id": "dummy-email-9",
            "subject": "Re: Conference Registration",
            "body": "I've registered for the conference. Looking forward to attending the sessions on AI and machine learning.\n\nSee you there!\n\nOn Fri, Oct 12, 2024 at 2:00 PM, Conference Team wrote:\n> Registration is now open for the annual tech conference...",
            "body_preview": "I've registered for the conference. Looking forward to attending...",
            "sender": "Alex Thompson",
            "sender_email": "alex.thompson@example.com",
            "received_at": (datetime.now() - timedelta(hours=6)).isoformat(),
            "is_read": True,
            "importance": "low",
            "has_attachments": False
        },
        {
            "id": "dummy-email-10",
            "subject": "Action Required: Sign Off on Design Mockups",
            "body": "Please review and sign off on the design mockups for the new website. The designs are available in the shared folder. We need your approval by Thursday to stay on schedule.\n\nThank you,\nDesign Team",
            "body_preview": "Please review and sign off on the design mockups for the new website...",
            "sender": "Design Team",
            "sender_email": "design@example.com",
            "received_at": (datetime.now() - timedelta(hours=4)).isoformat(),
            "is_read": False,
            "importance": "high",
            "has_attachments": True
        }
    ]
    
    # Filter by unread if requested
    if unread_only:
        filtered = [e for e in dummy_emails if not e.get("is_read", True)]
    else:
        filtered = dummy_emails
    
    # Return up to max_results
    return filtered[:max_results]


def generate_dummy_teams_chats(max_results: int = 50) -> List[Dict[str, Any]]:
    """Generate dummy Teams chat messages with Indian names and realistic conversations"""
    dummy_messages = [
        {
            "chat_id": "dummy-chat-1",
            "message_id": "dummy-msg-1",
            "sender": "Priya Sharma",
            "content": "Hey team, can we move the standup to 10 AM tomorrow?",
            "sent_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "is_read": False
        },
        {
            "chat_id": "dummy-chat-1",
            "message_id": "dummy-msg-2",
            "sender": "Rahul Gupta",
            "content": "Sure, that works for me!",
            "sent_at": (datetime.now() - timedelta(minutes=50)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-1",
            "message_id": "dummy-msg-2a",
            "sender": "Shubham Garg",
            "content": "Yes, 10 AM is fine with me 👍",
            "sent_at": (datetime.now() - timedelta(minutes=48)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-greeting-1",
            "message_id": "dummy-msg-greet-1",
            "sender": "Neha Kapoor",
            "content": "Hi team!",
            "sent_at": (datetime.now() - timedelta(minutes=20)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-greeting-2",
            "message_id": "dummy-msg-greet-2",
            "sender": "Rohit Verma",
            "content": "Hello everyone 👋",
            "sent_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-greeting-3",
            "message_id": "dummy-msg-greet-3",
            "sender": "Sneha Desai",
            "content": "Hey!",
            "sent_at": (datetime.now() - timedelta(minutes=10)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-greeting-4",
            "message_id": "dummy-msg-greet-4",
            "sender": "Amit Joshi",
            "content": "Thanks!",
            "sent_at": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-greeting-5",
            "message_id": "dummy-msg-greet-5",
            "sender": "Deepika Nair",
            "content": "Thank you!",
            "sent_at": (datetime.now() - timedelta(minutes=3)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-greeting-6",
            "message_id": "dummy-msg-greet-6",
            "sender": "Karan Malhotra",
            "content": "Hi",
            "sent_at": (datetime.now() - timedelta(minutes=2)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-2",
            "message_id": "dummy-msg-3",
            "sender": "Anjali Patel",
            "content": "URGENT: The client is asking for an update on the project status. @Shubham Garg can you provide a quick summary?",
            "sent_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "is_read": False
        },
        {
            "chat_id": "dummy-chat-3",
            "message_id": "dummy-msg-4",
            "sender": "Vikram Singh",
            "content": "I've completed the code review. Everything looks good! Ready to merge.",
            "sent_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-4",
            "message_id": "dummy-msg-5",
            "sender": "Kavita Reddy",
            "content": "The demo is scheduled for Friday at 2 PM. Please confirm your attendance.",
            "sent_at": (datetime.now() - timedelta(hours=3)).isoformat(),
            "is_read": False
        },
        {
            "chat_id": "dummy-chat-5",
            "message_id": "dummy-msg-6",
            "sender": "Arjun Mehta",
            "content": "ASAP: We need to fix the bug in production. @Shubham Garg can you take a look? It's related to the CheckoutPro SDK.",
            "sent_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
            "is_read": False
        },
        {
            "chat_id": "dummy-chat-6",
            "message_id": "dummy-msg-7",
            "sender": "Neha Kapoor",
            "content": "Thanks for the great work on the last sprint! The client is very happy with the results.",
            "sent_at": (datetime.now() - timedelta(hours=5)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-7",
            "message_id": "dummy-msg-8",
            "sender": "Rohit Kumar",
            "content": "I'm blocked on the API integration. @Shubham Garg can you help me troubleshoot?",
            "sent_at": (datetime.now() - timedelta(hours=4)).isoformat(),
            "is_read": False
        },
        {
            "chat_id": "dummy-chat-8",
            "message_id": "dummy-msg-9",
            "sender": "Sneha Desai",
            "content": "The deadline for the quarterly report is approaching. Let's make sure we're on track.",
            "sent_at": (datetime.now() - timedelta(hours=6)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-9",
            "message_id": "dummy-msg-10",
            "sender": "Amit Joshi",
            "content": "Action required: Please review the new feature proposal and provide feedback by end of day.",
            "sent_at": (datetime.now() - timedelta(hours=2, minutes=30)).isoformat(),
            "is_read": False
        },
        {
            "chat_id": "dummy-chat-10",
            "message_id": "dummy-msg-11",
            "sender": "Divya Nair",
            "content": "Great job on the presentation today! The stakeholders were impressed.",
            "sent_at": (datetime.now() - timedelta(hours=8)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-11",
            "message_id": "dummy-msg-12",
            "sender": "Rajesh Iyer",
            "content": "IMMEDIATE: The server is down. Investigating the issue now.",
            "sent_at": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "is_read": False
        },
        {
            "chat_id": "dummy-chat-12",
            "message_id": "dummy-msg-13",
            "sender": "Pooja Agarwal",
            "content": "The client meeting has been rescheduled to next Tuesday at 3 PM. Please update your calendars.",
            "sent_at": (datetime.now() - timedelta(hours=7)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-13",
            "message_id": "dummy-msg-14",
            "sender": "Manish Verma",
            "content": "Can someone review the deployment checklist? We're planning to deploy tomorrow morning.",
            "sent_at": (datetime.now() - timedelta(hours=9)).isoformat(),
            "is_read": False
        },
        {
            "chat_id": "dummy-chat-14",
            "message_id": "dummy-msg-15",
            "sender": "Swati Mishra",
            "content": "The quarterly review presentation is ready. I've shared it in the team folder.",
            "sent_at": (datetime.now() - timedelta(hours=10)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-15",
            "message_id": "dummy-msg-16",
            "sender": "Nikhil Shah",
            "content": "URGENT: We need approval for the budget increase. Deadline is today at 5 PM.",
            "sent_at": (datetime.now() - timedelta(minutes=20)).isoformat(),
            "is_read": False
        },
        {
            "chat_id": "dummy-chat-16",
            "message_id": "dummy-msg-17",
            "sender": "Shubham Garg",
            "content": "I've updated the project timeline. The new deadline is December 15th.",
            "sent_at": (datetime.now() - timedelta(hours=11)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-17",
            "message_id": "dummy-msg-18",
            "sender": "Aditya Rao",
            "content": "The API documentation has been updated. Check the wiki for the latest changes.",
            "sent_at": (datetime.now() - timedelta(hours=13)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-18",
            "message_id": "dummy-msg-19",
            "sender": "Kiran Malhotra",
            "content": "ASAP: The production issue has been escalated. We need all hands on deck. @Shubham Garg your expertise on this would be helpful.",
            "sent_at": (datetime.now() - timedelta(minutes=3)).isoformat(),
            "is_read": False
        },
        {
            "chat_id": "dummy-chat-19",
            "message_id": "dummy-msg-20",
            "sender": "Tanvi Chawla",
            "content": "The code review is complete. All tests are passing. Ready for merge.",
            "sent_at": (datetime.now() - timedelta(hours=14)).isoformat(),
            "is_read": True
        },
        {
            "chat_id": "dummy-chat-20",
            "message_id": "dummy-msg-21",
            "sender": "Harsh Tiwari",
            "content": "Action required: Please submit your time-off requests for December by Friday.",
            "sent_at": (datetime.now() - timedelta(hours=15)).isoformat(),
            "is_read": False
        },
        {
            "chat_id": "dummy-chat-21",
            "message_id": "dummy-msg-22",
            "sender": "Isha Bansal",
            "content": "Hey @Shubham Garg, can you share the status update on the wallet SDK documentation?",
            "sent_at": (datetime.now() - timedelta(minutes=45)).isoformat(),
            "is_read": False
        },
        {
            "chat_id": "dummy-chat-22",
            "message_id": "dummy-msg-23",
            "sender": "Varun Agarwal",
            "content": "Thanks Shubham for the quick fix yesterday! Really helped us unblock the deployment.",
            "sent_at": (datetime.now() - timedelta(hours=1, minutes=30)).isoformat(),
            "is_read": True
        }
    ]
    
    return dummy_messages[:max_results]


def generate_dummy_channel_messages(team_id: str, channel_id: str, max_results: int = 50) -> List[Dict[str, Any]]:
    """Generate dummy Teams channel messages with Indian names and realistic conversations"""
    dummy_messages = [
        {
            "message_id": "dummy-channel-msg-1",
            "channel_id": channel_id,
            "sender": "Priya Sharma",
            "content": "Welcome to the project channel! Let's use this space for updates and discussions.",
            "sent_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "is_reply": False,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-2",
            "channel_id": channel_id,
            "sender": "Rahul Gupta",
            "content": "Thanks! I'll post weekly updates here every Monday.",
            "sent_at": (datetime.now() - timedelta(minutes=55)).isoformat(),
            "is_reply": True,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-3",
            "channel_id": channel_id,
            "sender": "Anjali Patel",
            "content": "URGENT: We need to address the performance issues before the next release. Can everyone prioritize this? @Shubham Garg can you take a look?",
            "sent_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "is_reply": False,
            "is_read": False
        },
        {
            "message_id": "dummy-channel-msg-4",
            "channel_id": channel_id,
            "sender": "Vikram Singh",
            "content": "I've started working on it. Should have a fix ready by tomorrow.",
            "sent_at": (datetime.now() - timedelta(minutes=25)).isoformat(),
            "is_reply": True,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-5",
            "channel_id": channel_id,
            "sender": "Kavita Reddy",
            "content": "The sprint planning meeting is scheduled for this Friday. Please come prepared with your capacity estimates.",
            "sent_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "is_reply": False,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-6",
            "channel_id": channel_id,
            "sender": "Arjun Mehta",
            "content": "ASAP: Client is requesting a demo. Can we schedule it for this week?",
            "sent_at": (datetime.now() - timedelta(minutes=10)).isoformat(),
            "is_reply": False,
            "is_read": False
        },
        {
            "message_id": "dummy-channel-msg-7",
            "channel_id": channel_id,
            "sender": "Neha Kapoor",
            "content": "I can do Thursday afternoon. Does that work for everyone?",
            "sent_at": (datetime.now() - timedelta(minutes=8)).isoformat(),
            "is_reply": True,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-8",
            "channel_id": channel_id,
            "sender": "Rohit Kumar",
            "content": "The new feature is ready for testing. Please review the PR when you have a chance.",
            "sent_at": (datetime.now() - timedelta(hours=3)).isoformat(),
            "is_reply": False,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-9",
            "channel_id": channel_id,
            "sender": "Sneha Desai",
            "content": "Action required: Please update your status in the project tracker by end of day.",
            "sent_at": (datetime.now() - timedelta(hours=4)).isoformat(),
            "is_reply": False,
            "is_read": False
        },
        {
            "message_id": "dummy-channel-msg-10",
            "channel_id": channel_id,
            "sender": "Amit Joshi",
            "content": "Great work on the last deployment! Everything went smoothly.",
            "sent_at": (datetime.now() - timedelta(hours=5)).isoformat(),
            "is_reply": False,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-11",
            "channel_id": channel_id,
            "sender": "Divya Nair",
            "content": "The sprint retrospective is scheduled for Friday at 2 PM. Please come prepared with your feedback.",
            "sent_at": (datetime.now() - timedelta(hours=6)).isoformat(),
            "is_reply": False,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-12",
            "channel_id": channel_id,
            "sender": "Rajesh Iyer",
            "content": "I've fixed the bug in the authentication module. The fix is in PR #1234.",
            "sent_at": (datetime.now() - timedelta(hours=7)).isoformat(),
            "is_reply": False,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-13",
            "channel_id": channel_id,
            "sender": "Pooja Agarwal",
            "content": "URGENT: The client demo has been moved to tomorrow. Can everyone confirm availability?",
            "sent_at": (datetime.now() - timedelta(minutes=12)).isoformat(),
            "is_reply": False,
            "is_read": False
        },
        {
            "message_id": "dummy-channel-msg-14",
            "channel_id": channel_id,
            "sender": "Manish Verma",
            "content": "I'm available. What time is the demo?",
            "sent_at": (datetime.now() - timedelta(minutes=10)).isoformat(),
            "is_reply": True,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-15",
            "channel_id": channel_id,
            "sender": "Swati Mishra",
            "content": "The demo is at 3 PM. I'll send the agenda shortly.",
            "sent_at": (datetime.now() - timedelta(minutes=8)).isoformat(),
            "is_reply": True,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-16",
            "channel_id": channel_id,
            "sender": "Nikhil Shah",
            "content": "The new feature branch is ready for testing. QA team, please start your review.",
            "sent_at": (datetime.now() - timedelta(hours=8)).isoformat(),
            "is_reply": False,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-17",
            "channel_id": channel_id,
            "sender": "Aditya Rao",
            "content": "Action required: Please update your project status in the tracker by end of day.",
            "sent_at": (datetime.now() - timedelta(hours=9)).isoformat(),
            "is_reply": False,
            "is_read": False
        },
        {
            "message_id": "dummy-channel-msg-18",
            "channel_id": channel_id,
            "sender": "Kiran Malhotra",
            "content": "The infrastructure monitoring dashboard is now live. Check it out!",
            "sent_at": (datetime.now() - timedelta(hours=10)).isoformat(),
            "is_reply": False,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-19",
            "channel_id": channel_id,
            "sender": "Tanvi Chawla",
            "content": "ASAP: We need to address the security vulnerability found in the latest scan. Priority fix needed. @Shubham Garg your expertise would be helpful here.",
            "sent_at": (datetime.now() - timedelta(minutes=7)).isoformat(),
            "is_reply": False,
            "is_read": False
        },
        {
            "message_id": "dummy-channel-msg-20",
            "channel_id": channel_id,
            "sender": "Shubham Garg",
            "content": "I'm on it. Should have a patch ready within the hour.",
            "sent_at": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "is_reply": True,
            "is_read": True
        },
        {
            "message_id": "dummy-channel-msg-21",
            "channel_id": channel_id,
            "sender": "Harsh Tiwari",
            "content": "Hey @Shubham Garg, can you share the status on the CheckoutPro SDK integration?",
            "sent_at": (datetime.now() - timedelta(minutes=2)).isoformat(),
            "is_reply": False,
            "is_read": False
        },
        {
            "message_id": "dummy-channel-msg-22",
            "channel_id": channel_id,
            "sender": "Isha Bansal",
            "content": "Thanks Shubham for helping with the deployment yesterday! Really appreciate it.",
            "sent_at": (datetime.now() - timedelta(hours=1, minutes=15)).isoformat(),
            "is_reply": False,
            "is_read": True
        }
    ]
    
    return dummy_messages[:max_results]


def generate_dummy_joined_teams(max_results: int = 100) -> List[Dict[str, Any]]:
    """Generate dummy Teams that the user is a member of with Indian context"""
    dummy_teams = [
        {
            "id": "dummy-team-engineering",
            "displayName": "PayU Engineering Team",
            "description": "Main engineering team for product development - CheckoutPro SDK, Payment Gateway",
            "internalId": "19:payu-engineering@payu.in",
            "visibility": "private"
        },
        {
            "id": "dummy-team-checkoutpro",
            "displayName": "CheckoutPro SDK Team",
            "description": "Cross-functional team for CheckoutPro SDK development and integration",
            "internalId": "19:checkoutpro-sdk@payu.in",
            "visibility": "private"
        },
        {
            "id": "dummy-team-payments",
            "displayName": "Payments & Integration",
            "description": "Payment gateway integration and merchant onboarding team",
            "internalId": "19:payments-integration@payu.in",
            "visibility": "private"
        },
        {
            "id": "dummy-team-support",
            "displayName": "Customer Support - India",
            "description": "Customer success and support team for Indian market",
            "internalId": "19:support-india@payu.in",
            "visibility": "private"
        },
        {
            "id": "dummy-team-allhands",
            "displayName": "PayU India - All Hands",
            "description": "Company-wide announcements and discussions for PayU India",
            "internalId": "19:payu-india-allhands@payu.in",
            "visibility": "public"
        },
        {
            "id": "dummy-team-wallet",
            "displayName": "Wallet SDK Team",
            "description": "Mia Wallet SDK development and documentation team",
            "internalId": "19:wallet-sdk@payu.in",
            "visibility": "private"
        },
        {
            "id": "dummy-team-design",
            "displayName": "Design & UX - PayU",
            "description": "Design and user experience team for PayU products",
            "internalId": "19:design-ux-payu@payu.in",
            "visibility": "private"
        },
        {
            "id": "dummy-team-devops",
            "displayName": "DevOps & Infrastructure - India",
            "description": "DevOps and infrastructure management for PayU India",
            "internalId": "19:devops-india@payu.in",
            "visibility": "private"
        }
    ]
    
    return dummy_teams[:max_results]


def generate_dummy_team_channels(team_id: str, max_results: int = 100) -> List[Dict[str, Any]]:
    """Generate dummy channels for a Team"""
    # Generate different channels based on team_id to make it more realistic
    base_channels = [
        {
            "id": f"{team_id}-channel-general",
            "displayName": "General",
            "description": "General team discussions",
            "email": f"general-{team_id}@example.com",
            "webUrl": f"https://teams.microsoft.com/l/channel/{team_id}-channel-general",
            "membershipType": "standard",
            "createdDateTime": (datetime.now() - timedelta(days=180)).isoformat()
        },
        {
            "id": f"{team_id}-channel-announcements",
            "displayName": "Announcements",
            "description": "Team announcements and important updates",
            "email": f"announcements-{team_id}@example.com",
            "webUrl": f"https://teams.microsoft.com/l/channel/{team_id}-channel-announcements",
            "membershipType": "standard",
            "createdDateTime": (datetime.now() - timedelta(days=150)).isoformat()
        },
        {
            "id": f"{team_id}-channel-random",
            "displayName": "Random",
            "description": "Non-work banter and water cooler chat",
            "email": f"random-{team_id}@example.com",
            "webUrl": f"https://teams.microsoft.com/l/channel/{team_id}-channel-random",
            "membershipType": "standard",
            "createdDateTime": (datetime.now() - timedelta(days=120)).isoformat()
        }
    ]
    
    # Add team-specific channels based on team name patterns
    if "engineering" in team_id.lower() or "team-1" in team_id:
        base_channels.extend([
            {
                "id": f"{team_id}-channel-code-review",
                "displayName": "Code Review",
                "description": "Code review discussions and PR feedback",
                "email": f"code-review-{team_id}@example.com",
                "webUrl": f"https://teams.microsoft.com/l/channel/{team_id}-channel-code-review",
                "membershipType": "standard",
                "createdDateTime": (datetime.now() - timedelta(days=90)).isoformat()
            },
            {
                "id": f"{team_id}-channel-standup",
                "displayName": "Daily Standup",
                "description": "Daily standup updates and async communication",
                "email": f"standup-{team_id}@example.com",
                "webUrl": f"https://teams.microsoft.com/l/channel/{team_id}-channel-standup",
                "membershipType": "standard",
                "createdDateTime": (datetime.now() - timedelta(days=60)).isoformat()
            }
        ])
    elif "product" in team_id.lower() or "launch" in team_id.lower() or "team-2" in team_id:
        base_channels.extend([
            {
                "id": f"{team_id}-channel-planning",
                "displayName": "Sprint Planning",
                "description": "Sprint planning and backlog discussions",
                "email": f"planning-{team_id}@example.com",
                "webUrl": f"https://teams.microsoft.com/l/channel/{team_id}-channel-planning",
                "membershipType": "standard",
                "createdDateTime": (datetime.now() - timedelta(days=80)).isoformat()
            },
            {
                "id": f"{team_id}-channel-launch-updates",
                "displayName": "Launch Updates",
                "description": "Product launch status and milestone updates",
                "email": f"launch-updates-{team_id}@example.com",
                "webUrl": f"https://teams.microsoft.com/l/channel/{team_id}-channel-launch-updates",
                "membershipType": "standard",
                "createdDateTime": (datetime.now() - timedelta(days=50)).isoformat()
            }
        ])
    elif "sales" in team_id.lower() or "marketing" in team_id.lower() or "team-3" in team_id:
        base_channels.extend([
            {
                "id": f"{team_id}-channel-leads",
                "displayName": "Sales Leads",
                "description": "Sales leads and opportunity discussions",
                "email": f"leads-{team_id}@example.com",
                "webUrl": f"https://teams.microsoft.com/l/channel/{team_id}-channel-leads",
                "membershipType": "standard",
                "createdDateTime": (datetime.now() - timedelta(days=70)).isoformat()
            },
            {
                "id": f"{team_id}-channel-campaigns",
                "displayName": "Marketing Campaigns",
                "description": "Marketing campaign planning and execution",
                "email": f"campaigns-{team_id}@example.com",
                "webUrl": f"https://teams.microsoft.com/l/channel/{team_id}-channel-campaigns",
                "membershipType": "standard",
                "createdDateTime": (datetime.now() - timedelta(days=55)).isoformat()
            }
        ])
    
    return base_channels[:max_results]


def generate_dummy_meetings() -> List[Dict[str, Any]]:
    """Generate dummy meeting sessions with MOM, FAQ, and email draft"""
    now = datetime.now()
    
    dummy_meetings = [
        {
            "id": "dummy-meeting-1",
            "title": "Q4 Planning & Strategy Review",
            "started_at": (now - timedelta(days=2, hours=3)).isoformat(),
            "ended_at": (now - timedelta(days=2, hours=1)).isoformat(),
            "is_active": False,
            "transcript": "We discussed the Q4 roadmap and strategic initiatives. Key focus areas include product expansion, market penetration, and team scaling. The team agreed on prioritizing three main projects: Project Alpha, Beta, and Gamma. Budget allocation was approved for the next quarter.",
            "full_transcript": "We discussed the Q4 roadmap and strategic initiatives. Key focus areas include product expansion, market penetration, and team scaling. The team agreed on prioritizing three main projects: Project Alpha, Beta, and Gamma. Budget allocation was approved for the next quarter. Sarah presented the market analysis showing strong growth potential. Michael raised concerns about resource constraints. We decided to hire 5 new team members by end of month. Emily will lead the recruitment process.",
            "mom": {
                "session_id": "dummy-meeting-1",
                "summary": "The Q4 Planning & Strategy Review meeting covered strategic initiatives, budget allocation, and team expansion plans. Key decisions were made on project prioritization and resource allocation.",
                "decisions": [
                    {
                        "decision": "Prioritize Project Alpha, Beta, and Gamma for Q4",
                        "context": "Based on market analysis and strategic alignment",
                        "timestamp": None
                    },
                    {
                        "decision": "Approve budget allocation for Q4 initiatives",
                        "context": "Budget approved by finance team",
                        "timestamp": None
                    },
                    {
                        "decision": "Hire 5 new team members by end of month",
                        "context": "To support project expansion",
                        "timestamp": None
                    }
                ],
                "action_items": [
                    {
                        "task": "Complete market analysis report for Project Alpha",
                        "owner": "Sarah Johnson",
                        "deadline": "2024-11-15",
                        "priority": "high",
                        "context": "Required for stakeholder presentation"
                    },
                    {
                        "task": "Initiate recruitment process for 5 new hires",
                        "owner": "Emily Rodriguez",
                        "deadline": "2024-11-20",
                        "priority": "high",
                        "context": "Urgent to meet project timelines"
                    },
                    {
                        "task": "Prepare budget breakdown for approved initiatives",
                        "owner": "Michael Chen",
                        "deadline": "2024-11-12",
                        "priority": "medium",
                        "context": "Finance team requirement"
                    }
                ],
                "key_points": [
                    "Strong market growth potential identified",
                    "Resource constraints need to be addressed",
                    "Three main projects prioritized for Q4",
                    "Budget approval secured"
                ],
                "attendees": ["Sarah Johnson", "Michael Chen", "Emily Rodriguez", "David Kim", "Lisa Wang"],
                "duration": "2 hours"
            },
            "faqs": [
                {
                    "question": "What are the three main projects prioritized for Q4?",
                    "answer": "The three main projects are Project Alpha, Beta, and Gamma. These were selected based on strategic alignment and market potential.",
                    "context": "Project prioritization discussion"
                },
                {
                    "question": "When is the deadline for hiring new team members?",
                    "answer": "The deadline for hiring 5 new team members is by the end of the month (November 30, 2024).",
                    "context": "Team expansion discussion"
                },
                {
                    "question": "Who is responsible for the market analysis report?",
                    "answer": "Sarah Johnson is responsible for completing the market analysis report for Project Alpha by November 15, 2024.",
                    "context": "Action items assignment"
                }
            ],
            "email_draft": {
                "to": ["sarah.johnson@example.com", "michael.chen@example.com", "emily.rodriguez@example.com"],
                "subject": "Q4 Planning & Strategy Review - Meeting Summary",
                "body": "Hi Team,\n\nThank you for attending today's Q4 Planning & Strategy Review meeting. Here's a summary of what we discussed:\n\nKey Decisions:\n- Prioritized Project Alpha, Beta, and Gamma for Q4\n- Approved budget allocation for Q4 initiatives\n- Approved hiring 5 new team members by end of month\n\nAction Items:\n1. Sarah Johnson: Complete market analysis report for Project Alpha (Deadline: Nov 15)\n2. Emily Rodriguez: Initiate recruitment process for 5 new hires (Deadline: Nov 20)\n3. Michael Chen: Prepare budget breakdown for approved initiatives (Deadline: Nov 12)\n\nPlease review the attached meeting notes and let me know if you have any questions.\n\nBest regards,\nMeeting Organizer",
                "cc": ["david.kim@example.com", "lisa.wang@example.com"],
                "bcc": None
            },
            "risks": [
                "Resource constraints may impact project timelines if hiring is delayed",
                "Budget approval is pending final finance review"
            ]
        },
        {
            "id": "dummy-meeting-2",
            "title": "Product Launch Planning Session",
            "started_at": (now - timedelta(days=5, hours=2)).isoformat(),
            "ended_at": (now - timedelta(days=5)).isoformat(),
            "is_active": False,
            "transcript": "Product launch planning session focused on the upcoming release of our new feature set. We discussed launch timeline, marketing strategy, and customer communication plan.",
            "full_transcript": "Product launch planning session focused on the upcoming release of our new feature set. We discussed launch timeline, marketing strategy, and customer communication plan. The team agreed on a soft launch date of December 1st. Marketing will prepare campaign materials. Support team needs to be briefed on new features. Technical team confirmed all features are ready for production.",
            "mom": {
                "session_id": "dummy-meeting-2",
                "summary": "Product Launch Planning Session covered the timeline, marketing strategy, and customer communication for the upcoming feature release. Soft launch scheduled for December 1st.",
                "decisions": [
                    {
                        "decision": "Set soft launch date for December 1st, 2024",
                        "context": "Based on technical readiness and market timing",
                        "timestamp": None
                    },
                    {
                        "decision": "Approve marketing campaign strategy",
                        "context": "Campaign materials to be prepared by marketing team",
                        "timestamp": None
                    }
                ],
                "action_items": [
                    {
                        "task": "Prepare marketing campaign materials",
                        "owner": "Marketing Team",
                        "deadline": "2024-11-25",
                        "priority": "high",
                        "context": "Required for launch"
                    },
                    {
                        "task": "Brief support team on new features",
                        "owner": "Support Lead",
                        "deadline": "2024-11-28",
                        "priority": "high",
                        "context": "Customer support preparation"
                    },
                    {
                        "task": "Final production readiness check",
                        "owner": "Technical Team",
                        "deadline": "2024-11-29",
                        "priority": "high",
                        "context": "Pre-launch verification"
                    }
                ],
                "key_points": [
                    "Soft launch scheduled for December 1st",
                    "All features confirmed ready for production",
                    "Marketing campaign strategy approved",
                    "Support team briefing required"
                ],
                "attendees": ["Product Manager", "Marketing Team", "Technical Lead", "Support Lead"],
                "duration": "2 hours"
            },
            "faqs": [
                {
                    "question": "When is the product launch date?",
                    "answer": "The soft launch is scheduled for December 1st, 2024.",
                    "context": "Launch timeline discussion"
                },
                {
                    "question": "What features are included in this launch?",
                    "answer": "The launch includes the new feature set that was discussed. All features have been confirmed ready for production by the technical team.",
                    "context": "Feature readiness discussion"
                },
                {
                    "question": "Who needs to be briefed before the launch?",
                    "answer": "The support team needs to be briefed on the new features by November 28th to ensure they can assist customers effectively.",
                    "context": "Support team preparation"
                }
            ],
            "email_draft": {
                "to": ["product@example.com", "marketing@example.com"],
                "subject": "Product Launch Planning - Action Items",
                "body": "Hi Team,\n\nFollowing our Product Launch Planning Session, here are the key action items:\n\nLaunch Date: December 1st, 2024 (Soft Launch)\n\nAction Items:\n1. Marketing Team: Prepare campaign materials (Deadline: Nov 25)\n2. Support Lead: Brief support team on new features (Deadline: Nov 28)\n3. Technical Team: Final production readiness check (Deadline: Nov 29)\n\nAll features are confirmed ready for production. Please ensure all action items are completed before the launch date.\n\nBest regards,\nProduct Team",
                "cc": ["technical@example.com", "support@example.com"],
                "bcc": None
            },
            "risks": [
                "Marketing materials may not be ready in time if delays occur",
                "Support team briefing is critical for customer satisfaction"
            ]
        },
        {
            "id": "dummy-meeting-3",
            "title": "Client Feedback & Requirements Discussion",
            "started_at": (now - timedelta(days=7, hours=4)).isoformat(),
            "ended_at": (now - timedelta(days=7, hours=2)).isoformat(),
            "is_active": False,
            "transcript": "Client feedback session covered their requirements and concerns. We discussed feature requests, timeline adjustments, and resource needs.",
            "full_transcript": "Client feedback session covered their requirements and concerns. We discussed feature requests, timeline adjustments, and resource needs. The client requested three new features: Advanced Analytics, Custom Reporting, and API Integration. They also requested timeline adjustment for Phase 2 delivery. We agreed to review and provide updated timeline by next week.",
            "mom": {
                "session_id": "dummy-meeting-3",
                "summary": "Client Feedback & Requirements Discussion covered new feature requests, timeline adjustments, and resource planning. Client requested Advanced Analytics, Custom Reporting, and API Integration features.",
                "decisions": [
                    {
                        "decision": "Review and provide updated timeline for Phase 2 by next week",
                        "context": "Client requested timeline adjustment",
                        "timestamp": None
                    },
                    {
                        "decision": "Prioritize client feature requests: Advanced Analytics, Custom Reporting, API Integration",
                        "context": "Based on client feedback and business value",
                        "timestamp": None
                    }
                ],
                "action_items": [
                    {
                        "task": "Review Phase 2 timeline and provide updated estimate",
                        "owner": "Project Manager",
                        "deadline": "2024-11-18",
                        "priority": "high",
                        "context": "Client requirement"
                    },
                    {
                        "task": "Assess feasibility of Advanced Analytics feature",
                        "owner": "Technical Lead",
                        "deadline": "2024-11-16",
                        "priority": "high",
                        "context": "Feature planning"
                    },
                    {
                        "task": "Prepare requirements document for Custom Reporting and API Integration",
                        "owner": "Product Owner",
                        "deadline": "2024-11-17",
                        "priority": "medium",
                        "context": "Feature specification"
                    }
                ],
                "key_points": [
                    "Client requested three new features",
                    "Timeline adjustment needed for Phase 2",
                    "Updated timeline to be provided by next week",
                    "Feature prioritization required"
                ],
                "attendees": ["Client Representative", "Project Manager", "Technical Lead", "Product Owner"],
                "duration": "2 hours"
            },
            "faqs": [
                {
                    "question": "What features did the client request?",
                    "answer": "The client requested three new features: Advanced Analytics, Custom Reporting, and API Integration.",
                    "context": "Feature requests discussion"
                },
                {
                    "question": "When will the updated Phase 2 timeline be provided?",
                    "answer": "The updated timeline for Phase 2 will be provided by next week (November 18, 2024).",
                    "context": "Timeline discussion"
                },
                {
                    "question": "Who is responsible for assessing the Advanced Analytics feature?",
                    "answer": "The Technical Lead is responsible for assessing the feasibility of the Advanced Analytics feature by November 16, 2024.",
                    "context": "Action items assignment"
                }
            ],
            "email_draft": {
                "to": ["client@example.com"],
                "subject": "Client Feedback & Requirements - Follow-up",
                "body": "Dear Client,\n\nThank you for the productive discussion during our feedback session. As discussed, we will:\n\n1. Review and provide an updated timeline for Phase 2 by November 18, 2024\n2. Assess the feasibility of the requested features: Advanced Analytics, Custom Reporting, and API Integration\n3. Prepare detailed requirements documents for your review\n\nWe appreciate your feedback and will keep you updated on our progress.\n\nBest regards,\nProject Team",
                "cc": ["project.manager@example.com"],
                "bcc": None
            },
            "risks": [
                "Timeline adjustment may impact other project phases",
                "Feature complexity may require additional resources"
            ]
        }
    ]
    
    return dummy_meetings


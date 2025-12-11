"""
Pydantic schemas for request/response models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TranscriptSegment(BaseModel):
    """Transcript segment with speaker"""
    speaker: str
    text: str
    timestamp: float
    confidence: Optional[float] = None


class MeetingSessionCreate(BaseModel):
    """Create meeting session request"""
    title: Optional[str] = "Untitled Meeting"


class TranscriptUpdateRequest(BaseModel):
    """Update transcript request"""
    transcript: str


class MeetingSessionResponse(BaseModel):
    """Meeting session response"""
    id: str
    title: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    is_active: bool
    transcript: Optional[str] = None


class MeetingDetailsResponse(BaseModel):
    """Comprehensive meeting details response with all data"""
    id: str
    title: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    is_active: bool
    transcript: Optional[str] = None
    full_transcript: Optional[str] = None
    mom: Optional[Dict[str, Any]] = None
    faqs: Optional[List[Dict[str, Any]]] = None
    email_draft: Optional[Dict[str, Any]] = None
    risks: Optional[List[str]] = None


class TranscriptResponse(BaseModel):
    """Transcript response"""
    session_id: str
    segments: List[TranscriptSegment]
    full_text: str
    language: Optional[str] = None


class DecisionItem(BaseModel):
    """Decision item"""
    decision: str
    context: Optional[str] = None
    timestamp: Optional[float] = None


class ActionItem(BaseModel):
    """Action item with owner and deadline"""
    task: str
    owner: str
    deadline: Optional[str] = None
    priority: Optional[str] = "medium"
    context: Optional[str] = None


class MOMResponse(BaseModel):
    """Minutes of Meeting response"""
    session_id: str
    summary: str
    decisions: List[DecisionItem]
    action_items: List[ActionItem]
    key_points: List[str]
    attendees: List[str]
    duration: Optional[str] = None


class FAQItem(BaseModel):
    """FAQ item"""
    question: str
    answer: str
    context: Optional[str] = None


class EmailDraft(BaseModel):
    """Email draft"""
    to: List[str]
    subject: str
    body: str
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None


class AIProcessingRequest(BaseModel):
    """AI processing request"""
    session_id: str
    include_faqs: bool = True
    include_email_draft: bool = True


class AIProcessingResponse(BaseModel):
    """AI processing response"""
    mom: MOMResponse
    faqs: Optional[List[FAQItem]] = None
    email_draft: Optional[EmailDraft] = None
    risks: Optional[List[str]] = None


class EmailSummary(BaseModel):
    """Email summary"""
    total_emails: int
    unread: int
    urgent: int
    pending_approvals: int
    mailbox_summary: Optional[str] = None
    emails: List[Dict[str, Any]]


class TeamsSummary(BaseModel):
    """Teams summary"""
    total_messages: int
    unread: int
    urgent: int
    teams_summary: Optional[str] = None
    messages: List[Dict[str, Any]]
    error: Optional[str] = None
    error_type: Optional[str] = None  # "auth", "permission", "api", "empty"


class AutoReplySuggestion(BaseModel):
    """Auto-reply suggestion"""
    email_id: str
    suggested_reply: str
    confidence: float
    reasoning: Optional[str] = None


class RiskAlert(BaseModel):
    """Risk alert"""
    type: str
    message: str
    severity: str
    deadline: Optional[datetime] = None
    item_id: Optional[str] = None


class TodoItemCreate(BaseModel):
    """Create todo item request"""
    title: str
    description: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    source_data: Optional[Dict[str, Any]] = None


class TodoItemUpdate(BaseModel):
    """Update todo item request"""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    is_completed: Optional[bool] = None


class TodoItemResponse(BaseModel):
    """Todo item response"""
    id: int
    title: str
    description: Optional[str] = None
    priority: str
    order: Optional[float] = 0.0
    is_completed: bool
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    source_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class SearchResultItem(BaseModel):
    """Individual search result item"""
    type: str  # "meeting", "todo", "email", "teams"
    id: str
    title: str
    snippet: str
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Search response"""
    query: str
    total_results: int
    results: List[SearchResultItem]


class TokenInput(BaseModel):
    """Manual token input for Graph Explorer"""
    access_token: str


class MeetingInsights(BaseModel):
    """Meeting insights analysis"""
    sentiment: str
    sentiment_score: Optional[float] = None
    topics: List[str] = []
    engagement_score: Optional[float] = None
    key_insights: List[str] = []
    participant_engagement: Optional[Dict[str, Any]] = None
    meeting_effectiveness: Optional[str] = None
    recommendations: List[str] = []


class EmailCategorization(BaseModel):
    """Email categorization result"""
    category: str
    priority: str
    action_required: bool
    urgency: str
    estimated_response_time: Optional[str] = None
    suggested_tags: List[str] = []
    reasoning: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message for AI assistant"""
    query: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """AI chat assistant response"""
    answer: str
    confidence: float
    sources: List[str] = []
    follow_up_questions: List[str] = []
    action_items: List[str] = []


class TrendAnalysis(BaseModel):
    """Trend analysis across meetings"""
    trends: List[Dict[str, Any]] = []
    insights: List[str] = []
    recommendations: List[str] = []
    key_themes: List[str] = []
    action_item_trends: Optional[str] = None
    decision_patterns: Optional[str] = None


class SemanticSearchRequest(BaseModel):
    """Semantic search request"""
    query: str
    limit: Optional[int] = 10


class EmailSentimentAnalysis(BaseModel):
    """Email sentiment analysis result"""
    sentiment: str
    sentiment_score: Optional[float] = None
    urgency_detected: bool = False
    frustration_detected: bool = False
    tone: str
    emotional_markers: List[str] = []
    recommended_response_tone: Optional[str] = None


class EmailPriorityScore(BaseModel):
    """Email priority scoring result"""
    priority_score: int
    priority_level: str
    factors: List[str] = []
    reasoning: Optional[str] = None


class TeamsConversationSummary(BaseModel):
    """Teams conversation thread summary"""
    summary: str
    key_points: List[str] = []
    action_items: List[Dict[str, Any]] = []
    decisions: List[str] = []
    participants: List[str] = []
    topic: Optional[str] = None
    thread_id: Optional[str] = None


class ChannelActivityAnalysis(BaseModel):
    """Teams channel activity analysis"""
    active_discussions: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    activity_level: str
    top_contributors: List[str] = []
    key_topics: List[str] = []


class MentionAnalysis(BaseModel):
    """Teams @mention analysis"""
    mentions: List[Dict[str, Any]] = []
    unanswered_mentions: List[Dict[str, Any]] = []
    requires_response: List[Dict[str, Any]] = []


class CrossPlatformCorrelation(BaseModel):
    """Cross-platform correlation between emails and Teams"""
    correlations: List[Dict[str, Any]] = []
    related_items: List[Dict[str, Any]] = []


class DailyDigest(BaseModel):
    """Daily digest combining all communications"""
    summary: str
    highlights: List[str] = []
    action_items: List[Dict[str, Any]] = []
    urgent_items: List[str] = []
    dependencies: List[Dict[str, Any]] = []
    recommendations: List[str] = []


class DeadlineRiskPrediction(BaseModel):
    """Deadline risk prediction"""
    at_risk: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    recommendations: List[str] = []


class TeamsResponseSuggestion(BaseModel):
    """Teams response suggestion"""
    suggested_response: str
    tone: str
    confidence: float
    alternatives: List[str] = []


class JiraIssue(BaseModel):
    """Jira issue format"""
    title: str
    description: str
    issue_type: str
    priority: Optional[str] = None
    labels: List[str] = []
    components: List[str] = []
    acceptance_criteria: List[str] = []


class ConfluencePage(BaseModel):
    """Confluence page format"""
    title: str
    content: str
    page_type: str
    labels: List[str] = []
    sections: List[Dict[str, Any]] = []


class ToneOptimization(BaseModel):
    """Tone-optimized communication"""
    optimized_text: str
    tone: str
    changes: List[Dict[str, Any]] = []
    tone_score: Optional[float] = None
    recommendations: List[str] = []


class SmartNotification(BaseModel):
    """Smart notification item"""
    type: str
    item_id: str = ""
    priority: str = "high"
    reason: str = "Requires attention"
    action_required: bool = True
    urgency_score: Optional[float] = None
    item: Optional[Dict[str, Any]] = None


class SmartNotifications(BaseModel):
    """Smart notifications response"""
    notifications: List[SmartNotification] = []
    total: int = 0
    summary: str = "No notifications"






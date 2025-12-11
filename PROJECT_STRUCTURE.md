# Project Structure

```
hackathon/
├── backend/                          # FastAPI Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI application entry point
│   │   ├── database.py              # Database models and configuration
│   │   ├── api/                     # API routes
│   │   │   ├── __init__.py
│   │   │   ├── transcription.py    # Transcription endpoints
│   │   │   ├── ai_processing.py    # AI processing endpoints
│   │   │   ├── email.py            # Email integration endpoints
│   │   │   ├── teams.py            # Teams integration endpoints
│   │   │   └── export.py           # Export endpoints (PDF, DOCX, JSON)
│   │   ├── services/                # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── transcription_service.py  # Audio transcription logic
│   │   │   └── ai_service.py              # AI processing logic
│   │   ├── integrations/            # External API integrations
│   │   │   ├── __init__.py
│   │   │   ├── email_integration.py      # Outlook integration
│   │   │   └── teams_integration.py      # Microsoft Teams integration
│   │   └── models/                  # Data models
│   │       ├── __init__.py
│   │       └── schemas.py          # Pydantic schemas
│   ├── requirements.txt            # Python dependencies
│   └── Dockerfile                   # Backend Docker configuration
│
├── frontend/                        # React Frontend
│   ├── src/
│   │   ├── App.jsx                 # Main application component
│   │   ├── main.jsx                # React entry point
│   │   ├── index.css               # Global styles
│   │   ├── components/             # React components
│   │   │   ├── Dashboard.jsx       # Main dashboard
│   │   │   ├── TranscriptionView.jsx  # Transcription interface
│   │   │   ├── EmailView.jsx       # Email intelligence view
│   │   │   └── TeamsView.jsx       # Teams intelligence view
│   │   └── services/
│   │       └── api.js              # API client functions
│   ├── index.html                  # HTML template
│   ├── package.json                # Node.js dependencies
│   ├── vite.config.js              # Vite configuration
│   └── Dockerfile                  # Frontend Docker configuration
│
├── docker-compose.yml               # Docker Compose configuration
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
├── README.md                        # Main documentation
├── SETUP.md                         # Setup instructions
└── PROJECT_STRUCTURE.md             # This file
```

## Key Components

### Backend (`backend/app/`)

#### API Routes (`api/`)
- **transcription.py**: Handles meeting session creation, real-time transcription via WebSocket
- **ai_processing.py**: Processes transcripts to generate MOM, FAQs, email drafts, and risk detection
- **email.py**: Fetches and analyzes emails from Outlook
- **teams.py**: Fetches and analyzes Microsoft Teams messages
- **export.py**: Exports meeting data in PDF, DOCX, and JSON formats

#### Services (`services/`)
- **transcription_service.py**: 
  - Supports Whisper (local) and Deepgram (API) for transcription
  - Handles audio capture and real-time processing
- **ai_service.py**:
  - Uses OpenAI GPT models for summarization
  - Generates MOM, FAQs, email drafts
  - Detects risks and deadlines

#### Integrations (`integrations/`)
- **email_integration.py**: 
  - Microsoft Graph API for Outlook
  - Analyzes inbox for urgent items and approvals
- **teams_integration.py**:
  - Microsoft Graph API for Teams
  - Fetches chats and channel messages
  - Analyzes for urgency

### Frontend (`frontend/src/`)

#### Components
- **Dashboard.jsx**: Overview of all features, quick actions
- **TranscriptionView.jsx**: Real-time transcription interface with live transcript display
- **EmailView.jsx**: Email inbox with AI analysis and auto-reply suggestions
- **TeamsView.jsx**: Teams messages with urgency detection

#### Services
- **api.js**: Centralized API client with all endpoint functions

## Data Flow

1. **Transcription Flow**:
   - User starts session → Backend creates session → WebSocket connection → Audio capture → Transcription → Real-time updates

2. **AI Processing Flow**:
   - Transcript complete → AI service processes → Generates MOM, FAQs, email draft → Stores in database

3. **Email/Teams Flow**:
   - User requests inbox → Integration authenticates → Fetches messages → AI analyzes → Returns summary

## Database Schema

- **meeting_sessions**: Stores meeting sessions, transcripts, MOM, decisions, action items
- **email_cache**: Caches email data for quick access
- **teams_message_cache**: Caches Teams messages

## Environment Variables

See `.env.example` for all required configuration:
- API keys (OpenAI, Deepgram)
- OAuth credentials (Microsoft)
- Database configuration
- Privacy mode settings


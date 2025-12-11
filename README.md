# PayU Sensei - Meeting Assistant

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![React](https://img.shields.io/badge/React-18.2-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**An intelligent full-stack application that transforms your meetings and workday with AI-powered transcription, automatic MOM generation, and cognitive email/Teams assistance.**

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [API Reference](#-api-reference) • [Contributing](#-contributing)

</div>

---

## 🎯 Overview

PayU Sensei is a comprehensive AI-powered assistant designed to enhance productivity in modern work environments. It combines real-time meeting transcription, intelligent document generation, and proactive email/Teams management to help professionals stay organized and focused.

### Key Capabilities

- **🎤 Real-time Audio Transcription** - Capture and transcribe audio from any meeting platform (Zoom, Google Meet, Microsoft Teams)
- **📝 Automatic MOM Generation** - Generate structured minutes of meeting with decisions, action items, and key takeaways
- **🤖 AI-Powered Insights** - Get FAQs, follow-up email suggestions, and risk detection
- **📧 Email & Teams Integration** - Summarize inbox, detect urgent tasks, and suggest intelligent replies
- **📊 Live Dashboard** - Real-time view of transcript and AI-generated insights
- **🔒 Privacy Mode** - Option for local-only processing without cloud dependencies

---

## ✨ Features

### Meeting Intelligence
- **Multi-platform Support**: Works with Zoom, Google Meet, Microsoft Teams, and any audio source
- **Real-time Transcription**: Live transcription with speaker diarization
- **Smart MOM Generation**: Automatically extracts decisions, action items, and key points
- **Export Options**: Export transcripts and MOMs in multiple formats (PDF, DOCX, TXT)

### Email & Teams Assistant
- **Inbox Summarization**: Get AI-powered summaries of your email inbox
- **Urgency Detection**: Automatically identify and prioritize urgent emails
- **Smart Reply Suggestions**: Generate context-aware email responses
- **Teams Message Analysis**: Analyze and summarize Teams conversations

### AI Processing
- **Multiple Model Support**: GPT-4, GPT-o1, Llama 3, Claude (via AWS Bedrock), and more
- **Context-Aware Analysis**: Understands meeting context for better insights
- **Risk Detection**: Identifies potential issues or concerns in conversations
- **Follow-up Generation**: Creates actionable follow-up items
- **Flexible Provider Support**: Switch between OpenAI and AWS Bedrock

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite (with PostgreSQL support for production)
- **Transcription**: 
  - Local: OpenAI Whisper
  - Cloud: Deepgram API
- **AI Models**: OpenAI GPT-4 / GPT-o1, AWS Bedrock (Claude, Llama, Titan), Llama 3
- **Integrations**: Microsoft Graph API (Teams/Outlook)

### Frontend
- **Framework**: React 18
- **UI Library**: Material-UI (MUI)
- **Build Tool**: Vite
- **State Management**: React Hooks
- **Charts**: Recharts

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **API Documentation**: FastAPI Swagger/OpenAPI
- **Real-time Communication**: WebSockets

---

## 📁 Project Structure

```
hackathon/
├── backend/                    # FastAPI backend application
│   ├── app/
│   │   ├── api/               # API route handlers
│   │   │   ├── transcription.py
│   │   │   ├── ai_processing.py
│   │   │   ├── email.py
│   │   │   ├── teams.py
│   │   │   └── export.py
│   │   ├── services/          # Business logic services
│   │   │   ├── transcription_service.py
│   │   │   └── ai_service.py
│   │   ├── models/            # Data models and schemas
│   │   │   └── schemas.py
│   │   ├── integrations/      # Third-party integrations
│   │   │   ├── email_integration.py
│   │   │   └── teams_integration.py
│   │   ├── database.py         # Database configuration
│   │   └── main.py            # FastAPI application entry point
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Backend container configuration
│   ├── env.example           # Environment variables template
│   └── start.sh              # Startup script
│
├── frontend/                   # React frontend application
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── Home.jsx
│   │   │   ├── TranscriptionView.jsx
│   │   │   ├── EmailView.jsx
│   │   │   └── TeamsView.jsx
│   │   ├── services/          # API client services
│   │   │   └── api.js
│   │   ├── App.jsx           # Main application component
│   │   ├── main.jsx          # Application entry point
│   │   └── theme.js          # MUI theme configuration
│   ├── package.json          # Node.js dependencies
│   ├── Dockerfile           # Frontend container configuration
│   ├── vite.config.js       # Vite configuration
│   └── start.sh             # Startup script
│
├── docker-compose.yml        # Docker Compose configuration
├── .env.example             # Environment variables template
├── README.md               # This file
├── QUICKSTART.md           # Quick start guide
├── SETUP.md                # Detailed setup instructions
├── PROJECT_STRUCTURE.md    # Project structure documentation
├── AUDIO_SETUP.md          # Audio capture setup guide
└── AWS_BEDROCK_SETUP.md    # AWS Bedrock integration guide
```

---

## 🚀 Quick Start

### Prerequisites

- **Python** 3.9 or higher
- **Node.js** 16 or higher
- **Docker** and Docker Compose (optional, for containerized deployment)
- **FFmpeg** (for audio processing)

### Option 1: Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/ShubhGar/PayU-Sensei.git
cd PayU-Sensei

# 2. Create environment file
cp .env.example .env

# 3. Add your API keys to .env
# OPENAI_API_KEY=sk-your-key-here
# DEEPGRAM_API_KEY=your-deepgram-key (optional)

# 4. Start services
docker-compose up --build

# 5. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp env.example .env
# Edit .env with your API keys

# Start server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

> 📖 For detailed setup instructions, see [SETUP.md](SETUP.md)  
> ⚡ For a quick 5-minute setup, see [QUICKSTART.md](QUICKSTART.md)

---

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure the following:

#### Required
- `OPENAI_API_KEY` - Your OpenAI API key for AI processing (MOM generation, email summarization, etc.)

#### Optional
- `DEEPGRAM_API_KEY` - Deepgram API key for cloud transcription (defaults to local Whisper)
- `USE_DEEPGRAM` - Set to `"true"` to use Deepgram instead of local Whisper
- `LOCAL_WHISPER_MODEL` - Whisper model size: `base`, `small`, `medium`, `large` (default: `base`)
- `OPENAI_MODEL` - OpenAI model to use (default: `gpt-4o`)
- `OPENAI_FALLBACK_MODEL` - Fallback OpenAI model if primary model is unavailable (default: `gpt-3.5-turbo`)

#### AWS Bedrock (Alternative to OpenAI)
- `USE_BEDROCK` - Set to `"true"` to use AWS Bedrock instead of OpenAI
- `AWS_REGION` - AWS region for Bedrock (e.g., `us-east-1`)
- `AWS_ACCESS_KEY_ID` - AWS access key ID
- `AWS_SECRET_ACCESS_KEY` - AWS secret access key
- `BEDROCK_MODEL_ID` - Bedrock model ID (e.g., `anthropic.claude-3-sonnet-20240229-v1:0`)

> 📖 For detailed AWS Bedrock setup, see [AWS_BEDROCK_SETUP.md](AWS_BEDROCK_SETUP.md)

#### Microsoft Integration
- `MICROSOFT_CLIENT_ID` - Azure App Registration Client ID
- `MICROSOFT_CLIENT_SECRET` - Azure App Registration Client Secret
- `MICROSOFT_TENANT_ID` - Azure Tenant ID

#### CORS Configuration
- `ALLOWED_ORIGINS` - Comma-separated list of allowed origins (default: `http://localhost:3000,http://localhost:5173`)

### Audio Capture Setup

For system audio capture (meeting transcription):

**macOS:**
```bash
brew install blackhole-2ch
# Configure Audio MIDI Setup to route system audio through BlackHole
```

**Windows:**
- Use WASAPI loopback device (PyAudio should detect automatically)

**Linux:**
- Use PulseAudio or ALSA loopback device

> 📖 For detailed audio setup, see [AUDIO_SETUP.md](AUDIO_SETUP.md)  
> 🤖 For AWS Bedrock integration, see [AWS_BEDROCK_SETUP.md](AWS_BEDROCK_SETUP.md)

---

## 📚 API Reference

### Core Endpoints

#### Transcription
- `POST /api/transcribe/start` - Start a new transcription session
- `POST /api/transcribe/stop` - Stop an active transcription session
- `GET /api/transcript/{session_id}` - Get transcript for a session
- `WebSocket /ws/transcribe/{session_id}` - Real-time transcription stream

#### AI Processing
- `POST /api/ai/summarize` - Generate MOM and insights from transcript
- `POST /api/ai/faqs` - Generate FAQs from transcript
- `POST /api/ai/followup` - Generate follow-up items

#### Email Integration
- `GET /api/email/inbox` - Get email inbox summary
- `POST /api/email/analyze` - Analyze specific email
- `POST /api/email/suggest-reply` - Generate reply suggestions

#### Teams Integration
- `GET /api/teams/messages` - Get Teams messages
- `POST /api/teams/analyze` - Analyze Teams conversation

#### Export
- `POST /api/export/{format}` - Export transcript/MOM (formats: `pdf`, `docx`, `txt`)

### Interactive API Documentation

Once the backend is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 🧪 Testing

### Health Check

```bash
curl http://localhost:8000/health
```

### Start Transcription Session

```bash
curl -X POST http://localhost:8000/api/transcribe/start \
  -H "Content-Type: application/json" \
  -d '{"title": "Team Standup Meeting"}'
```

### Generate MOM

```bash
curl -X POST http://localhost:8000/api/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-session-id"}'
```

---

## 🐛 Troubleshooting

### Backend Issues

**Server won't start?**
- Check Python version: `python --version` (need 3.9+)
- Verify port 8000 is available
- Check `.env` file exists and contains required keys
- Review backend logs for error messages

**Transcription not working?**
- Verify audio capture setup (see [AUDIO_SETUP.md](AUDIO_SETUP.md))
- Check microphone/system audio permissions
- For macOS: Ensure BlackHole is installed and configured
- Try using Deepgram API instead of local Whisper
- Check FFmpeg installation: `ffmpeg -version`

**AI processing errors?**
- Verify OpenAI API key is correct and has credits
- Check API quota/rate limits
- Review backend logs for detailed error messages

### Frontend Issues

**Frontend won't start?**
- Check Node version: `node --version` (need 16+)
- Delete `node_modules` and run `npm install` again
- Check if port 3000 is available
- Clear browser cache and try again

**API connection errors?**
- Verify backend is running on port 8000
- Check CORS configuration in `.env`
- Verify `VITE_API_URL` in frontend environment

### Database Issues

- Database file (`meetings.db`) is created automatically
- Check file permissions in project directory
- Delete `meetings.db` to reset database

---

## 🚢 Deployment

### Production Considerations

1. **Database**: Use PostgreSQL instead of SQLite
2. **Environment**: Set `PRIVACY_MODE=true` for local-only processing
3. **Security**: 
   - Use HTTPS
   - Set up proper OAuth redirect URIs
   - Use environment-specific `.env` files
4. **Monitoring**: Set up logging and monitoring
5. **Scaling**: Consider using a reverse proxy (nginx) and load balancer

### Docker Production

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Run with production settings
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- OpenAI for Whisper and GPT models
- Deepgram for transcription API
- FastAPI for the excellent web framework
- Material-UI for the beautiful component library
- All contributors and users of this project

---

## 📞 Support

For issues, questions, or contributions:
- Open an issue on [GitHub](https://github.com/ShubhGar/PayU-Sensei/issues)
- Check the [Documentation](https://github.com/ShubhGar/PayU-Sensei/wiki)

---

<div align="center">

**Made with ❤️ by the PayU Sensei Team**

[⭐ Star us on GitHub](https://github.com/ShubhGar/PayU-Sensei) • [🐛 Report Bug](https://github.com/ShubhGar/PayU-Sensei/issues) • [💡 Request Feature](https://github.com/ShubhGar/PayU-Sensei/issues)

</div>

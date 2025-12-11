# Quick Start Guide

Get the Meeting Assistant running in 5 minutes!

## Option 1: Docker (Recommended)

```bash
# 1. Clone/navigate to project
cd hackathon

# 2. Create .env file (copy from .env.example)
cp .env.example .env

# 3. Add your OpenAI API key to .env
# OPENAI_API_KEY=sk-your-key-here

# 4. Start services
docker-compose up --build

# 5. Open browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Option 2: Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file with OPENAI_API_KEY
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# Start server
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## First Steps

1. **Test the API**: Visit `http://localhost:8000/docs` to see the interactive API documentation

2. **Start a Meeting Session**:
   - Go to http://localhost:3000/transcription
   - Enter a meeting title
   - Click "Start Recording"
   - (Note: Audio capture requires microphone/system audio setup)

3. **Generate MOM**:
   - After recording, click "Generate Insights"
   - View MOM, FAQs, and email draft

4. **Test Email Integration**:
   - Go to http://localhost:3000/email
   - Authenticate with your email provider
   - View inbox summary and AI analysis

## Minimal Configuration

For basic testing, you only need:
- `OPENAI_API_KEY` - For AI processing (MOM, FAQs, etc.)

Optional but recommended:
- `DEEPGRAM_API_KEY` - For better transcription (or use local Whisper)
- `MICROSOFT_CLIENT_ID` / `MICROSOFT_CLIENT_SECRET` - For Teams/Outlook

## Troubleshooting

**Backend won't start?**
- Check Python version: `python --version` (need 3.9+)
- Check if port 8000 is available
- Verify `.env` file exists

**Frontend won't start?**
- Check Node version: `node --version` (need 16+)
- Delete `node_modules` and run `npm install` again
- Check if port 3000 is available

**Transcription not working?**
- Audio capture requires PyAudio and system audio setup
- For macOS: Install BlackHole for system audio
- Check microphone permissions
- Try using Deepgram API instead of local Whisper

**AI processing errors?**
- Verify OpenAI API key is correct
- Check API quota/credits
- Review backend logs for error messages

## Next Steps

- Read [SETUP.md](SETUP.md) for detailed configuration
- Read [README.md](README.md) for full feature documentation
- Check [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) to understand the codebase

## API Testing

Use the interactive docs at `http://localhost:8000/docs` or test with curl:

```bash
# Health check
curl http://localhost:8000/health

# Start transcription session
curl -X POST http://localhost:8000/api/transcribe/start \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Meeting"}'
```




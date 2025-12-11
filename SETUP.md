# Setup Instructions

## Prerequisites

- Python 3.9 or higher
- Node.js 16 or higher
- Docker and Docker Compose (optional, for containerized deployment)

## Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp ../.env.example .env
# Edit .env with your API keys
```

5. Run the backend server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Docker Setup

1. Copy the environment file:
```bash
cp .env.example .env
# Edit .env with your API keys
```

2. Build and run with Docker Compose:
```bash
docker-compose up --build
```

This will start both backend and frontend services.

## API Keys Configuration

### OpenAI API Key
1. Sign up at https://platform.openai.com
2. Create an API key
3. Add to `.env`: `OPENAI_API_KEY=your_key_here`

### Deepgram API Key (Optional)
1. Sign up at https://deepgram.com
2. Create an API key
3. Add to `.env`: `DEEPGRAM_API_KEY=your_key_here`
4. Set `USE_DEEPGRAM=true` to use Deepgram instead of local Whisper

### Microsoft Graph API (Teams & Outlook)
1. Go to https://portal.azure.com
2. Register a new application
3. Add API permissions: Mail.Read, Chat.Read, ChannelMessage.Read.All
4. Create a client secret
5. Add to `.env`:
   - `MICROSOFT_CLIENT_ID=your_client_id`
   - `MICROSOFT_CLIENT_SECRET=your_client_secret`
   - `MICROSOFT_TENANT_ID=your_tenant_id`


## Audio Capture Setup

### macOS
1. Install BlackHole for system audio capture:
```bash
brew install blackhole-2ch
```

2. Configure Audio MIDI Setup to route system audio through BlackHole

### Windows
- Use WASAPI loopback device
- PyAudio should detect it automatically

### Linux
- Use PulseAudio or ALSA
- Configure loopback device

## Testing

### Test Backend API
```bash
curl http://localhost:8000/health
```

### Test Transcription
1. Start a meeting session via API
2. Connect WebSocket for real-time transcription
3. Speak into microphone or play audio

### Test Email Integration
1. Authenticate with email provider
2. Fetch inbox via `/api/email/inbox`
3. Test auto-reply suggestions

## Troubleshooting

### Audio Capture Issues
- Ensure microphone permissions are granted
- Check audio device configuration
- Verify PyAudio installation: `python -c "import pyaudio; print(pyaudio.__version__)"`

### Transcription Issues
- Check API keys in `.env`
- Verify Whisper model download (first run may take time)
- Check network connection for Deepgram API

### Database Issues
- Database file is created automatically
- Check file permissions in project directory
- Delete `meetings.db` to reset

### CORS Issues
- Ensure `ALLOWED_ORIGINS` in `.env` includes frontend URL
- Check backend logs for CORS errors

## Development Notes

- Backend uses async/await for non-blocking operations
- Frontend uses React with Material-UI components
- WebSocket connection for real-time transcription
- SQLite database for lightweight persistence
- All AI processing is async to avoid blocking

## Production Deployment

1. Set `PRIVACY_MODE=true` for local-only processing
2. Use PostgreSQL instead of SQLite for production
3. Set up proper OAuth redirect URIs
4. Configure HTTPS
5. Set up proper logging and monitoring
6. Use environment-specific `.env` files




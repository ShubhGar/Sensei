# Audio Capture Test Guide

This guide helps you test if the app can capture audio from your microphone.

## Prerequisites

1. **Backend server running** on port 8000
2. **Frontend server running** on port 3000 (or 5173 for Vite)
3. **Microphone access** - Make sure your browser has permission to access the microphone

## Testing Steps

### 1. Start the Application

If not already running:
```bash
# Backend (from backend directory)
./start.sh

# Frontend (from frontend directory)  
npm run dev
```

### 2. Test Audio Capture

1. Open your browser and navigate to `http://localhost:3000` (or the port your frontend is running on)
2. Navigate to the "Transcription" view/tab
3. Enter a meeting title (optional)
4. Click "Start Recording"
5. **Grant microphone permission** when prompted by the browser
6. **Speak into your microphone** for a few seconds
7. You should see:
   - The transcript appearing in real-time in the "Live Transcript" section
   - Audio being captured (check browser console for any errors)

### 3. Verify Audio Capture

**Check Browser Console:**
- Open Developer Tools (F12)
- Look for:
  - "WebSocket connected" message when recording starts
  - Any errors related to microphone access
  - WebSocket messages being sent/received

**Check Backend Logs:**
- Look for:
  - WebSocket connection messages
  - Transcription service initialization
  - Any errors during transcription

### 4. Expected Behavior

✅ **Success Indicators:**
- Microphone permission prompt appears
- "WebSocket connected" in console
- Transcript text appears as you speak
- No errors in console or backend logs

❌ **Common Issues:**
- **No microphone prompt**: Check browser permissions in settings
- **WebSocket connection error**: Verify backend is running on port 8000
- **No transcript appearing**: 
  - Check if transcription service (Deepgram/Whisper) is configured
  - Verify API keys are set in `.env` file
  - Check backend logs for transcription errors

### 5. Test Different Scenarios

- **Short phrases**: Say "Hello, this is a test"
- **Longer speech**: Speak for 10-20 seconds
- **Stop and restart**: Stop recording, then start again
- **Multiple sessions**: Create multiple recording sessions

## Troubleshooting

### Microphone Not Working
1. Check browser permissions: Settings → Privacy → Microphone
2. Try a different browser (Chrome, Firefox, Safari)
3. Check system microphone settings

### WebSocket Connection Issues
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check CORS settings in backend
3. Verify WebSocket URL matches your backend URL

### No Transcription
1. Check `.env` file has transcription service configured:
   - `USE_DEEPGRAM=true` and `DEEPGRAM_API_KEY` set, OR
   - `USE_DEEPGRAM=false` and Whisper model installed
2. Check backend logs for transcription errors
3. Verify audio format is being sent correctly (WebM/Opus)

## Manual API Test

You can also test the API directly:

```bash
# Start a session
curl -X POST http://localhost:8000/api/transcribe/start \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Session"}'

# This will return a session_id, use it in the WebSocket connection
```


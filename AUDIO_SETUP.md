# Audio Setup Guide

This guide helps you set up audio capture for the transcription service.

## PyAudio Installation

PyAudio is now installed and ready to use! It was installed with the following steps:

1. **Install PortAudio** (prerequisite on macOS):
   ```bash
   brew install portaudio
   ```

2. **Install PyAudio**:
   ```bash
   cd backend
   source venv/bin/activate
   pip install pyaudio
   ```

PyAudio is now included in `requirements.txt` and will be installed automatically when you run `pip install -r requirements.txt`.

## System Audio Capture Setup (macOS)

To capture system audio (e.g., from Zoom, Teams, or other applications), you need to set up a virtual audio device on macOS using **BlackHole**.

### Step 1: Install BlackHole

```bash
brew install blackhole-2ch
```

Or download from: https://github.com/ExistentialAudio/BlackHole

### Step 2: Configure Audio Routing

1. Open **Audio MIDI Setup** (Applications → Utilities → Audio MIDI Setup)
2. Click the **+** button at the bottom left and select **Create Multi-Output Device**
3. Check both:
   - Your speakers/headphones (e.g., "MacBook Pro Speakers")
   - **BlackHole 2ch**
4. Right-click on the Multi-Output Device and select **Use This Device For Sound Output**
5. In Audio MIDI Setup, select **BlackHole 2ch** and set it as the input device for your application

### Step 3: Configure System Audio Input

1. Go to **System Settings** → **Sound**
2. Set **Output** to your Multi-Output Device (created above)
3. This routes system audio to both your speakers AND BlackHole

### Step 4: Test Audio Capture

1. Start the backend server:
   ```bash
   cd backend
   ./start.sh
   ```

2. In the frontend, select **"System Audio"** as the audio source
3. Play some audio (e.g., a YouTube video or meeting)
4. The transcription should capture the system audio

## Troubleshooting

### PyAudio Installation Issues

**On macOS:**
- Make sure PortAudio is installed: `brew install portaudio`
- If installation fails, try: `pip install --global-option="build_ext" --global-option="-I/opt/homebrew/include" --global-option="-L/opt/homebrew/lib" pyaudio`

**On Linux:**
- Install PortAudio: `sudo apt-get install portaudio19-dev` (Ubuntu/Debian) or `sudo yum install portaudio-devel` (CentOS/RHEL)

**On Windows:**
- PyAudio should work with pre-built wheels. If not, install Visual C++ Build Tools.

### System Audio Not Capturing

1. **Verify BlackHole is installed:**
   ```bash
   brew list blackhole-2ch
   ```

2. **Check Audio MIDI Setup:**
   - Make sure Multi-Output Device includes BlackHole
   - Verify BlackHole is selected as an input device

3. **Test PyAudio directly:**
   ```python
   import pyaudio
   p = pyaudio.PyAudio()
   print("Available input devices:")
   for i in range(p.get_device_count()):
       info = p.get_device_info_by_index(i)
       if info['maxInputChannels'] > 0:
           print(f"  {i}: {info['name']}")
   p.terminate()
   ```

4. **Check system permissions:**
   - macOS may require microphone permissions even for system audio
   - Go to System Settings → Privacy & Security → Microphone
   - Ensure your terminal/IDE has microphone access

### Microphone Capture Issues

If using **"User Microphone"** instead of system audio:

1. **Browser permissions:**
   - Make sure your browser has microphone access
   - Check browser settings → Privacy → Microphone

2. **Test microphone:**
   - Try recording in another application first
   - Check System Settings → Sound → Input

## Alternative: Use Deepgram for Transcription

If you're having issues with local audio capture, you can use Deepgram API instead:

1. Set `USE_DEEPGRAM=true` in your `.env` file
2. Add your `DEEPGRAM_API_KEY`
3. The app will use Deepgram for transcription, which works with browser microphone capture

## Verification

To verify everything is working:

```bash
cd backend
source venv/bin/activate
python -c "import pyaudio; print(f'PyAudio {pyaudio.__version__} is installed!')"
```

You should see: `PyAudio 0.2.14 is installed!`





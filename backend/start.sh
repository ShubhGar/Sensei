#!/bin/bash

# Backend Startup Script
# This script automates the process of creating a virtual environment, installing dependencies, and starting the backend server

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Backend Development Server${NC}"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3 first.${NC}"
    echo "You can install it using: brew install python@3.14"
    exit 1
fi

echo -e "${GREEN}✓ Python version: $(python3 --version)${NC}"

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip and install build tools
echo -e "${YELLOW}📦 Upgrading pip and installing build tools...${NC}"
pip install --upgrade pip --quiet
pip install setuptools wheel --quiet

# Install dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"

# Install core packages first (without strict version pinning for Python 3.14 compatibility)
pip install fastapi "uvicorn[standard]" python-multipart pydantic pydantic-settings openai deepgram-sdk python-dotenv httpx aiohttp msal google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-docx reportlab websockets pydub asyncio-mqtt --quiet

# Install database dependencies
pip install sqlalchemy aiosqlite greenlet --quiet

# Install numpy with compatible version for Python 3.14
pip install "numpy>=1.26.0" --quiet

echo -e "${GREEN}✓ Dependencies installed successfully${NC}"

# Note about optional packages
echo -e "${YELLOW}ℹ️  Note: whisper is not installed due to Python 3.14 compatibility.${NC}"
echo -e "${YELLOW}   The app will use Deepgram for transcription instead.${NC}"
echo -e "${GREEN}✓ PyAudio is available for system audio capture${NC}"
echo ""

# Start the development server
echo -e "${GREEN}🎯 Starting FastAPI development server on http://localhost:8000${NC}"
echo -e "${GREEN}📚 API Documentation available at http://localhost:8000/docs${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload




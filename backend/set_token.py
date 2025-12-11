#!/usr/bin/env python3
"""
Helper script to set Microsoft Graph API access token
Usage: python set_token.py <access_token>
"""
import sys
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

async def set_token(token):
    """Set the Microsoft access token via API"""
    if not token or not token.strip():
        print("Error: Token cannot be empty")
        return False
    
    token = token.strip()
    
    # Validate token format
    if len(token) < 100:
        print("Warning: Token seems too short. Make sure you copied the entire token.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return False
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/auth/microsoft/token",
                json={"access_token": token},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✓ Token set successfully!")
                print(f"  Status: {result.get('status')}")
                print(f"  Expires at: {result.get('expires_at')}")
                print(f"  Message: {result.get('message')}")
                return True
            else:
                error_data = response.json()
                error_msg = error_data.get("detail", "Unknown error")
                print(f"✗ Failed to set token: {error_msg}")
                return False
    except httpx.ConnectError:
        print(f"✗ Error: Could not connect to API at {API_BASE_URL}")
        print("  Make sure the backend server is running")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_token.py <access_token>")
        print()
        print("Example:")
        print("  python set_token.py 'EwB4BMl6BAAUu4TQbLz/EdYigQnDPtIo76ZZUKsAA...'")
        print()
        print("To get a token with Teams permissions:")
        print("  1. Go to https://developer.microsoft.com/en-us/graph/graph-explorer")
        print("  2. Sign in and click 'Modify permissions' (gear icon)")
        print("  3. Add: Chat.Read, Chat.ReadWrite, ChannelMessage.Read.All")
        print("  4. Consent to permissions")
        print("  5. Get a new access token")
        print("  6. Run this script with the new token")
        sys.exit(1)
    
    token = sys.argv[1]
    success = asyncio.run(set_token(token))
    sys.exit(0 if success else 1)


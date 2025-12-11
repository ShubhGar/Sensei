#!/usr/bin/env python3
"""
Step-by-step guide to fix Teams permissions issue
This script will help you get a token with proper Teams permissions
"""
import asyncio
import httpx
import webbrowser
import sys

print("=" * 80)
print("Teams Permissions Fix - Step by Step Guide")
print("=" * 80)
print()
print("ISSUE DETECTED: Your token is valid but missing Teams permissions.")
print("Even if you've added permissions in Graph Explorer, you need to:")
print("  1. Make sure you CONSENTED to the permissions")
print("  2. Get a NEW token AFTER consenting (old tokens won't work)")
print()
print("=" * 80)
print("STEP-BY-STEP SOLUTION")
print("=" * 80)
print()
print("Step 1: Open Microsoft Graph Explorer")
print("  → Opening browser to: https://developer.microsoft.com/en-us/graph/graph-explorer")
print()
input("Press Enter to open Graph Explorer in your browser...")
webbrowser.open("https://developer.microsoft.com/en-us/graph/graph-explorer")

print()
print("Step 2: In Graph Explorer, do the following:")
print("  a) Make sure you're signed in with your Microsoft account")
print("  b) Click the 'Modify permissions' button (gear icon in top right)")
print("  c) In the search box, search for and select:")
print("     - Chat.Read")
print("     - Chat.ReadWrite")
print("     - ChannelMessage.Read.All")
print("     - Team.ReadBasic.All")
print("  d) IMPORTANT: Click 'Consent' button to grant permissions")
print("     → You'll see a consent screen - click 'Accept'")
print("  e) After consenting, close the permissions panel")
print()
input("Press Enter after you've consented to the permissions...")

print()
print("Step 3: Get a NEW access token")
print("  a) In Graph Explorer, try making a request to: GET /me/chats")
print("     → This will generate a new token with the consented permissions")
print("  b) Click on the 'Access token' tab (or check request headers)")
print("  c) Copy the ENTIRE access token (it's very long!)")
print()
print("Step 4: Test the new token")
print("  → We'll test it to make sure it has Teams permissions")
print()

token = input("Paste your NEW access token here (or press Enter to skip testing): ").strip()

if token:
    print()
    print("Testing your new token...")
    print("-" * 80)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    async def test_token():
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test user profile
            try:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers=headers
                )
                if response.status_code == 200:
                    user_data = response.json()
                    print(f"✓ User profile: {user_data.get('displayName', 'N/A')}")
                else:
                    print(f"✗ User profile failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"✗ Error: {e}")
                return False
            
            # Test Teams chats
            try:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me/chats",
                    headers=headers,
                    params={"$top": 5}
                )
                if response.status_code == 200:
                    chats_data = response.json()
                    chats = chats_data.get("value", [])
                    print(f"✓ Teams chats: Found {len(chats)} chats")
                    return True
                elif response.status_code == 403:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown")
                    print(f"✗ Teams chats: Still getting 403 - {error_msg}")
                    print(f"  → The token still doesn't have Chat.Read permissions")
                    print(f"  → Make sure you CONSENTED (not just added) the permissions")
                    return False
                else:
                    print(f"✗ Teams chats: Unexpected status {response.status_code}")
                    return False
            except Exception as e:
                print(f"✗ Error: {e}")
                return False
    
    success = asyncio.run(test_token())
    
    if success:
        print()
        print("=" * 80)
        print("✓ SUCCESS! Your token has Teams permissions!")
        print("=" * 80)
        print()
        print("Now set this token in your application:")
        print()
        print("Option 1: Using the helper script")
        print(f"  python set_token.py \"{token[:50]}...\"")
        print()
        print("Option 2: Using curl")
        print(f"  curl -X POST http://localhost:8000/api/auth/microsoft/token \\")
        print(f"    -H 'Content-Type: application/json' \\")
        print(f"    -d '{{\"access_token\": \"{token[:50]}...\"}}'")
        print()
        print("Option 3: Using the frontend UI")
        print("  → Go to http://localhost:3000")
        print("  → Navigate to Teams view")
        print("  → Click 'Enter Token Manually'")
        print("  → Paste the token and click 'Set Token'")
        print()
    else:
        print()
        print("=" * 80)
        print("✗ Token still doesn't have Teams permissions")
        print("=" * 80)
        print()
        print("Common issues:")
        print("  1. You added permissions but didn't CONSENT to them")
        print("     → Solution: Go back to Graph Explorer and click 'Consent'")
        print()
        print("  2. You're using an old token from before consenting")
        print("     → Solution: Get a NEW token after consenting")
        print()
        print("  3. Permissions require admin consent (for work/school accounts)")
        print("     → Solution: Contact your IT admin to grant permissions")
        print()
        print("  4. Your account doesn't have Teams access")
        print("     → Solution: Make sure you have a Teams license")
        print()
else:
    print()
    print("Skipping token test.")
    print()
    print("To set your token manually, use:")
    print("  python set_token.py <your_token>")
    print()

print("=" * 80)


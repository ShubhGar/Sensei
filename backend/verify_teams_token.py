#!/usr/bin/env python3
"""
Quick script to verify if a token has Teams permissions
Usage: python verify_teams_token.py [token]
If no token provided, will check the one in the database
"""
import asyncio
import sys
import httpx
from app.database import AsyncSessionLocal, MicrosoftAuth
from sqlalchemy import select


async def verify_token(token=None):
    """Verify if a token has Teams permissions"""
    if not token:
        # Get token from database
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MicrosoftAuth).where(MicrosoftAuth.user_id == "default")
            )
            auth_record = result.scalar_one_or_none()
            if not auth_record or not auth_record.access_token:
                print("❌ No token found in database")
                print("   Provide a token as argument or set one first")
                return False
            token = auth_record.access_token.strip()
            print("Using token from database...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n" + "=" * 60)
    print("Verifying Teams Permissions")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: User profile (should always work)
        print("\n1. Testing user profile...", end=" ")
        try:
            response = await client.get("https://graph.microsoft.com/v1.0/me", headers=headers)
            if response.status_code == 200:
                print("✓")
            else:
                print(f"✗ ({response.status_code})")
                print("   Token is invalid or expired")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
        
        # Test 2: Teams chats
        print("2. Testing Teams chats...", end=" ")
        try:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/chats",
                headers=headers,
                params={"$top": 1}
            )
            if response.status_code == 200:
                print("✓ Has Chat.Read permission")
                return True
            elif response.status_code == 403:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "")
                print(f"✗ Missing Chat.Read permission")
                print(f"   Error: {error_msg}")
                return False
            else:
                print(f"✗ Unexpected status: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False


async def main():
    token = sys.argv[1] if len(sys.argv) > 1 else None
    
    if token:
        print(f"Testing provided token (length: {len(token)})...")
    else:
        print("No token provided, checking database...")
    
    has_permissions = await verify_token(token)
    
    print("\n" + "=" * 60)
    if has_permissions:
        print("✓ Token has Teams permissions!")
        print("=" * 60)
    else:
        print("✗ Token is missing Teams permissions")
        print("=" * 60)
        print("\nTo fix:")
        print("1. Go to https://developer.microsoft.com/en-us/graph/graph-explorer")
        print("2. Click 'Modify permissions' and CONSENT to:")
        print("   - Chat.Read")
        print("   - Chat.ReadWrite")
        print("   - ChannelMessage.Read.All")
        print("3. Get a NEW token after consenting")
        print("4. Set it: python set_token.py <new_token>")


if __name__ == "__main__":
    asyncio.run(main())


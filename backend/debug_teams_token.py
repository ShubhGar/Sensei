#!/usr/bin/env python3
"""
Debug script to check Microsoft Teams token in database
"""
import asyncio
import sys
import os
import base64
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal, MicrosoftAuth
from sqlalchemy import select


async def check_token():
    """Check the token stored in the database"""
    print("=" * 80)
    print("Microsoft Teams Token Diagnostic")
    print("=" * 80)
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MicrosoftAuth).where(MicrosoftAuth.user_id == "default")
            )
            auth_record = result.scalar_one_or_none()
            
            if not auth_record:
                print("\n❌ No Microsoft auth record found in database")
                print("   You need to authenticate first using the OAuth flow.")
                return
            
            print(f"\n✓ Found auth record (ID: {auth_record.id})")
            print(f"  User ID: {auth_record.user_id}")
            print(f"  Token Type: {auth_record.token_type}")
            print(f"  Created At: {auth_record.created_at}")
            print(f"  Updated At: {auth_record.updated_at}")
            
            # Check access token
            if not auth_record.access_token:
                print("\n❌ Access token is None")
                return
            
            token = auth_record.access_token.strip()
            token_length = len(token)
            
            print(f"\n📝 Access Token Info:")
            print(f"  Length: {token_length} characters")
            print(f"  First 50 chars: {token[:50]}...")
            print(f"  Last 50 chars: ...{token[-50:]}")
            
            # Check if token looks like a JWT (should have 3 parts separated by dots)
            parts = token.split('.')
            if len(parts) == 3:
                print(f"\n✓ Token appears to be a JWT (has 3 parts)")
                try:
                    # Decode JWT header (first part)
                    header_padded = parts[0] + '=' * (4 - len(parts[0]) % 4)
                    header_json = base64.urlsafe_b64decode(header_padded)
                    header = json.loads(header_json)
                    print(f"  Header: {json.dumps(header, indent=2)}")
                    
                    # Decode JWT payload (second part)
                    payload_padded = parts[1] + '=' * (4 - len(parts[1]) % 4)
                    payload_json = base64.urlsafe_b64decode(payload_padded)
                    payload = json.loads(payload_json)
                    print(f"  Payload (decoded):")
                    print(f"    - Issuer: {payload.get('iss', 'N/A')}")
                    print(f"    - Audience: {payload.get('aud', 'N/A')}")
                    print(f"    - Expires: {datetime.fromtimestamp(payload.get('exp', 0)) if payload.get('exp') else 'N/A'}")
                    print(f"    - Scopes: {payload.get('scp', payload.get('roles', 'N/A'))}")
                except Exception as e:
                    print(f"  ⚠️  Could not decode JWT parts: {e}")
            else:
                print(f"\n⚠️  Token does not appear to be a JWT (expected 3 parts, got {len(parts)})")
                print(f"   This might indicate the token is corrupted or in an unexpected format")
            
            # Check expiration
            if auth_record.expires_at:
                is_expired = auth_record.expires_at < datetime.utcnow()
                print(f"\n⏰ Expiration:")
                print(f"  Expires At: {auth_record.expires_at}")
                print(f"  Is Expired: {'Yes ❌' if is_expired else 'No ✓'}")
                if is_expired:
                    print(f"  ⚠️  Token has expired! You need to refresh or re-authenticate.")
            else:
                print(f"\n⏰ Expiration: Not set")
            
            # Check refresh token
            if auth_record.refresh_token:
                refresh_length = len(auth_record.refresh_token)
                print(f"\n🔄 Refresh Token:")
                print(f"  Length: {refresh_length} characters")
                print(f"  Present: Yes ✓")
            else:
                print(f"\n🔄 Refresh Token: Not present ❌")
                print(f"  ⚠️  Without a refresh token, you cannot automatically refresh expired tokens")
            
            # Test token with Microsoft Graph API
            print(f"\n🧪 Testing token with Microsoft Graph API...")
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    # Test with /me endpoint
                    response = await client.get(
                        "https://graph.microsoft.com/v1.0/me",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=5.0
                    )
                    
                    print(f"  Status Code: {response.status_code}")
                    
                    if response.status_code == 200:
                        user_data = response.json()
                        print(f"  ✓ Token is valid!")
                        print(f"  User: {user_data.get('displayName', 'N/A')} ({user_data.get('mail', user_data.get('userPrincipalName', 'N/A'))})")
                    elif response.status_code == 401:
                        print(f"  ❌ Token is invalid or expired (401 Unauthorized)")
                        error_data = response.json() if response.text else {}
                        print(f"  Error: {error_data.get('error', {}).get('message', response.text)}")
                    elif response.status_code == 403:
                        print(f"  ⚠️  Token is valid but lacks permissions (403 Forbidden)")
                        error_data = response.json() if response.text else {}
                        print(f"  Error: {error_data.get('error', {}).get('message', response.text)}")
                    else:
                        print(f"  ⚠️  Unexpected status code: {response.status_code}")
                        print(f"  Response: {response.text[:200]}")
            except Exception as e:
                print(f"  ❌ Error testing token: {e}")
            
            # Test with Teams chats endpoint
            print(f"\n🧪 Testing token with Teams Chats API...")
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://graph.microsoft.com/v1.0/me/chats",
                        headers={"Authorization": f"Bearer {token}"},
                        params={"$top": 1},
                        timeout=5.0
                    )
                    
                    print(f"  Status Code: {response.status_code}")
                    
                    if response.status_code == 200:
                        print(f"  ✓ Token works with Teams Chats API!")
                        data = response.json()
                        print(f"  Chats found: {len(data.get('value', []))}")
                    elif response.status_code == 401:
                        print(f"  ❌ Token is invalid or expired (401 Unauthorized)")
                        error_data = response.json() if response.text else {}
                        print(f"  Error: {error_data.get('error', {}).get('message', response.text)}")
                    elif response.status_code == 403:
                        print(f"  ⚠️  Token is valid but lacks Chat.Read permissions (403 Forbidden)")
                        error_data = response.json() if response.text else {}
                        error_code = error_data.get('error', {}).get('code', '')
                        error_message = error_data.get('error', {}).get('message', '')
                        print(f"  Error Code: {error_code}")
                        print(f"  Error Message: {error_message}")
                        if 'Chat.Read' in error_message or 'Chat.ReadBasic' in error_message:
                            print(f"\n  💡 Solution: Re-authenticate with Chat.Read or Chat.ReadWrite scopes")
                    else:
                        print(f"  ⚠️  Unexpected status code: {response.status_code}")
                        print(f"  Response: {response.text[:200]}")
            except Exception as e:
                print(f"  ❌ Error testing Teams API: {e}")
            
    except Exception as e:
        print(f"\n❌ Error checking token: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_token())


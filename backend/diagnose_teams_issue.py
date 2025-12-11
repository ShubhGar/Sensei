#!/usr/bin/env python3
"""
Comprehensive diagnostic script to identify Teams token issues
"""
import asyncio
import sys
import os
import base64
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from app.database import AsyncSessionLocal, MicrosoftAuth
from sqlalchemy import select


def decode_jwt_payload(token):
    """Decode JWT payload to see token claims"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        # Decode the payload (second part)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - (len(payload) % 4)
        if padding != 4:
            payload += '=' * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        return None


async def check_database_token():
    """Check token stored in database"""
    print("=" * 80)
    print("Step 1: Checking Token in Database")
    print("=" * 80)
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MicrosoftAuth).where(MicrosoftAuth.user_id == "default")
            )
            auth_record = result.scalar_one_or_none()
            
            if not auth_record:
                print("\n❌ No Microsoft auth record found in database")
                print("   → You need to set a token first")
                return None
            
            if not auth_record.access_token:
                print("\n❌ Access token is None or empty in database")
                return None
            
            token = auth_record.access_token.strip()
            print(f"\n✓ Found token in database")
            print(f"  Token length: {len(token)} characters")
            print(f"  Token type: {auth_record.token_type}")
            print(f"  Expires at: {auth_record.expires_at}")
            
            # Check if expired
            if auth_record.expires_at and auth_record.expires_at < datetime.utcnow():
                print(f"  ⚠️  TOKEN IS EXPIRED!")
                return token
            
            # Try to decode JWT
            token_info = decode_jwt_payload(token)
            if token_info:
                print(f"\n  Token Details (decoded):")
                print(f"    User: {token_info.get('upn', token_info.get('unique_name', 'N/A'))}")
                
                # Check expiration
                exp = token_info.get('exp')
                if exp:
                    exp_time = datetime.fromtimestamp(exp)
                    now = datetime.now()
                    if exp_time < now:
                        print(f"    ⚠️  EXPIRED! Expired at: {exp_time}")
                    else:
                        print(f"    ✓ Expires at: {exp_time} (in {(exp_time - now).total_seconds() / 60:.1f} minutes)")
                
                # Check scopes
                scopes = token_info.get('scp', token_info.get('roles', []))
                if isinstance(scopes, str):
                    scopes = scopes.split()
                
                print(f"    Scopes: {', '.join(scopes) if scopes else 'NONE FOUND'}")
                
                # Check for Teams scopes
                teams_scopes = [s for s in scopes if any(x in s for x in ['Chat', 'Channel', 'Team'])]
                if teams_scopes:
                    print(f"    ✓ Teams scopes found: {', '.join(teams_scopes)}")
                else:
                    print(f"    ❌ NO Teams scopes found!")
                    print(f"    → Required: Chat.Read, Chat.ReadWrite, or ChannelMessage.Read.All")
            else:
                print(f"  ⚠️  Token is not a standard JWT (may be OAuth 2.0 format)")
                print(f"  → Cannot decode to check scopes directly")
            
            return token
            
    except Exception as e:
        print(f"\n❌ Error checking database: {e}")
        return None


async def test_token_with_api(token):
    """Test the token with Microsoft Graph API"""
    print("\n" + "=" * 80)
    print("Step 2: Testing Token with Microsoft Graph API")
    print("=" * 80)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    results = {}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: User profile
        print("\n1. Testing /me endpoint...")
        try:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers
            )
            if response.status_code == 200:
                user_data = response.json()
                print(f"   ✓ Success! User: {user_data.get('displayName', 'N/A')} ({user_data.get('mail', user_data.get('userPrincipalName', 'N/A'))})")
                results['user'] = True
            else:
                print(f"   ❌ Failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('error', {}).get('message', 'Unknown')}")
                except:
                    print(f"   Response: {response.text[:200]}")
                results['user'] = False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results['user'] = False
        
        # Test 2: Teams chats
        print("\n2. Testing /me/chats endpoint...")
        try:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/chats",
                headers=headers,
                params={"$top": 10}
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                chats_data = response.json()
                chats = chats_data.get("value", [])
                print(f"   ✓ Success! Found {len(chats)} chats")
                results['chats'] = True
            elif response.status_code == 403:
                error_data = response.json()
                error_code = error_data.get("error", {}).get("code", "Unknown")
                error_msg = error_data.get("error", {}).get("message", "Unknown")
                print(f"   ❌ Permission Denied (403)")
                print(f"   Error Code: {error_code}")
                print(f"   Error Message: {error_msg}")
                
                # Check for specific error messages
                if "authorization" in error_msg.lower() or "No authorization" in error_msg:
                    print(f"   → This usually means missing Chat.Read permissions")
                elif "consent" in error_msg.lower():
                    print(f"   → This usually means permissions need admin consent")
                elif "insufficient" in error_msg.lower():
                    print(f"   → This usually means the token doesn't have the required scopes")
                
                results['chats'] = False
            elif response.status_code == 401:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown")
                print(f"   ❌ Unauthorized (401) - Token expired or invalid")
                print(f"   Error: {error_msg}")
                results['chats'] = False
            else:
                print(f"   ❌ Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                results['chats'] = False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results['chats'] = False
        
        # Test 3: Joined Teams
        print("\n3. Testing /me/joinedTeams endpoint...")
        try:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/joinedTeams",
                headers=headers,
                params={"$top": 10}
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                teams_data = response.json()
                teams = teams_data.get("value", [])
                print(f"   ✓ Success! Found {len(teams)} Teams")
                results['teams'] = True
            elif response.status_code == 403:
                error_data = response.json()
                error_code = error_data.get("error", {}).get("code", "Unknown")
                error_msg = error_data.get("error", {}).get("message", "Unknown")
                print(f"   ❌ Permission Denied (403)")
                print(f"   Error: {error_msg}")
                results['teams'] = False
            else:
                print(f"   ❌ Status: {response.status_code}")
                results['teams'] = False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results['teams'] = False
    
    return results


async def check_application_endpoint():
    """Check if the application endpoint works"""
    print("\n" + "=" * 80)
    print("Step 3: Testing Application Endpoint")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "http://localhost:8000/api/teams/messages?max_results=5",
                params={"force_refresh": "true"}
            )
            print(f"\nStatus: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                is_dummy = data.get("is_dummy_data", False)
                error = data.get("error")
                
                if is_dummy:
                    print(f"   ⚠️  Using dummy data (no real Teams messages)")
                    if error:
                        print(f"   Error: {error}")
                else:
                    print(f"   ✓ Success! Retrieved {len(messages)} real Teams messages")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
    except httpx.ConnectError:
        print(f"   ⚠️  Could not connect to application (is it running?)")
    except Exception as e:
        print(f"   ❌ Error: {e}")


async def main():
    """Run all diagnostics"""
    print("\n" + "=" * 80)
    print("Microsoft Teams Token Diagnostic Tool")
    print("=" * 80)
    
    # Step 1: Check database token
    token = await check_database_token()
    
    if not token:
        print("\n" + "=" * 80)
        print("CONCLUSION: No token found in database")
        print("=" * 80)
        print("\nSolution: Set a token using one of these methods:")
        print("  1. python set_token.py <token>")
        print("  2. POST /api/auth/microsoft/token")
        print("  3. Frontend UI")
        return
    
    # Step 2: Test token with API
    results = await test_token_with_api(token)
    
    # Step 3: Test application endpoint
    await check_application_endpoint()
    
    # Summary
    print("\n" + "=" * 80)
    print("DIAGNOSIS SUMMARY")
    print("=" * 80)
    
    if not results.get('user'):
        print("\n❌ Token is invalid or expired")
        print("   → Get a new token from Graph Explorer")
    elif not results.get('chats') and not results.get('teams'):
        print("\n❌ Token is valid but missing Teams permissions")
        print("\n   Solutions:")
        print("   1. Go to https://developer.microsoft.com/en-us/graph/graph-explorer")
        print("   2. Click 'Modify permissions' (gear icon)")
        print("   3. Add and CONSENT to:")
        print("      - Chat.Read")
        print("      - Chat.ReadWrite")
        print("      - ChannelMessage.Read.All")
        print("      - Team.ReadBasic.All")
        print("   4. IMPORTANT: After consenting, get a NEW token")
        print("   5. Set the new token using: python set_token.py <new_token>")
        print("\n   Note: Just adding permissions is not enough - you must:")
        print("   - Click 'Consent' to grant them")
        print("   - Get a NEW token after consenting (old token won't work)")
    elif results.get('chats') or results.get('teams'):
        print("\n✓ Token appears to be working!")
        print("   If you're still having issues, check:")
        print("   - Backend logs for detailed errors")
        print("   - Whether you have any Teams chats/channels")
        print("   - Application endpoint configuration")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())


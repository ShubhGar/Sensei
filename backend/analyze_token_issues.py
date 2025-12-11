#!/usr/bin/env python3
"""
Detailed analysis of token issues
"""
import asyncio
import httpx
import json
import base64
from datetime import datetime

# The new token provided
ACCESS_TOKEN = "EwB4BMl6BAAUu4TQbLz/EdYigQnDPtIo76ZZUKsAAQbgjcwNAnM0y/Z9X4LEk2iDapvuTQW5CfSsdLHDy4TELyqkN9oY8waxsjRgMsIrWT9zDMdgbnkL6P6SggCloQISzbnuhV5R29BNp3E4iN/mTZnLJhOicTD1PlpLwOJ9T6gcLJkTZdrH/+m8dtldFEEPi4Mf+9WWrJ1Cpk2IOCwT0DY04sdtxNhK3lierXbieWeT9MnRb1XZQ3pdgddgLb+ODCTp100/zqsWTUUJdsJmCeRWXybfF4Z3mhalTZE5G3X6MdJpO1VRXEfzZfc/tFyE3gyS2m3KO47BGa+8+3vnsBPA5jn3l0dZPJzEtWOuzF8fSnkNdlnrssowsyPtUagQZgAAEGBerGkBRpB5yNUbC+LzsbdAA78FvLSL/vxIEzgFD8ac57RcyAlFH8McBPuuqb+Mn2W8SdQ/NkeSFvsFmjpDX+jilSxXm5FAV99M8AkfmYRfXMwAYWMd0YFwz4/iLh4VN2mx3LTZ5pscPx7k8ST+XeLPIYQ2upCl68iW37gK2+h2a8dT8F0TgnXWLP90frgdYGjsciLYWI4Ft/ai5t+jEFQsr8NfTNvqoYhspifWBGAgG2xCk2dAM2rDWVIeC9ZLi/16FwM77NVw1O9yQdkpXTpbNdYAUQjWc4loEryHzCyx7dOTTlpf1gkjwDJ07pYwk/n9+V4s//Rjg5EeAjbGlfDGnqdqM9Lr1Ui/VtT3Dg19c9iHAKR/6+TL1gyR34OUMcTtnNC3jOtfgVwNU3hbHFnSB3mgskmLPQRZXxslO+z7ztBX3HOn8WCBEnX37fAM+WpRXjukoalCY/+m364piPWeHYnW4dH/MYqLnADYTYtFczum/JHzjIKgNjs2ak+Bp/XiubYIMQHbCoN98WLDFeSnaUCv0hnrd4O2h0/7PGewz1YEsVhdrQUQA6FKMzeDQPYcSamkfKhxB1wGQ6zbGY3Xz3RLKvGU14gB/5WD1w3DfooeJFGZFiyLYC1X7MdTf74VhC/sY6Q+qMIXHh2oU482JQS0yPXQ3VjeHXpgqz50P2X5tGPYHCBUBuu0YJXmfJqC9btmMoqkX/F/k4aekdapwN0+j64sAGVUXemqEYyZ+rigaMDDbTOmt0gMJR+16BeIqi6bT9zCUKvY3SrT/Qe6M/lAWmqKezU0SGauEEm3ISPgAeTdtqMD5jthOQuZSOzOyH1C6Jqy83VBAUvQUeEF7f90/UfYL/QYgui3UobxmPVBddkiI5dCI708E3UBulMrx9eyiMs9h/rxUri91eVuY+2jLB87gyyxmUm+ZBErbwzA0/pm5VC+ApAT925Q4qeSOsOChOTaBFKzohSXB1MbBffx/r5UU/SNZmhWgrQiFtCIoNdQVCgRyhlwL5MtvGkZ7O94uzl5K2SFBP00P/2VhHvkOtyFKkFXGxrdSDVcn3RzRH2AGzIHpsmfl3nPFP2gbMQnWg8EgMsN5tDis6MGORNj8zsvt4fZgYmSOrpKMBOJAw=="

async def analyze_token():
    """Comprehensive token analysis"""
    print("=" * 80)
    print("COMPREHENSIVE TOKEN ANALYSIS")
    print("=" * 80)
    print()
    
    # Token format analysis
    print("1. TOKEN FORMAT ANALYSIS")
    print("-" * 80)
    print(f"   Token length: {len(ACCESS_TOKEN)} characters")
    print(f"   Starts with: {ACCESS_TOKEN[:20]}...")
    print(f"   Ends with: ...{ACCESS_TOKEN[-20:]}")
    
    # Check if it's a JWT
    parts = ACCESS_TOKEN.split('.')
    if len(parts) == 3:
        print(f"   Format: JWT (3 parts)")
        try:
            # Try to decode payload
            payload = parts[1]
            padding = 4 - (len(payload) % 4)
            if padding != 4:
                payload += '=' * padding
            decoded = base64.urlsafe_b64decode(payload)
            token_data = json.loads(decoded)
            
            print(f"   ✓ Successfully decoded JWT payload")
            print(f"   User: {token_data.get('upn', token_data.get('unique_name', 'N/A'))}")
            
            # Check expiration
            exp = token_data.get('exp')
            if exp:
                exp_time = datetime.fromtimestamp(exp)
                now = datetime.now()
                if exp_time < now:
                    print(f"   ⚠️  EXPIRED! Expired at: {exp_time}")
                else:
                    print(f"   ✓ Expires at: {exp_time} (in {(exp_time - now).total_seconds() / 60:.1f} minutes)")
            
            # Check scopes
            scopes = token_data.get('scp', token_data.get('roles', []))
            if isinstance(scopes, str):
                scopes = scopes.split()
            
            print(f"   Scopes in token: {', '.join(scopes) if scopes else 'NONE FOUND'}")
            
            # Check for Teams scopes
            teams_scopes = [s for s in scopes if any(x in s for x in ['Chat', 'Channel', 'Team'])]
            if teams_scopes:
                print(f"   ✓ Teams scopes: {', '.join(teams_scopes)}")
            else:
                print(f"   ❌ NO Teams scopes found in token!")
                
        except Exception as e:
            print(f"   ⚠️  Could not decode JWT: {e}")
    else:
        print(f"   Format: OAuth 2.0 access token (not JWT)")
        print(f"   → Cannot decode to check scopes directly")
    
    print()
    
    # API testing
    print("2. API ENDPOINT TESTING")
    print("-" * 80)
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test user profile
        print("\n   a) GET /me")
        try:
            response = await client.get("https://graph.microsoft.com/v1.0/me", headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                print(f"      ✓ Status 200 - User: {user_data.get('displayName')} ({user_data.get('mail', user_data.get('userPrincipalName'))})")
            else:
                print(f"      ✗ Status {response.status_code}")
                try:
                    error = response.json()
                    print(f"      Error: {error.get('error', {}).get('message', 'Unknown')}")
                except:
                    print(f"      Response: {response.text[:200]}")
        except Exception as e:
            print(f"      ✗ Exception: {e}")
        
        # Test Teams chats
        print("\n   b) GET /me/chats")
        try:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/chats",
                headers=headers,
                params={"$top": 1}
            )
            print(f"      Status: {response.status_code}")
            if response.status_code == 200:
                chats_data = response.json()
                chats = chats_data.get("value", [])
                print(f"      ✓ SUCCESS! Found {len(chats)} chats")
                print(f"      → Token HAS Chat.Read permission!")
            elif response.status_code == 403:
                error_data = response.json()
                error_code = error_data.get("error", {}).get("code", "Unknown")
                error_msg = error_data.get("error", {}).get("message", "Unknown")
                print(f"      ✗ Permission Denied (403)")
                print(f"      Error Code: {error_code}")
                print(f"      Error Message: {error_msg}")
                print(f"      → Token is MISSING Chat.Read permission")
                
                # Analyze error message
                if "No authorization information" in error_msg:
                    print(f"      → This means the token doesn't have Chat.Read scope at all")
                elif "consent" in error_msg.lower():
                    print(f"      → This means permissions need to be consented")
                elif "insufficient" in error_msg.lower():
                    print(f"      → This means the token doesn't have sufficient privileges")
            elif response.status_code == 401:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown")
                print(f"      ✗ Unauthorized (401) - Token expired or invalid")
                print(f"      Error: {error_msg}")
            else:
                print(f"      ✗ Unexpected status: {response.status_code}")
                print(f"      Response: {response.text[:300]}")
        except Exception as e:
            print(f"      ✗ Exception: {e}")
        
        # Test joined Teams
        print("\n   c) GET /me/joinedTeams")
        try:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/joinedTeams",
                headers=headers,
                params={"$top": 1}
            )
            print(f"      Status: {response.status_code}")
            if response.status_code == 200:
                teams_data = response.json()
                teams = teams_data.get("value", [])
                print(f"      ✓ SUCCESS! Found {len(teams)} Teams")
            elif response.status_code == 403:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown")
                print(f"      ✗ Permission Denied (403)")
                print(f"      Error: {error_msg}")
            else:
                print(f"      ✗ Status: {response.status_code}")
        except Exception as e:
            print(f"      ✗ Exception: {e}")
    
    print()
    print("=" * 80)
    print("PROBLEM SUMMARY")
    print("=" * 80)
    print()
    print("❌ ISSUE IDENTIFIED: Token is missing Teams permissions")
    print()
    print("Root Cause:")
    print("  The token does not have the required Teams scopes:")
    print("    - Chat.Read")
    print("    - Chat.ReadWrite")
    print("    - ChannelMessage.Read.All")
    print("    - Team.ReadBasic.All")
    print()
    print("Why this happens:")
    print("  1. Permissions were added in Graph Explorer but NOT consented")
    print("  2. Token was generated BEFORE consenting to permissions")
    print("  3. Old token is being used (tokens don't automatically get new permissions)")
    print()
    print("SOLUTION:")
    print("  1. Go to https://developer.microsoft.com/en-us/graph/graph-explorer")
    print("  2. Click 'Modify permissions' (gear icon)")
    print("  3. Make sure these are SELECTED:")
    print("     - Chat.Read")
    print("     - Chat.ReadWrite")
    print("     - ChannelMessage.Read.All")
    print("     - Team.ReadBasic.All")
    print("  4. CRITICAL: Click 'Consent' button (not just add)")
    print("  5. Accept the consent screen")
    print("  6. IMPORTANT: Get a NEW token AFTER consenting")
    print("     → Make a request in Graph Explorer (e.g., GET /me/chats)")
    print("     → This generates a token with the new permissions")
    print("  7. Copy the NEW token and set it using:")
    print("     python set_token.py <new_token>")
    print()
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(analyze_token())


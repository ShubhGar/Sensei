#!/usr/bin/env python3
"""
Helper script to verify token format and provide guidance
"""
import sys

def check_token_format(token):
    """Check if token is in valid JWT format"""
    token = token.strip()
    
    # Check for dots (JWT format)
    dots = token.count('.')
    
    print("=" * 80)
    print("Token Format Check")
    print("=" * 80)
    print(f"Token length: {len(token)} characters")
    print(f"Number of dots (.): {dots}")
    print(f"Starts with: {token[:20]}...")
    print(f"Ends with: ...{token[-20:]}")
    print()
    
    if dots == 0:
        print("❌ INVALID FORMAT: Token has no dots - not a valid JWT")
        print()
        print("A valid Microsoft Graph API access token should:")
        print("  - Have exactly 2 dots (.) separating 3 parts")
        print("  - Look like: eyJ...header...payload...signature")
        print("  - Be a long string (typically 1000-2000+ characters)")
        print()
        print("How to get the correct token from Graph Explorer:")
        print("  1. Go to https://developer.microsoft.com/en-us/graph/graph-explorer")
        print("  2. Sign in with your Microsoft account")
        print("  3. Click on 'Access token' tab (or look in the request headers)")
        print("  4. The token should start with 'eyJ' and contain dots")
        print("  5. Copy the ENTIRE token (it's very long)")
        print()
        print("Common issues:")
        print("  - Token might be truncated (too short)")
        print("  - Token might be URL-encoded (shouldn't be)")
        print("  - You might have copied something else (like a session ID)")
        return False
    elif dots == 2:
        print("✓ Token format looks valid (has 2 dots)")
        parts = token.split('.')
        print(f"  Part 1 (header) length: {len(parts[0])}")
        print(f"  Part 2 (payload) length: {len(parts[1])}")
        print(f"  Part 3 (signature) length: {len(parts[2])}")
        return True
    else:
        print(f"⚠ UNUSUAL FORMAT: Token has {dots} dots (expected 2)")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_token_format.py <token>")
        print()
        print("Example:")
        print('  python verify_token_format.py "eyJ0eXAiOiJKV1QiLCJhbGc..."')
        sys.exit(1)
    
    token = sys.argv[1]
    is_valid = check_token_format(token)
    
    if not is_valid:
        sys.exit(1)


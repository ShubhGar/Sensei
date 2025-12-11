# Teams Messages Not Fetching - Solution Guide

## Problem Diagnosis

Your Microsoft Graph API access token is **valid** but **missing Teams permissions**. 

### Test Results:
- ✅ **User Profile**: Works (token is valid)
- ❌ **Teams Chats**: 403 Forbidden - "No authorization information present on the request"
- ❌ **Joined Teams**: 403 Forbidden - Missing permissions

### Root Cause:
The token doesn't have the required Teams scopes:
- `Chat.Read` or `Chat.ReadWrite` (for Teams chats)
- `ChannelMessage.Read.All` (for Teams channel messages)
- `Team.ReadBasic.All` (for joined Teams)

## Solution: Get a New Token with Teams Permissions

### Step 1: Get Token from Graph Explorer

1. Go to **[Microsoft Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)**
2. Sign in with your Microsoft account (91garg.shubham@gmail.com)
3. Click the **"Modify permissions"** button (gear icon in the top right)
4. In the permissions panel, search for and select:
   - ✅ `Chat.Read`
   - ✅ `Chat.ReadWrite`
   - ✅ `ChannelMessage.Read.All`
   - ✅ `Team.ReadBasic.All`
   - ✅ `Mail.Read` (if you also need email)
   - ✅ `Mail.ReadWrite` (if you also need email)
5. Click **"Consent"** to grant permissions
6. After consenting, the token will refresh automatically
7. Click on **"Access token"** tab or look in the request headers
8. Copy the **entire access token** (it's very long, typically 1000-2000+ characters)

### Step 2: Set the Token

You have three options to set the new token:

#### Option A: Using the Helper Script (Recommended)
```bash
cd backend
python set_token.py "YOUR_NEW_TOKEN_HERE"
```

#### Option B: Using the API Endpoint Directly
```bash
curl -X POST http://localhost:8000/api/auth/microsoft/token \
  -H "Content-Type: application/json" \
  -d '{"access_token": "YOUR_NEW_TOKEN_HERE"}'
```

#### Option C: Using the Frontend
1. Go to `http://localhost:3000`
2. Navigate to Teams or Email view
3. Click "Enter Token Manually" or "Use Graph Explorer Token"
4. Paste the new token
5. Click "Set Token"

### Step 3: Verify It Works

Test the Teams endpoint:
```bash
curl http://localhost:8000/api/teams/messages?max_results=10
```

You should now see Teams messages instead of dummy data!

## Important Notes

1. **Token Expiration**: Graph Explorer tokens expire after ~1 hour. When they expire:
   - Go back to Graph Explorer
   - Get a new token (it refreshes automatically)
   - Set it again using one of the methods above

2. **Admin Consent**: Some permissions (like `ChannelMessage.Read.All`) may require admin consent for work/school accounts. If you see consent errors, contact your IT admin.

3. **Token Format**: The token should:
   - Start with `eyJ` (standard JWT format)
   - Contain exactly 2 dots (`.`) separating 3 parts
   - Be very long (1000-2000+ characters)
   - Not be URL-encoded

## Troubleshooting

### Still Getting 403 Errors?
- Make sure you **consented** to the permissions in Graph Explorer
- Verify the token includes Teams scopes (you can test with `test_user_token.py`)
- Try getting a fresh token after consenting

### Token Expired?
- Tokens from Graph Explorer expire after ~1 hour
- Get a new token from Graph Explorer
- Set it again using one of the methods above

### Still Not Working?
1. Check backend logs for detailed error messages
2. Run the diagnostic script: `python test_user_token.py`
3. Verify your Microsoft account has Teams access
4. Make sure you're using a personal Microsoft account or have proper Teams licenses

## Quick Reference

**Required Scopes for Teams:**
- `Chat.Read` - Read Teams chats
- `Chat.ReadWrite` - Read and write Teams chats  
- `ChannelMessage.Read.All` - Read Teams channel messages
- `Team.ReadBasic.All` - List joined Teams

**API Endpoints:**
- Set token: `POST /api/auth/microsoft/token`
- Check status: `GET /api/auth/microsoft/status`
- Get Teams messages: `GET /api/teams/messages`


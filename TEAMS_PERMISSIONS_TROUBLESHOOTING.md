# Teams Permissions Troubleshooting Guide

## Current Status

✅ **Token is valid** - Can access user profile (`/me`)  
❌ **Token missing Teams permissions** - Getting 403 on `/me/chats` and `/me/joinedTeams`  
⚠️ **Application returning dummy data** - This confirms the token doesn't have Teams permissions

## The Problem

Even though you've **added** permissions in Graph Explorer, your token still doesn't have Teams permissions. This usually means:

1. **You added permissions but didn't CONSENT to them** (most common)
2. **You're using an old token** from before you consented
3. **Permissions require admin consent** (for work/school accounts)
4. **Token format issue** - Your token is OAuth 2.0 format (not JWT), which is fine, but you need a fresh one after consenting

## Solution: Step-by-Step Fix

### Step 1: Verify Permissions Are Actually Consented

1. Go to **[Microsoft Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)**
2. Make sure you're signed in
3. Click **"Modify permissions"** (gear icon)
4. Check if these permissions show as **"Consented"** (not just selected):
   - `Chat.Read`
   - `Chat.ReadWrite`
   - `ChannelMessage.Read.All`
   - `Team.ReadBasic.All`

**If they're NOT consented:**
- Select them
- Click **"Consent"** button
- You'll see a consent screen - click **"Accept"**
- Wait for the consent to complete

### Step 2: Get a NEW Token (Critical!)

**IMPORTANT:** After consenting, you MUST get a NEW token. Old tokens won't work even if you've consented to new permissions.

**Method 1: Make a request in Graph Explorer**
1. In Graph Explorer, try: `GET https://graph.microsoft.com/v1.0/me/chats`
2. This will generate a new token with the consented permissions
3. Click on **"Access token"** tab
4. Copy the entire token

**Method 2: Use the token from request headers**
1. Open browser DevTools (F12)
2. Go to Network tab
3. Make a request in Graph Explorer
4. Find the request, check Headers
5. Look for `Authorization: Bearer <token>`
6. Copy the token

### Step 3: Test the New Token

Run the diagnostic to verify:
```bash
cd backend
python3 diagnose_teams_issue.py
```

Or test manually:
```bash
# Update test_user_token.py with your new token, then:
python3 test_user_token.py
```

### Step 4: Set the New Token

Once you have a token that works:

**Option A: Using helper script**
```bash
python set_token.py "YOUR_NEW_TOKEN_HERE"
```

**Option B: Using API**
```bash
curl -X POST http://localhost:8000/api/auth/microsoft/token \
  -H "Content-Type: application/json" \
  -d '{"access_token": "YOUR_NEW_TOKEN_HERE"}'
```

**Option C: Using frontend**
1. Go to `http://localhost:3000`
2. Navigate to Teams view
3. Click "Enter Token Manually"
4. Paste token and click "Set Token"

### Step 5: Verify It Works

```bash
curl http://localhost:8000/api/teams/messages?max_results=5&force_refresh=true
```

You should see real Teams messages (not dummy data with "dummy-chat-1" IDs).

## Common Issues & Solutions

### Issue 1: "I added permissions but still getting 403"

**Solution:**
- Adding permissions is not enough - you must **CONSENT** to them
- After consenting, get a **NEW token** (old tokens won't work)
- The token must be generated AFTER you consented

### Issue 2: "I consented but token still doesn't work"

**Possible causes:**
1. **Using old token** - Get a fresh token after consenting
2. **Admin consent required** - Some permissions need admin approval for work/school accounts
3. **Account doesn't have Teams** - Verify your account has Teams access/license

**Solution:**
- Make sure you got the token AFTER consenting
- Try making a request in Graph Explorer first (this generates a new token)
- Check if you see an admin consent required message

### Issue 3: "Token works in Graph Explorer but not in my app"

**Possible causes:**
1. **Token format issue** - Make sure you copied the entire token
2. **Token expired** - Tokens expire after ~1 hour
3. **App using cached token** - Clear cache or restart app

**Solution:**
- Verify token is set correctly: `python3 diagnose_teams_issue.py`
- Check if token is expired
- Try setting token again with `force_refresh=true`

### Issue 4: "Admin consent required"

If you see "Admin consent required" or similar messages:

**For personal accounts:**
- This shouldn't happen - try consenting again

**For work/school accounts:**
- Contact your IT admin
- They need to grant permissions in Azure AD
- Or use a personal Microsoft account for testing

## Verification Checklist

Before reporting issues, verify:

- [ ] Permissions are **consented** (not just added) in Graph Explorer
- [ ] You got a **NEW token** after consenting
- [ ] Token is not expired (check with `diagnose_teams_issue.py`)
- [ ] Token works in Graph Explorer directly (`GET /me/chats`)
- [ ] Token is set in your application database
- [ ] Application is using the correct token (check logs)

## Quick Diagnostic Commands

```bash
# Check token in database and test it
cd backend
python3 diagnose_teams_issue.py

# Test a specific token
python3 test_user_token.py

# Set a new token
python3 set_token.py "YOUR_TOKEN"

# Check application endpoint
curl http://localhost:8000/api/teams/messages?max_results=5
```

## Still Having Issues?

1. **Check backend logs** for detailed error messages
2. **Run diagnostics**: `python3 diagnose_teams_issue.py`
3. **Test token directly**: `python3 test_user_token.py`
4. **Verify in Graph Explorer**: Try `GET /me/chats` - does it work there?
5. **Check account**: Does your account actually have Teams access?

## Key Takeaways

1. **Adding permissions ≠ Consenting** - You must click "Consent"
2. **Old tokens don't get new permissions** - Get a NEW token after consenting
3. **Token format doesn't matter** - OAuth 2.0 tokens work fine, just need proper scopes
4. **Test in Graph Explorer first** - If it works there, it should work in your app


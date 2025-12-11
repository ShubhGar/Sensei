# Microsoft Authentication Setup Guide (Using Graph Explorer)

This guide will help you set up Microsoft authentication for Outlook and Teams integration using **Microsoft Graph Explorer** (no Azure app registration required).

## Prerequisites

- A Microsoft account (personal or work/school account)
- Access to [Microsoft Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)

## Method: Using Graph Explorer (Recommended for Development)

Graph Explorer is a web-based tool that allows you to test Microsoft Graph API calls and obtain access tokens without needing to register an application in Azure.

### Step 1: Get Access Token from Graph Explorer

1. Go to [Microsoft Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)
2. Click **"Sign in to Graph Explorer"** in the top right corner
3. Sign in with your Microsoft account (personal or work/school)
4. After signing in, you'll see your profile information on the left side
5. Click on **"Access token"** tab (or look for the token in the request headers)
6. Copy the access token - it will look like a long string starting with `eyJ...`

**Note**: The token from Graph Explorer is valid for about 1 hour. You'll need to refresh it periodically.

### Step 2: Set the Token in Your Application

You have two options to set the token:

#### Option A: Using the API Endpoint (Recommended)

1. Start your backend server:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. Use curl or any HTTP client to set the token:
   ```bash
   curl -X POST http://localhost:8000/api/auth/microsoft/token \
     -H "Content-Type: application/json" \
     -d '{"access_token": "YOUR_TOKEN_FROM_GRAPH_EXPLORER"}'
   ```

   Or use the frontend UI (see Option B below).

#### Option B: Using the Frontend UI

1. Start your frontend server:
   ```bash
   cd frontend
   npm run dev
   ```

2. Navigate to `http://localhost:3000`
3. Click on **"Login with Microsoft"** or go to Email/Teams view
4. You'll see an option to **"Enter Token Manually"** or **"Use Graph Explorer Token"**
5. Paste the token from Graph Explorer and click **"Set Token"**

### Step 3: Verify Authentication

1. After setting the token, check the authentication status:
   ```bash
   curl http://localhost:8000/api/auth/microsoft/status
   ```

2. You should see:
   ```json
   {
     "authenticated": true,
     "provider": "microsoft"
   }
   ```

3. Try accessing your emails or Teams messages - they should now work!

### Step 4: Token Refresh

**Important**: Tokens from Graph Explorer expire after about 1 hour. When they expire:

1. Go back to [Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)
2. Make sure you're still signed in
3. Get a new access token (it refreshes automatically when you make a request)
4. Set the new token using the same method as Step 2

### Required Permissions

When using Graph Explorer, make sure you have the following permissions granted:

**For Email:**
- `Mail.Read` - to read emails
- `Mail.ReadWrite` - to read and write emails

**For Teams:**
- `Chat.Read` - to read Teams chats (1-on-1 and group chats)
- `Chat.ReadWrite` - to read and write Teams chats
- `ChannelMessage.Read.All` - to read Teams channel messages (requires admin consent for organization accounts)

**General:**
- `User.Read` - to read user profile

**Important Notes:**
- Graph Explorer will prompt you to consent to these permissions when you first try to access them
- For Teams data, you may need to explicitly request Teams permissions in Graph Explorer:
  1. In Graph Explorer, click on "Modify permissions" (gear icon)
  2. Search for and select: `Chat.Read`, `Chat.ReadWrite`, and `ChannelMessage.Read.All`
  3. Click "Consent" to grant permissions
  4. Get a new access token after granting permissions
- If Teams data is not showing, check the backend logs for permission errors
- Some Teams permissions (like `ChannelMessage.Read.All`) may require admin consent for work/school accounts

## Troubleshooting

### "Invalid token" or "Token expired" error
- Tokens from Graph Explorer expire after about 1 hour
- Get a new token from Graph Explorer and set it again
- Make sure you copy the entire token (it's a long string)

### "Insufficient permissions" error
- Make sure you've granted the required permissions in Graph Explorer
- Try making a test request in Graph Explorer first (e.g., `GET /me/messages`)
- Graph Explorer will prompt you to consent to permissions if needed

### "Authentication failed" error
- Verify the token is correctly copied (no extra spaces or line breaks)
- Check that the token hasn't expired
- Try getting a fresh token from Graph Explorer

### Token not working for API calls
- Make sure you're signed in to Graph Explorer with the correct account
- Verify the token has the required scopes/permissions
- Check backend logs for detailed error messages

## Alternative: Azure App Registration (For Production)

If you need a more permanent solution for production, you can still use Azure App Registration. See the old setup instructions below (commented out for reference).

<details>
<summary>Click to view Azure App Registration setup (for production use)</summary>

### Azure App Registration Steps

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Fill in application details and register
5. Configure API permissions and create client secret
6. Set environment variables in `.env` file

</details>

## Security Notes

- **Never commit tokens to version control**
- Tokens are sensitive - treat them like passwords
- Tokens expire after 1 hour - you'll need to refresh them periodically
- For production, consider using Azure App Registration for automatic token refresh
- Use HTTPS in production

## Additional Resources

- [Microsoft Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)
- [Microsoft Graph API Documentation](https://docs.microsoft.com/en-us/graph/overview)
- [Graph Explorer Documentation](https://docs.microsoft.com/en-us/graph/graph-explorer/overview)



import axios from 'axios'

// Use relative URL in development (to leverage Vite proxy) or explicit URL if provided
// In production, VITE_API_URL should be set to the backend URL
const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'http://localhost:8000')

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 30000 // Increased timeout for AI operations (30 seconds)
})

// Request deduplication: prevent multiple simultaneous calls to the same endpoint
const pendingRequests = new Map()

// Request interceptor for deduplication
api.interceptors.request.use(
  (config) => {
    // Create a unique key for the request (method + url + params)
    const requestKey = `${config.method}:${config.url}:${JSON.stringify(config.params || {})}`
    
    // If a request with the same key is already pending, return the existing promise
    if (pendingRequests.has(requestKey)) {
      console.log(`[API] Deduplicating request: ${requestKey}`)
      return pendingRequests.get(requestKey)
    }
    
    // Create a new promise for this request
    const requestPromise = Promise.resolve(config)
      .then((config) => {
        // Remove from pending after request completes
        pendingRequests.delete(requestKey)
        return config
      })
      .catch((error) => {
        // Remove from pending on error
        pendingRequests.delete(requestKey)
        throw error
      })
    
    pendingRequests.set(requestKey, requestPromise)
    return requestPromise
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to clean up pending requests
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // Clean up on error
    if (error.config) {
      const requestKey = `${error.config.method}:${error.config.url}:${JSON.stringify(error.config.params || {})}`
      pendingRequests.delete(requestKey)
    }
    return Promise.reject(error)
  }
)

// Transcription API
export const transcriptionAPI = {
  startSession: (title) => api.post('/api/transcribe/start', { title }),
  stopSession: (sessionId) => api.post(`/api/transcribe/stop/${sessionId}`),
  getSession: (sessionId) => api.get(`/api/transcribe/session/${sessionId}`),
  getSessionDetails: (sessionId) => api.get(`/api/transcribe/session/${sessionId}/details`),
  getTranscript: (sessionId) => api.get(`/api/transcribe/transcript/${sessionId}`),
  updateTranscript: (sessionId, transcript) => api.put(`/api/transcribe/transcript/${sessionId}`, { transcript }),
  listMeetings: () => api.get('/api/transcribe/meetings')
}

// AI Processing API
export const aiAPI = {
  processTranscript: (sessionId, includeFAQs = true, includeEmailDraft = true) =>
    api.post('/api/ai/summarize', {
      session_id: sessionId,
      include_faqs: includeFAQs,
      include_email_draft: includeEmailDraft
    }),
  getMeetingInsights: (sessionId) =>
    api.post(`/api/ai/meeting-insights/${sessionId}`),
  categorizeEmail: (emailContent, subject, sender) =>
    api.post('/api/ai/categorize-email', null, {
      params: { email_content: emailContent, subject, sender }
    }),
  chat: (query, context = null) =>
    api.post('/api/ai/chat', { query, context }),
  analyzeTrends: (limit = 10) =>
    api.get('/api/ai/trends', { params: { limit } }),
  semanticSearch: (query, limit = 10) =>
    api.post('/api/ai/semantic-search', { query, limit }),
  // New features
  analyzeEmailSentiment: (emailContent, subject) =>
    api.post('/api/ai/email/sentiment', null, {
      params: { email_content: emailContent, subject }
    }),
  scoreEmailPriority: (emailContent, subject, sender, receivedAt = null) =>
    api.post('/api/ai/email/priority-score', null, {
      params: { email_content: emailContent, subject, sender, received_at: receivedAt }
    }),
  summarizeTeamsConversation: (messages, threadId = null) =>
    api.post('/api/ai/teams/conversation-summary', { messages, thread_id: threadId }),
  analyzeChannelActivity: (messages, channelName = null) =>
    api.post('/api/ai/teams/channel-activity', { messages, channel_name: channelName }),
  analyzeMentions: (messages, userEmail = null) =>
    api.post('/api/ai/teams/mentions', { messages, user_email: userEmail }),
  correlateCrossPlatform: (emails = [], teamsMessages = []) =>
    api.post('/api/ai/correlate', { emails, teams_messages: teamsMessages }),
  getDailyDigest: () =>
    api.get('/api/ai/digest/daily'),
  predictDeadlineRisks: () =>
    api.get('/api/ai/risks/deadlines'),
  suggestTeamsResponse: (messageContent, conversationContext = null, tone = null) =>
    api.post('/api/ai/teams/suggest-response', {
      message_content: messageContent,
      conversation_context: conversationContext,
      tone
    }),
  generateJiraContent: (sourceType, content) =>
    api.post('/api/ai/generate-jira-content', content, {
      params: { source_type: sourceType }
    }),
  convertToJira: (text, issueType = 'Task') =>
    api.post('/api/ai/convert/jira', null, {
      params: { text, issue_type: issueType }
    }),
  getJiraProjects: () =>
    api.get('/api/ai/jira-projects'),
  createJiraIssue: (projectKey, summary, description, issueType = 'Task', priority = null, labels = null, assignee = null) =>
    api.post('/api/ai/create-jira-issue', null, {
      params: { 
        project_key: projectKey,
        summary,
        description,
        issue_type: issueType,
        priority,
        labels,
        assignee
      }
    }),
  convertToConfluence: (text, pageType = 'Documentation') =>
    api.post('/api/ai/convert/confluence', null, {
      params: { text, page_type: pageType }
    }),
  optimizeTone: (text, targetAudience, desiredTone, context = null) =>
    api.post('/api/ai/optimize-tone', null, {
      params: { text, target_audience: targetAudience, desired_tone: desiredTone, context }
    }),
  getSmartNotifications: () =>
    api.get('/api/ai/notifications/smart')
}

// Email API
export const emailAPI = {
  getInbox: (maxResults = 50, unreadOnly = false, includeSentiment = false, includePriorityScore = false) =>
    api.get('/api/email/inbox', {
      params: { 
        max_results: maxResults, 
        unread_only: unreadOnly,
        include_sentiment: includeSentiment,
        include_priority_score: includePriorityScore
      }
    }),
  suggestReply: (emailId) =>
    api.post(`/api/email/suggest-reply/${emailId}`),
  summarizeEmail: (emailId) =>
    api.post(`/api/email/summarize/${emailId}`),
  generateTodos: (emailId) =>
    api.post(`/api/email/generate-todos/${emailId}`),
  authenticate: (authCode) =>
    api.post('/api/email/authenticate', null, {
      params: { auth_code: authCode }
    }),
  sendEmail: (to, subject, body, bodyType = 'text', cc = null, bcc = null, importance = 'normal') =>
    api.post('/api/email/send', {
      to,
      subject,
      body,
      body_type: bodyType,
      cc,
      bcc,
      importance
    })
}

// Teams API
export const teamsAPI = {
  getMessages: (maxResults = 50, chatType = 'chats', teamId = null, channelId = null, analyzeMentions = false, analyzeActivity = false, forceRefresh = false) =>
    api.get('/api/teams/messages', {
      params: { 
        max_results: maxResults, 
        chat_type: chatType, 
        team_id: teamId, 
        channel_id: channelId,
        analyze_mentions: analyzeMentions,
        analyze_activity: analyzeActivity,
        force_refresh: forceRefresh
      }
    }),
  getJoinedTeams: (maxResults = 100) =>
    api.get('/api/teams/joined', {
      params: { max_results: maxResults }
    }),
  getTeamChannels: (teamId, maxResults = 100) =>
    api.get(`/api/teams/${teamId}/channels`, {
      params: { max_results: maxResults }
    }),
  authenticate: (authCode) =>
    api.post('/api/teams/authenticate', null, {
      params: { auth_code: authCode }
    }),
  sendMessage: (chatId, teamId, channelId, content, contentType = 'text') =>
    api.post('/api/teams/send-message', {
      chat_id: chatId,
      team_id: teamId,
      channel_id: channelId,
      content,
      content_type: contentType
    })
}

// Authentication API
export const authAPI = {
  getMicrosoftLoginUrl: () => api.get('/api/auth/microsoft/login'),
  getAuthStatus: () => api.get('/api/auth/microsoft/status'),
  logout: () => api.post('/api/auth/microsoft/logout'),
  setToken: (accessToken) => api.post('/api/auth/microsoft/token', { access_token: accessToken })
}

// Export API
export const exportAPI = {
  exportPDF: (sessionId) =>
    api.get(`/api/export/pdf/${sessionId}`, { responseType: 'blob' }),
  exportDOCX: (sessionId) =>
    api.get(`/api/export/docx/${sessionId}`, { responseType: 'blob' }),
  exportJSON: (sessionId) =>
    api.get(`/api/export/json/${sessionId}`, { responseType: 'blob' })
}

// Todo API
export const todoAPI = {
  createTodo: (todo) => api.post('/api/todos/', todo),
  listTodos: (completed = null, priority = null) =>
    api.get('/api/todos/', { params: { completed, priority } }),
  getTodo: (todoId) => api.get(`/api/todos/${todoId}`),
  updateTodo: (todoId, updates) => api.patch(`/api/todos/${todoId}`, updates),
  deleteTodo: (todoId) => api.delete(`/api/todos/${todoId}`),
  reorderTodos: (todoIds) => api.post('/api/todos/reorder', { todo_ids: todoIds })
}

// Search API
export const searchAPI = {
  search: (query, limit = 50) =>
    api.get('/api/search/', { params: { q: query, limit } })
}

export default api




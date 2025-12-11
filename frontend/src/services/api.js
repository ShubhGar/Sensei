import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

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
    api.post('/api/ai/semantic-search', { query, limit })
}

// Email API
export const emailAPI = {
  getInbox: (maxResults = 50, unreadOnly = false) =>
    api.get('/api/email/inbox', {
      params: { max_results: maxResults, unread_only: unreadOnly }
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
    })
}

// Teams API
export const teamsAPI = {
  getMessages: (maxResults = 50, chatType = 'chats', teamId = null, channelId = null) =>
    api.get('/api/teams/messages', {
      params: { max_results: maxResults, chat_type: chatType, team_id: teamId, channel_id: channelId }
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




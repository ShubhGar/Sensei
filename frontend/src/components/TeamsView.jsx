import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  Chip,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import SummarizeIcon from '@mui/icons-material/Summarize'
import ReplyIcon from '@mui/icons-material/Reply'
import AlternateEmailIcon from '@mui/icons-material/AlternateEmail'
import AnalyticsIcon from '@mui/icons-material/Analytics'
import GroupsIcon from '@mui/icons-material/Groups'
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline'
import EmailIcon from '@mui/icons-material/Email'
import { teamsAPI, authAPI, aiAPI } from '../services/api'
import SendIcon from '@mui/icons-material/Send'
import CodeIcon from '@mui/icons-material/Code'
import { useTheme } from '../ThemeContext'
import { getCardBackground, DESIGN_TOKENS } from '../designSystem'
import ContextMenu from './ContextMenu'
import JiraConversionDialog from './JiraConversionDialog'

const TeamsView = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { mode } = useTheme()
  const [messages, setMessages] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [chatType, setChatType] = useState('chats')
  const [contextMenu, setContextMenu] = useState({ open: false, anchorEl: null, data: null })
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [authLoading, setAuthLoading] = useState(true)
  const [tokenDialogOpen, setTokenDialogOpen] = useState(false)
  const [tokenInput, setTokenInput] = useState('')
  const [tokenLoading, setTokenLoading] = useState(false)
  const [analyzeMentions, setAnalyzeMentions] = useState(false)
  const [analyzeActivity, setAnalyzeActivity] = useState(false)
  const [conversationSummary, setConversationSummary] = useState(null)
  const [suggestedResponse, setSuggestedResponse] = useState(null)
  const [responseDialogOpen, setResponseDialogOpen] = useState(false)
  const [summaryDialogOpen, setSummaryDialogOpen] = useState(false)
  const [sendMessageDialog, setSendMessageDialog] = useState({ open: false, messageData: null })
  const [sendingMessage, setSendingMessage] = useState(false)
  const [sendMessageError, setSendMessageError] = useState(null)
  const [jiraDialogOpen, setJiraDialogOpen] = useState(false)
  const [jiraDialogText, setJiraDialogText] = useState('')
  const [generatingJiraContent, setGeneratingJiraContent] = useState(new Set())
  
  // Set nav tab based on current route
  const getNavTab = useCallback(() => {
    if (location.pathname === '/email') return 'email'
    if (location.pathname === '/teams') return 'teams'
    if (location.pathname === '/communications') return 'communications'
    return 'teams'
  }, [location.pathname])
  const [navTab, setNavTab] = useState(() => {
    if (location.pathname === '/email') return 'email'
    if (location.pathname === '/teams') return 'teams'
    if (location.pathname === '/communications') return 'communications'
    return 'teams'
  })
  
  // Theme-aware card background
  const cardBackground = getCardBackground(mode)

  const checkAuthStatus = useCallback(async () => {
    try {
      setAuthLoading(true)
      const response = await authAPI.getAuthStatus()
      setIsAuthenticated(response.data.authenticated || false)
    } catch (err) {
      setIsAuthenticated(false)
    } finally {
      setAuthLoading(false)
    }
  }, [])

  const loadMessages = useCallback(async (forceRefresh = false) => {
    setLoading(true)
    setError(null)
    try {
      // Reduced to 20 items for faster loading
      const response = await teamsAPI.getMessages(20, chatType, null, null, analyzeMentions, analyzeActivity, forceRefresh)
      console.log('[TeamsView] API Response:', response.data)
      setSummary(response.data)
      const messagesList = response.data.messages || []
      const mentionAnalysis = response.data.mention_analysis
      console.log('[TeamsView] Messages list:', messagesList.length, messagesList)
      console.log('[TeamsView] Mention analysis:', mentionAnalysis)
      
      // Helper function to check if message mentions user
      const isMentioned = (message) => {
        if (!analyzeMentions) return false
        // First check the is_mentioned flag from backend
        if (message.is_mentioned === true) return true
        // Fallback: check content directly
        const content = (message.content || '').toLowerCase()
        return content.includes('@shubham') || 
               content.includes('shubham garg') || 
               content.includes('shubham.garg') ||
               (mentionAnalysis?.unanswered_mentions || []).some(m => m.message_id === message.message_id)
      }
      
      // Sort messages by criticality and urgency (highest first)
      const sortedMessages = [...messagesList].sort((a, b) => {
        // Highest priority: Mentions when analyze_mentions is enabled
        const aMentioned = isMentioned(a) ? 2000 : 0
        const bMentioned = isMentioned(b) ? 2000 : 0
        
        // Second: "blocked on us" and "waiting for us"
        const aBlocked = a.priority_score?.blocked_on_us ? 1000 : 0
        const bBlocked = b.priority_score?.blocked_on_us ? 1000 : 0
        const aWaiting = a.priority_score?.waiting_for_us ? 500 : 0
        const bWaiting = b.priority_score?.waiting_for_us ? 500 : 0
        
        // Then by criticality score
        const aCriticality = a.priority_score?.criticality_score || a.priority_score?.priority_score || 0
        const bCriticality = b.priority_score?.criticality_score || b.priority_score?.priority_score || 0
        
        // Then by urgency score
        const aUrgency = a.priority_score?.urgency_score || a.priority_score?.priority_score || 0
        const bUrgency = b.priority_score?.urgency_score || b.priority_score?.priority_score || 0
        
        // Then by priority score
        const aPriority = a.priority_score?.priority_score || 0
        const bPriority = b.priority_score?.priority_score || 0
        
        // Then by unread status (unread first)
        const aUnread = !a.is_read ? 50 : 0
        const bUnread = !b.is_read ? 50 : 0
        
        // Calculate total score
        const aTotal = aMentioned + aBlocked + aWaiting + aCriticality + aUrgency + aPriority + aUnread
        const bTotal = bMentioned + bBlocked + bWaiting + bCriticality + bUrgency + bPriority + bUnread
        
        return bTotal - aTotal // Descending order (highest first)
      })
      
      setMessages(sortedMessages)
      
      // Only show error if there are no messages AND there's an error
      // If we have messages (even dummy data), don't show errors
      if (response.data.error && messagesList.length === 0) {
        const errorType = response.data.error_type
        if (errorType === 'auth' || errorType === 'permission') {
          setError(response.data.error)
        } else if (errorType === 'empty') {
          // Don't show error for empty results, just show the summary message
          setError(null)
        } else {
          setError(response.data.error)
        }
      } else if (messagesList.length > 0) {
        // Clear any errors if we have messages
        setError(null)
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to load Teams messages'
      setError(errorMsg)
      setMessages([])
    } finally {
      setLoading(false)
    }
  }, [chatType, analyzeMentions, analyzeActivity])

  useEffect(() => {
    checkAuthStatus()
    loadMessages()
  }, [chatType, checkAuthStatus, loadMessages])

  useEffect(() => {
    const currentTab = getNavTab()
    setNavTab(currentTab)
  }, [location.pathname, getNavTab])

  const handleSetToken = async () => {
    if (!tokenInput.trim()) {
      setError('Please enter a token')
      return
    }
    
    setTokenLoading(true)
    setError(null)
    try {
      await authAPI.setToken(tokenInput.trim())
      setTokenDialogOpen(false)
      setTokenInput('')
      await checkAuthStatus()
      await loadMessages(true) // Force refresh after setting token
    } catch (err) {
      setError('Failed to set token: ' + (err.response?.data?.detail || err.message))
    } finally {
      setTokenLoading(false)
    }
  }

  const handleContextMenu = (event, message) => {
    event.preventDefault()
    setContextMenu({
      open: true,
      anchorEl: event.currentTarget,
      data: message
    })
  }

  const handleCloseContextMenu = () => {
    setContextMenu({ open: false, anchorEl: null, data: null })
  }

  const handleSummarizeConversation = async () => {
    if (messages.length === 0) return
    setLoading(true)
    try {
      const response = await aiAPI.summarizeTeamsConversation(messages)
      setConversationSummary(response.data)
      setSummaryDialogOpen(true)
    } catch (err) {
      setError('Failed to summarize conversation: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleSuggestResponse = async (messageContent) => {
    setLoading(true)
    try {
      const context = messages.slice(-5).map(m => ({
        sender: m.sender,
        content: m.content
      }))
      const response = await aiAPI.suggestTeamsResponse(messageContent, context)
      setSuggestedResponse(response.data)
      setResponseDialogOpen(true)
    } catch (err) {
      setError('Failed to suggest response: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleNavChange = (event, newValue) => {
    setNavTab(newValue)
    if (newValue === 'email') {
      navigate('/email')
    } else if (newValue === 'communications') {
      navigate('/communications')
    }
  }

  const handleSendTeamsMessage = async (messageData) => {
    setSendingMessage(true)
    setSendMessageError(null)
    try {
      await teamsAPI.sendMessage(
        messageData.chatId,
        messageData.teamId,
        messageData.channelId,
        messageData.content,
        'text'
      )
      setSendMessageDialog({ open: false, messageData: null })
      setSuggestedResponse(null)
      // Show success
      setError(null)
      alert('Teams message sent successfully!')
    } catch (error) {
      setSendMessageError(error.response?.data?.detail || error.message || 'Failed to send message')
    } finally {
      setSendingMessage(false)
    }
  }

  const handleOpenSendMessageDialog = () => {
    if (!suggestedResponse) return
    setSendMessageDialog({
      open: true,
      messageData: {
        chatId: null,
        teamId: null,
        channelId: null,
        content: suggestedResponse.suggested_response
      }
    })
  }

  const handleConvertToJira = async (message) => {
    const messageId = message.message_id || message.id || Math.random().toString()
    setGeneratingJiraContent(prev => new Set(prev).add(messageId))
    setError(null)
    
    try {
      // Generate AI-formatted content optimized for JIRA
      const response = await aiAPI.generateJiraContent('teams', {
        sender: message.sender || 'Unknown',
        channel_id: message.channel_id || null,
        sent_at: message.sent_at || null,
        content: message.content || '',
        summary: message.summary || '',
        is_urgent: message.is_urgent || false
      })
      
      setJiraDialogText(response.data.content)
      setJiraDialogOpen(true)
    } catch (err) {
      setError('Failed to generate JIRA content: ' + (err.response?.data?.detail || err.message))
      // Fallback to basic formatting if AI generation fails
      let textToConvert = ''
      if (message.sender) {
        textToConvert += `From: ${message.sender}\n`
      }
      if (message.sent_at) {
        textToConvert += `Date: ${new Date(message.sent_at).toLocaleString()}\n`
      }
      if (message.channel_id) {
        textToConvert += `Channel: ${message.channel_id}\n`
      }
      textToConvert += '\n'
      if (message.content) {
        textToConvert += message.content
      }
      if (message.summary) {
        textToConvert += `\n\nSummary: ${message.summary}`
      }
      setJiraDialogText(textToConvert)
      setJiraDialogOpen(true)
    } finally {
      setGeneratingJiraContent(prev => {
        const next = new Set(prev)
        next.delete(messageId)
        return next
      })
    }
  }

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Tabs
          value={navTab}
          onChange={handleNavChange}
          sx={{
            borderBottom: 1,
            borderColor: 'divider',
            mb: 3,
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: 600,
              fontSize: '1rem',
              minHeight: 48,
            },
          }}
        >
          <Tab
            icon={<EmailIcon />}
            iconPosition="start"
            label="Email"
            value="email"
            sx={{
              '&.Mui-selected': {
                color: 'primary.main',
              },
            }}
          />
          <Tab
            icon={<GroupsIcon />}
            iconPosition="start"
            label="Teams"
            value="teams"
            sx={{
              '&.Mui-selected': {
                color: 'primary.main',
              },
            }}
          />
          <Tab
            label="All Communications"
            value="communications"
            sx={{
              '&.Mui-selected': {
                color: 'primary.main',
              },
            }}
          />
        </Tabs>
      </Box>

      <Typography 
        variant="h4" 
        gutterBottom
        sx={{ 
          mb: 3,
          fontWeight: 700,
          color: 'text.primary',
        }}
      >
        Microsoft Teams Intelligence
      </Typography>

      {error && summary?.error_type !== 'empty' && (
        <Alert 
          severity={summary?.error_type === 'auth' || summary?.error_type === 'permission' ? 'warning' : 'error'} 
          sx={{ 
            mb: 3,
            borderRadius: 2,
          }} 
          onClose={() => setError(null)}
          action={
            (summary?.error_type === 'auth' || summary?.error_type === 'permission') && (
              <Button
                color="inherit"
                size="small"
                onClick={() => setTokenDialogOpen(true)}
                variant="outlined"
              >
                Set Token
              </Button>
            )
          }
        >
          {error}
        </Alert>
      )}

      {!authLoading && !isAuthenticated && (
        <Alert 
          severity="info" 
          sx={{ 
            mb: 3,
            borderRadius: 2,
          }}
          action={
            <Button
              color="inherit"
              size="small"
              onClick={() => setTokenDialogOpen(true)}
              variant="contained"
            >
              Use Token
            </Button>
          }
        >
          Connect your Microsoft account using a token from <a href="https://developer.microsoft.com/en-us/graph/graph-explorer" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>Graph Explorer</a> to access your Teams messages.
        </Alert>
      )}

      <Card 
        sx={{ 
          mb: 3,
          background: cardBackground,
          borderLeft: '4px solid',
          borderLeftColor: 'primary.main',
        }}
      >
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
            <Typography 
              variant="h6"
              sx={{ 
                fontWeight: 600,
                color: 'text.primary',
              }}
            >
              Teams Summary
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
              <Button
                variant={chatType === 'chats' ? 'contained' : 'outlined'}
                onClick={() => setChatType('chats')}
              >
                Chats
              </Button>
              <Button
                variant={chatType === 'channels' ? 'contained' : 'outlined'}
                onClick={() => setChatType('channels')}
              >
                Channels
              </Button>
              <FormControlLabel
                control={
                  <Switch
                    checked={analyzeMentions}
                    onChange={(e) => {
                      setAnalyzeMentions(e.target.checked)
                      setTimeout(() => loadMessages(), 100)
                    }}
                    size="small"
                  />
                }
                label="Analyze Mentions"
              />
              {chatType === 'channels' && (
                <FormControlLabel
                  control={
                    <Switch
                      checked={analyzeActivity}
                      onChange={(e) => {
                        setAnalyzeActivity(e.target.checked)
                        setTimeout(() => loadMessages(), 100)
                      }}
                      size="small"
                    />
                  }
                  label="Analyze Activity"
                />
              )}
              <Button 
                variant="outlined" 
                onClick={() => loadMessages(true)} 
                disabled={loading}
              >
                Refresh
              </Button>
              <Button
                variant="contained"
                startIcon={<SendIcon />}
                onClick={() => setSendMessageDialog({ open: true, messageData: { chatId: null, teamId: null, channelId: null, content: '' } })}
              >
                Send Message
              </Button>
            </Box>
          </Box>

          {summary && (
            <Box>
              <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', mb: 2 }}>
                <Chip 
                  label={`Total: ${summary.total_messages}`}
                  sx={{ bgcolor: 'background.default', fontWeight: 500 }}
                />
                <Chip 
                  label={`Unread: ${summary.unread}`}
                  sx={{ 
                    bgcolor: 'primary.main',
                    color: 'white',
                    fontWeight: 600,
                  }}
                />
                <Chip 
                  label={`Urgent: ${summary.urgent}`}
                  sx={{ 
                    bgcolor: 'error.main',
                    color: 'white',
                    fontWeight: 600,
                  }}
                />
              </Box>

              {/* Mention Analysis Results */}
              {summary.mention_analysis && summary.mention_analysis.unanswered_mentions && summary.mention_analysis.unanswered_mentions.length > 0 && (
                <Accordion sx={{ mb: 2 }}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <AlternateEmailIcon color="primary" />
                      <Typography variant="h6">
                        @Mentions ({summary.mention_analysis.unanswered_mentions.length} unanswered)
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <List>
                      {summary.mention_analysis.unanswered_mentions.map((mention, idx) => (
                        <ListItem key={idx} sx={{ borderLeft: '3px solid', borderLeftColor: 'warning.main', mb: 1, bgcolor: 'background.default', borderRadius: 2 }}>
                          <ListItemText
                            primary={`From ${mention.sender}`}
                            secondary={
                              <Box>
                                <Typography variant="body2">{mention.content}</Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {new Date(mention.sent_at).toLocaleString()}
                                </Typography>
                              </Box>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  </AccordionDetails>
                </Accordion>
              )}

              {/* Channel Activity Analysis */}
              {summary.channel_activity && (
                <Accordion sx={{ mb: 2 }}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <AnalyticsIcon color="primary" />
                      <Typography variant="h6">
                        Channel Activity ({summary.channel_activity.activity_level})
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    {summary.channel_activity.blockers && summary.channel_activity.blockers.length > 0 && (
                      <Box mb={2}>
                        <Typography variant="subtitle2" fontWeight={600} mb={1}>Blockers:</Typography>
                        <List>
                          {summary.channel_activity.blockers.map((blocker, idx) => (
                            <ListItem key={idx} sx={{ borderLeft: '3px solid', borderLeftColor: 'error.main', mb: 1, bgcolor: 'background.default', borderRadius: 2 }}>
                              <ListItemText
                                primary={blocker.issue}
                                secondary={
                                  <Box>
                                    <Typography variant="body2" color="text.secondary">{blocker.impact}</Typography>
                                    {blocker.suggested_action && (
                                      <Typography variant="body2" color="primary" sx={{ mt: 0.5 }}>
                                        Suggested: {blocker.suggested_action}
                                      </Typography>
                                    )}
                                  </Box>
                                }
                              />
                            </ListItem>
                          ))}
                        </List>
                      </Box>
                    )}
                    {summary.channel_activity.active_discussions && summary.channel_activity.active_discussions.length > 0 && (
                      <Box mb={2}>
                        <Typography variant="subtitle2" fontWeight={600} mb={1}>Active Discussions:</Typography>
                        <List>
                          {summary.channel_activity.active_discussions.map((discussion, idx) => (
                            <ListItem key={idx}>
                              <ListItemText
                                primary={discussion.topic}
                                secondary={`${discussion.participants?.length || 0} participants, ${discussion.message_count || 0} messages`}
                              />
                            </ListItem>
                          ))}
                        </List>
                      </Box>
                    )}
                    {summary.channel_activity.top_contributors && summary.channel_activity.top_contributors.length > 0 && (
                      <Box>
                        <Typography variant="subtitle2" fontWeight={600} mb={1}>Top Contributors:</Typography>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                          {summary.channel_activity.top_contributors.map((contributor, idx) => (
                            <Chip key={idx} label={contributor} size="small" />
                          ))}
                        </Box>
                      </Box>
                    )}
                  </AccordionDetails>
                </Accordion>
              )}
            </Box>
          )}
        </CardContent>
      </Card>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress sx={{ color: 'primary.main' }} />
        </Box>
      ) : (
        <Card
          sx={{
            background: cardBackground,
            borderLeft: '4px solid',
            borderLeftColor: 'primary.main',
          }}
        >
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography 
                variant="h6" 
                sx={{ 
                  fontWeight: 600,
                  color: 'text.primary',
                }}
              >
                Messages
              </Typography>
              {messages.length > 0 && (
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<SummarizeIcon />}
                    onClick={handleSummarizeConversation}
                    disabled={loading}
                  >
                    Summarize Conversation
                  </Button>
                </Box>
              )}
            </Box>
            {messages.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <ChatBubbleOutlineIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.5 }} />
                <Typography variant="h6" color="text.secondary" sx={{ mb: 1, fontWeight: 500 }}>
                  {summary?.error_type === 'auth' || summary?.error_type === 'permission' 
                    ? 'Authentication Required' 
                    : 'No messages found'}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: 500, mx: 'auto' }}>
                  {summary?.teams_summary || summary?.error || 'Your Teams messages haven\'t been loaded yet or there are no messages.'}
                </Typography>
                {!summary && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Loading dummy data...
                  </Typography>
                )}
                {summary?.error_type === 'auth' && (
                  <Button
                    variant="contained"
                    onClick={() => setTokenDialogOpen(true)}
                    startIcon={<GroupsIcon />}
                    sx={{ mb: 2 }}
                  >
                    Set Authentication Token
                  </Button>
                )}
                <Button
                  variant="outlined"
                  onClick={() => loadMessages(true)}
                  startIcon={<GroupsIcon />}
                >
                  Refresh Messages
                </Button>
              </Box>
            ) : (
              <List sx={{ p: 0 }}>
                {messages.map((message, idx) => (
                <ListItem
                  key={message.message_id || idx}
                  onContextMenu={(e) => handleContextMenu(e, message)}
                  sx={{
                    border: '1px solid',
                    borderColor: 'secondary.light',
                    borderRadius: 2, // Very subtle rounded corners
                    mb: 1.5,
                    bgcolor: (message.priority_score?.blocked_on_us 
                      ? (mode === 'dark' ? '#4A1A1A' : '#FFEBEE')
                      : message.priority_score?.waiting_for_us
                      ? (mode === 'dark' ? '#3A2A1E' : '#FFF8E1')
                      : message.priority_score?.priority_score >= 80
                      ? (mode === 'dark' ? '#3A2A1E' : '#FFF8E1')
                      : message.is_urgent 
                      ? (mode === 'dark' ? '#3A2A1E' : '#FFF8E1')
                      : 'background.paper'),
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                      transform: 'translateY(-2px)',
                    },
                    borderLeft: (message.priority_score?.blocked_on_us || message.priority_score?.waiting_for_us || message.priority_score?.priority_score >= 80 || message.is_urgent) ? '4px solid' : 'none',
                    borderLeftColor: message.priority_score?.blocked_on_us ? 'error.dark' : (message.priority_score?.waiting_for_us ? 'warning.dark' : (message.priority_score?.priority_score >= 80 ? 'error.main' : (message.is_urgent ? 'error.main' : 'transparent'))),
                    cursor: 'context-menu',
                  }}
                >
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
                        <Typography 
                          variant="subtitle1"
                          sx={{ 
                            fontWeight: 600,
                            color: 'text.primary',
                          }}
                        >
                          {message.sender || 'Unknown'}
                        </Typography>
                        {message.is_urgent && (
                          <Chip 
                            label="Urgent" 
                            size="small"
                            sx={{ 
                              bgcolor: 'error.main',
                              color: 'white',
                              fontWeight: 600,
                            }}
                          />
                        )}
                        {!message.is_read && (
                          <Chip 
                            label="Unread" 
                            size="small"
                            sx={{ 
                              bgcolor: 'primary.main',
                              color: 'white',
                              fontWeight: 600,
                            }}
                          />
                        )}
                        {message.channel_id && (
                          <Chip 
                            label={`Channel: ${message.channel_id}`} 
                            size="small"
                            sx={{ 
                              bgcolor: 'background.default',
                              fontWeight: 500,
                            }}
                          />
                        )}
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            mt: 1,
                            color: 'text.primary',
                            lineHeight: 1.6,
                          }}
                        >
                          {message.content}
                        </Typography>
                        {message.summary && (
                          <Typography 
                            variant="body2" 
                            color="text.secondary" 
                            sx={{ 
                              mt: 1,
                              fontStyle: 'italic',
                            }}
                          >
                            Summary: {message.summary}
                          </Typography>
                        )}
                        {message.sent_at && (
                          <Typography 
                            variant="caption" 
                            color="text.secondary"
                            sx={{ 
                              mt: 0.5,
                              display: 'block',
                            }}
                          >
                            {new Date(message.sent_at).toLocaleString()}
                          </Typography>
                        )}
                        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<ReplyIcon />}
                            onClick={(e) => {
                              e.stopPropagation()
                              handleSuggestResponse(message.content)
                            }}
                          >
                            Suggest Response
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            color="secondary"
                            disabled={generatingJiraContent.has(message.message_id || message.id || '')}
                            startIcon={generatingJiraContent.has(message.message_id || message.id || '') ? <CircularProgress size={16} /> : <CodeIcon />}
                            onClick={(e) => {
                              e.stopPropagation()
                              handleConvertToJira(message)
                            }}
                          >
                            {generatingJiraContent.has(message.message_id || message.id || '') ? 'Generating...' : 'Convert to JIRA'}
                          </Button>
                        </Box>
                      </Box>
                    }
                  />
                </ListItem>
              ))}
              </List>
            )}
          </CardContent>
        </Card>
      )}

      {/* Token Input Dialog */}
      <Dialog
        open={tokenDialogOpen}
        onClose={() => {
          setTokenDialogOpen(false)
          setTokenInput('')
          setError(null)
        }}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 3,
          }
        }}
      >
        <DialogTitle
          sx={{
            bgcolor: 'primary.main',
            color: 'white',
            fontWeight: 600,
            background: 'linear-gradient(135deg, #009688 0%, #00796B 100%)',
          }}
        >
          Enter Graph Explorer Token
        </DialogTitle>
        <DialogContent sx={{ mt: 2 }}>
          <Alert severity="info" sx={{ mb: 2, borderRadius: 2 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              <strong>How to get your token:</strong>
            </Typography>
            <Typography variant="body2" component="div">
              1. Go to <a href="https://developer.microsoft.com/en-us/graph/graph-explorer" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>Graph Explorer</a>
              <br />
              2. Sign in with your Microsoft account
              <br />
              3. Click on "Access token" tab or check the request headers
              <br />
              4. Copy the token and paste it below
            </Typography>
            <Typography variant="caption" sx={{ mt: 1, display: 'block', fontStyle: 'italic' }}>
              Note: Tokens expire after ~1 hour. You'll need to refresh them periodically.
            </Typography>
          </Alert>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Access Token"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            placeholder="Paste your access token here (starts with eyJ...)"
            variant="outlined"
            sx={{
              '& .MuiOutlinedInput-root': {
                bgcolor: 'background.default',
                fontFamily: 'monospace',
                fontSize: '0.875rem',
              },
            }}
          />
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button 
            onClick={() => {
              setTokenDialogOpen(false)
              setTokenInput('')
              setError(null)
            }}
            variant="outlined"
          >
            Cancel
          </Button>
          <Button 
            onClick={handleSetToken}
            variant="contained"
            disabled={tokenLoading || !tokenInput.trim()}
            startIcon={tokenLoading ? <CircularProgress size={16} /> : null}
          >
            {tokenLoading ? 'Setting Token...' : 'Set Token'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Conversation Summary Dialog */}
      <Dialog
        open={summaryDialogOpen}
        onClose={() => setSummaryDialogOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 3,
            background: cardBackground,
          }
        }}
      >
        <DialogTitle
          sx={{
            bgcolor: 'primary.main',
            color: 'white',
            fontWeight: 600,
            background: 'linear-gradient(135deg, #009688 0%, #00796B 100%)',
          }}
        >
          <Box display="flex" alignItems="center" gap={1}>
            <SummarizeIcon />
            Conversation Summary
          </Box>
        </DialogTitle>
        <DialogContent sx={{ mt: 2 }}>
          {conversationSummary && (
            <Box>
              <Typography variant="body1" paragraph sx={{ lineHeight: 1.8 }}>
                {conversationSummary.summary}
              </Typography>
              {conversationSummary.key_points && conversationSummary.key_points.length > 0 && (
                <Box mb={2}>
                  <Typography variant="subtitle2" fontWeight={600} mb={1}>Key Points:</Typography>
                  <List>
                    {conversationSummary.key_points.map((point, idx) => (
                      <ListItem key={idx}>
                        <ListItemText primary={point} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
              {conversationSummary.action_items && conversationSummary.action_items.length > 0 && (
                <Box mb={2}>
                  <Typography variant="subtitle2" fontWeight={600} mb={1}>Action Items:</Typography>
                  <List>
                    {conversationSummary.action_items.map((item, idx) => (
                      <ListItem key={idx} sx={{ borderLeft: '3px solid', borderLeftColor: 'primary.main', mb: 1, bgcolor: 'background.default', borderRadius: 2 }}>
                        <ListItemText
                          primary={item.task}
                          secondary={`Owner: ${item.owner || 'Unassigned'}${item.deadline ? ` | Deadline: ${item.deadline}` : ''}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
              {conversationSummary.decisions && conversationSummary.decisions.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" fontWeight={600} mb={1}>Decisions:</Typography>
                  <List>
                    {conversationSummary.decisions.map((decision, idx) => (
                      <ListItem key={idx}>
                        <ListItemText primary={decision} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setSummaryDialogOpen(false)} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Suggested Response Dialog */}
      <Dialog
        open={responseDialogOpen}
        onClose={() => setResponseDialogOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 3,
            background: cardBackground,
          }
        }}
      >
        <DialogTitle
          sx={{
            bgcolor: 'primary.main',
            color: 'white',
            fontWeight: 600,
            background: 'linear-gradient(135deg, #009688 0%, #00796B 100%)',
          }}
        >
          <Box display="flex" alignItems="center" gap={1}>
            <ReplyIcon />
            Suggested Teams Response
          </Box>
        </DialogTitle>
        <DialogContent sx={{ mt: 2 }}>
          {suggestedResponse && (
            <Box>
              <Box sx={{ mb: 2, p: 1.5, bgcolor: 'background.default', borderRadius: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Confidence: <strong style={{ color: '#009688' }}>{(suggestedResponse.confidence * 100).toFixed(1)}%</strong>
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Tone: <strong>{suggestedResponse.tone}</strong>
                </Typography>
              </Box>
              <TextField
                fullWidth
                multiline
                rows={8}
                value={suggestedResponse.suggested_response}
                onChange={(e) => {
                  setSuggestedResponse({
                    ...suggestedResponse,
                    suggested_response: e.target.value
                  })
                }}
                variant="outlined"
                label="Response Content (Editable)"
                sx={{
                  '& .MuiOutlinedInput-root': {
                    bgcolor: 'background.default',
                  },
                }}
              />
              {suggestedResponse.alternatives && suggestedResponse.alternatives.length > 0 && (
                <Box mt={2}>
                  <Typography variant="subtitle2" fontWeight={600} mb={1}>Alternative Responses:</Typography>
                  <List>
                    {suggestedResponse.alternatives.map((alt, idx) => (
                      <ListItem key={idx} sx={{ bgcolor: 'background.default', mb: 1, borderRadius: 2 }}>
                        <ListItemText primary={alt} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setResponseDialogOpen(false)} variant="outlined">
            Close
          </Button>
          <Button
            onClick={handleOpenSendMessageDialog}
            variant="contained"
            startIcon={<SendIcon />}
          >
            Send Message
          </Button>
        </DialogActions>
      </Dialog>

      {/* Send Teams Message Dialog */}
      <SendMessageDialog
        open={sendMessageDialog.open}
        onClose={() => {
          setSendMessageDialog({ open: false, messageData: null })
          setSendMessageError(null)
        }}
        messageData={sendMessageDialog.messageData}
        onSend={handleSendTeamsMessage}
        sending={sendingMessage}
        error={sendMessageError}
      />

      {/* Context Menu */}
      <ContextMenu
        anchorEl={contextMenu.anchorEl}
        open={contextMenu.open}
        onClose={handleCloseContextMenu}
        data={contextMenu.data}
        sourceType="teams"
      />

      {/* JIRA Conversion Dialog */}
      <JiraConversionDialog
        open={jiraDialogOpen}
        onClose={() => {
          setJiraDialogOpen(false)
          setJiraDialogText('')
        }}
        initialText={jiraDialogText}
      />
    </Box>
  )
}

// Send Teams Message Dialog Component
const SendMessageDialog = ({ open, onClose, messageData, onSend, sending, error }) => {
  const [messageType, setMessageType] = useState('chat') // 'chat' or 'channel'
  const [chatId, setChatId] = useState('')
  const [teamId, setTeamId] = useState('')
  const [channelId, setChannelId] = useState('')
  const [body, setBody] = useState('')

  useEffect(() => {
    if (open && messageData) {
      setBody(messageData.content || '')
      if (messageData.chatId) {
        setMessageType('chat')
        setChatId(messageData.chatId)
      } else if (messageData.teamId && messageData.channelId) {
        setMessageType('channel')
        setTeamId(messageData.teamId)
        setChannelId(messageData.channelId)
      }
    }
  }, [open, messageData])

  const handleSubmit = () => {
    if (messageType === 'chat') {
      if (!chatId.trim()) return
      onSend({
        chatId: chatId.trim(),
        teamId: null,
        channelId: null,
        content: body
      })
    } else {
      if (!teamId.trim() || !channelId.trim()) return
      onSend({
        chatId: null,
        teamId: teamId.trim(),
        channelId: channelId.trim(),
        content: body
      })
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Send Teams Message</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <TextField
          fullWidth
          select
          label="Message Type"
          value={messageType}
          onChange={(e) => setMessageType(e.target.value)}
          SelectProps={{ native: true }}
          sx={{ mb: 2 }}
        >
          <option value="chat">Chat Message</option>
          <option value="channel">Channel Message</option>
        </TextField>
        {messageType === 'chat' ? (
          <TextField
            fullWidth
            label="Chat ID"
            value={chatId}
            onChange={(e) => setChatId(e.target.value)}
            placeholder="Enter Teams chat ID"
            required
            sx={{ mb: 2 }}
            helperText="You can find the chat ID from the Teams API or URL"
          />
        ) : (
          <>
            <TextField
              fullWidth
              label="Team ID"
              value={teamId}
              onChange={(e) => setTeamId(e.target.value)}
              placeholder="Enter Teams team ID"
              required
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Channel ID"
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              placeholder="Enter Teams channel ID"
              required
              sx={{ mb: 2 }}
            />
          </>
        )}
        <TextField
          fullWidth
          multiline
          rows={6}
          label="Message"
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={sending}>Cancel</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={sending || (messageType === 'chat' ? !chatId.trim() : !teamId.trim() || !channelId.trim()) || !body.trim()}
        >
          {sending ? 'Sending...' : 'Send Message'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default TeamsView




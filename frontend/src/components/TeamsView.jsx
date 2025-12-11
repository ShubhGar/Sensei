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
import { useTheme } from '../ThemeContext'
import ContextMenu from './ContextMenu'

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
  const cardBackground = mode === 'dark' 
    ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)'

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

  const loadMessages = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await teamsAPI.getMessages(50, chatType, null, null, analyzeMentions, analyzeActivity)
      console.log('[TeamsView] API Response:', response.data)
      setSummary(response.data)
      const messagesList = response.data.messages || []
      console.log('[TeamsView] Messages list:', messagesList.length, messagesList)
      setMessages(messagesList)
      
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
      await loadMessages()
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
                onClick={loadMessages} 
                disabled={loading}
              >
                Refresh
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
                        <ListItem key={idx} sx={{ borderLeft: '3px solid', borderLeftColor: 'warning.main', mb: 1, bgcolor: 'background.default', borderRadius: 1 }}>
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
                            <ListItem key={idx} sx={{ borderLeft: '3px solid', borderLeftColor: 'error.main', mb: 1, bgcolor: 'background.default', borderRadius: 1 }}>
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
                  onClick={loadMessages}
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
                    borderRadius: 2,
                    mb: 1.5,
                    bgcolor: message.is_urgent 
                      ? (mode === 'dark' ? '#3A2A1E' : '#FFF8E1')
                      : 'background.paper',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                      transform: 'translateY(-2px)',
                    },
                    borderLeft: message.is_urgent ? '4px solid' : 'none',
                    borderLeftColor: message.is_urgent ? 'error.main' : 'transparent',
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
                      <ListItem key={idx} sx={{ borderLeft: '3px solid', borderLeftColor: 'primary.main', mb: 1, bgcolor: 'background.default', borderRadius: 1 }}>
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
              <Box sx={{ mb: 2, p: 1.5, bgcolor: 'background.default', borderRadius: 1 }}>
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
                variant="outlined"
                InputProps={{
                  readOnly: true
                }}
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
                      <ListItem key={idx} sx={{ bgcolor: 'background.default', mb: 1, borderRadius: 1 }}>
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
          <Button onClick={() => setResponseDialogOpen(false)} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Context Menu */}
      <ContextMenu
        anchorEl={contextMenu.anchorEl}
        open={contextMenu.open}
        onClose={handleCloseContextMenu}
        data={contextMenu.data}
        sourceType="teams"
      />
    </Box>
  )
}

export default TeamsView




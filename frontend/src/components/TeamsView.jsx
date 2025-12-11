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
  TextField
} from '@mui/material'
import GroupsIcon from '@mui/icons-material/Groups'
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline'
import EmailIcon from '@mui/icons-material/Email'
import { teamsAPI, authAPI } from '../services/api'
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
      const response = await teamsAPI.getMessages(50, chatType)
      setSummary(response.data)
      setMessages(response.data.messages || [])
      
      // Show error from API response if present
      if (response.data.error) {
        const errorType = response.data.error_type
        if (errorType === 'auth' || errorType === 'permission') {
          setError(response.data.error)
        } else if (errorType === 'empty' && response.data.messages?.length === 0) {
          // Don't show error for empty results, just show the summary message
          setError(null)
        } else {
          setError(response.data.error)
        }
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to load Teams messages'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [chatType])

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
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
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
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
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
            <Typography 
              variant="h6" 
              gutterBottom
              sx={{ 
                fontWeight: 600,
                color: 'text.primary',
                mb: 2,
              }}
            >
              Messages
            </Typography>
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




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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Tabs,
  Tab
} from '@mui/material'
import EmailIcon from '@mui/icons-material/Email'
import InboxIcon from '@mui/icons-material/Inbox'
import GroupsIcon from '@mui/icons-material/Groups'
import { emailAPI, authAPI } from '../services/api'
import { useTheme } from '../ThemeContext'
import ContextMenu from './ContextMenu'

const EmailView = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { mode } = useTheme()
  const [emails, setEmails] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [suggestedReply, setSuggestedReply] = useState(null)
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
    return 'email'
  }, [location.pathname])
  const [navTab, setNavTab] = useState(() => {
    if (location.pathname === '/email') return 'email'
    if (location.pathname === '/teams') return 'teams'
    if (location.pathname === '/communications') return 'communications'
    return 'email'
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

  const loadInbox = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await emailAPI.getInbox(50, false)
      setSummary(response.data)
      setEmails(response.data.emails || [])
    } catch (err) {
      setError('Failed to load inbox: ' + err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    checkAuthStatus()
    loadInbox()
  }, [checkAuthStatus, loadInbox])

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
      await loadInbox()
    } catch (err) {
      setError('Failed to set token: ' + (err.response?.data?.detail || err.message))
    } finally {
      setTokenLoading(false)
    }
  }

  const handleSuggestReply = async (emailId) => {
    try {
      const response = await emailAPI.suggestReply(emailId)
      setSuggestedReply(response.data)
      setSelectedEmail(emailId)
    } catch (err) {
      setError('Failed to suggest reply: ' + err.message)
    }
  }

  const handleContextMenu = (event, email) => {
    event.preventDefault()
    setContextMenu({
      open: true,
      anchorEl: event.currentTarget,
      data: email
    })
  }

  const handleCloseContextMenu = () => {
    setContextMenu({ open: false, anchorEl: null, data: null })
  }

  const handleNavChange = (event, newValue) => {
    setNavTab(newValue)
    if (newValue === 'teams') {
      navigate('/teams')
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
        Email Intelligence
      </Typography>

      {error && (
        <Alert 
          severity="error" 
          sx={{ 
            mb: 3,
            borderRadius: 2,
          }} 
          onClose={() => setError(null)}
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
          Connect your Microsoft account using a token from <a href="https://developer.microsoft.com/en-us/graph/graph-explorer" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>Graph Explorer</a> to access your Outlook inbox.
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
              Inbox Summary
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Button 
                variant="outlined" 
                onClick={loadInbox} 
                disabled={loading}
              >
                Refresh
              </Button>
            </Box>
          </Box>

          {summary && (
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
              <Chip 
                label={`Total: ${summary.total_emails}`}
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
              {summary.pending_approvals > 0 && (
                <Chip 
                  label={`Pending Approvals: ${summary.pending_approvals}`}
                  sx={{ 
                    bgcolor: 'warning.main',
                    color: 'white',
                    fontWeight: 600,
                  }}
                />
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
            <Typography 
              variant="h6" 
              gutterBottom
              sx={{ 
                fontWeight: 600,
                color: 'text.primary',
                mb: 2,
              }}
            >
              Emails
            </Typography>
            {emails.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <InboxIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.5 }} />
                <Typography variant="h6" color="text.secondary" sx={{ mb: 1, fontWeight: 500 }}>
                  No emails found
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Your inbox is empty or emails haven't been loaded yet.
                </Typography>
                <Button
                  variant="outlined"
                  onClick={loadInbox}
                  startIcon={<EmailIcon />}
                >
                  Refresh Inbox
                </Button>
              </Box>
            ) : (
              <List sx={{ p: 0 }}>
                {emails.map((email) => (
                <ListItem
                  key={email.id}
                  onContextMenu={(e) => handleContextMenu(e, email)}
                  sx={{
                    border: '1px solid',
                    borderColor: 'secondary.light',
                    borderRadius: 2,
                    mb: 1.5,
                    bgcolor: email.is_urgent 
                      ? (mode === 'dark' ? '#3A2A1E' : '#FFF8E1')
                      : 'background.paper',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                      transform: 'translateY(-2px)',
                    },
                    borderLeft: email.is_urgent ? '4px solid' : 'none',
                    borderLeftColor: email.is_urgent ? 'error.main' : 'transparent',
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
                          {email.subject || '(No Subject)'}
                        </Typography>
                        {email.is_urgent && (
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
                        {!email.is_read && (
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
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography 
                          variant="body2" 
                          color="text.secondary"
                          sx={{ mb: 0.5 }}
                        >
                          From: {email.sender}
                        </Typography>
                        {email.summary && (
                          <Typography 
                            variant="body2" 
                            sx={{ 
                              mt: 1,
                              color: 'text.primary',
                              lineHeight: 1.6,
                            }}
                          >
                            {email.summary}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                  <Button
                    size="small"
                    onClick={() => handleSuggestReply(email.id)}
                    variant="outlined"
                  >
                    Suggest Reply
                  </Button>
                </ListItem>
              ))}
              </List>
            )}
          </CardContent>
        </Card>
      )}

      {/* Suggested Reply Dialog */}
      <Dialog
        open={!!suggestedReply}
        onClose={() => {
          setSuggestedReply(null)
          setSelectedEmail(null)
        }}
        maxWidth="md"
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
          Suggested Auto-Reply
        </DialogTitle>
        <DialogContent sx={{ mt: 2 }}>
          {suggestedReply && (
            <Box>
              <Box sx={{ mb: 2, p: 1.5, bgcolor: 'background.default', borderRadius: 1 }}>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: 'text.secondary',
                    fontWeight: 500,
                  }}
                >
                  Confidence: <strong style={{ color: '#009688' }}>{(suggestedReply.confidence * 100).toFixed(1)}%</strong>
                </Typography>
              </Box>
              {suggestedReply.reasoning && (
                <Alert 
                  severity="info" 
                  sx={{ 
                    mb: 2,
                    borderRadius: 2,
                    bgcolor: mode === 'dark' ? '#1E2A3A' : '#E3F2FD',
                  }}
                >
                  {suggestedReply.reasoning}
                </Alert>
              )}
              <TextField
                fullWidth
                multiline
                rows={10}
                value={suggestedReply.suggested_reply}
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
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button 
            onClick={() => {
              setSuggestedReply(null)
              setSelectedEmail(null)
            }}
            variant="contained"
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>

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
        sourceType="email"
      />
    </Box>
  )
}

export default EmailView




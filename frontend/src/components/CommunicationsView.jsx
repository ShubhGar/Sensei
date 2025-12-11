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
  Tab
} from '@mui/material'
import EmailIcon from '@mui/icons-material/Email'
import GroupsIcon from '@mui/icons-material/Groups'
import LoginIcon from '@mui/icons-material/Login'
import { emailAPI, teamsAPI, authAPI } from '../services/api'
import { useTheme } from '../ThemeContext'
import ContextMenu from './ContextMenu'

const CommunicationsView = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { mode } = useTheme()
  const [allMessages, setAllMessages] = useState([])
  const [emailSummary, setEmailSummary] = useState(null)
  const [teamsSummary, setTeamsSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [contextMenu, setContextMenu] = useState({ open: false, anchorEl: null, data: null })
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [authLoading, setAuthLoading] = useState(true)
  
  // Set nav tab based on current route
  const getNavTab = useCallback(() => {
    if (location.pathname === '/email') return 'email'
    if (location.pathname === '/teams') return 'teams'
    if (location.pathname === '/communications') return 'communications'
    return 'communications'
  }, [location.pathname])
  const [navTab, setNavTab] = useState(() => {
    if (location.pathname === '/email') return 'email'
    if (location.pathname === '/teams') return 'teams'
    if (location.pathname === '/communications') return 'communications'
    return 'communications'
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

  const handleMicrosoftLogin = async () => {
    try {
      const response = await authAPI.getMicrosoftLoginUrl()
      window.location.href = response.data.auth_url
    } catch (err) {
      setError('Failed to initiate login: ' + err.message)
    }
  }

  const loadAllCommunications = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Load emails and teams messages in parallel
      const [emailResponse, teamsResponse] = await Promise.allSettled([
        emailAPI.getInbox(50, false),
        teamsAPI.getMessages(50, 'chats')
      ])

      const emails = []
      const teamsMessages = []

      if (emailResponse.status === 'fulfilled') {
        setEmailSummary(emailResponse.value.data)
        const emailData = emailResponse.value.data.emails || []
        emails.push(...emailData.map(email => ({
          ...email,
          type: 'email',
          timestamp: email.received_at || email.sent_at || new Date().toISOString(),
          displayDate: email.received_at || email.sent_at
        })))
      }

      if (teamsResponse.status === 'fulfilled') {
        setTeamsSummary(teamsResponse.value.data)
        const teamsData = teamsResponse.value.data.messages || []
        teamsMessages.push(...teamsData.map(message => ({
          ...message,
          type: 'teams',
          timestamp: message.sent_at || new Date().toISOString(),
          displayDate: message.sent_at
        })))
      }

      // Combine and sort by timestamp (newest first)
      const combined = [...emails, ...teamsMessages].sort((a, b) => {
        const dateA = new Date(a.timestamp || 0)
        const dateB = new Date(b.timestamp || 0)
        return dateB - dateA
      })

      setAllMessages(combined)
    } catch (err) {
      setError('Failed to load communications: ' + err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    checkAuthStatus()
    loadAllCommunications()
  }, [checkAuthStatus, loadAllCommunications])

  useEffect(() => {
    const currentTab = getNavTab()
    setNavTab(currentTab)
  }, [location.pathname, getNavTab])

  const handleNavChange = (event, newValue) => {
    setNavTab(newValue)
    if (newValue === 'email') {
      navigate('/email')
    } else if (newValue === 'teams') {
      navigate('/teams')
    } else if (newValue === 'communications') {
      navigate('/communications')
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

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    try {
      const date = new Date(dateString)
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateString
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
        All Communications
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
              onClick={handleMicrosoftLogin}
              startIcon={<LoginIcon />}
            >
              Connect Microsoft
            </Button>
          }
        >
          Connect your Microsoft account to access your emails and Teams messages.
        </Alert>
      )}

      {/* Summary Cards */}
      {(emailSummary || teamsSummary) && (
        <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          {emailSummary && (
            <Card 
              sx={{ 
                flex: 1,
                minWidth: 200,
                background: cardBackground,
                borderLeft: '4px solid',
                borderLeftColor: 'primary.main',
              }}
            >
              <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 } }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <EmailIcon sx={{ color: 'primary.main' }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    Email Summary
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip 
                    label={`Total: ${emailSummary.total_emails || 0}`}
                    size="small"
                    sx={{ bgcolor: 'background.default', fontWeight: 500 }}
                  />
                  <Chip 
                    label={`Unread: ${emailSummary.unread || 0}`}
                    size="small"
                    sx={{ bgcolor: 'primary.main', color: 'white', fontWeight: 600 }}
                  />
                  {emailSummary.urgent > 0 && (
                    <Chip 
                      label={`Urgent: ${emailSummary.urgent || 0}`}
                      size="small"
                      sx={{ bgcolor: 'error.main', color: 'white', fontWeight: 600 }}
                    />
                  )}
                </Box>
              </CardContent>
            </Card>
          )}
          {teamsSummary && (
            <Card 
              sx={{ 
                flex: 1,
                minWidth: 200,
                background: cardBackground,
                borderLeft: '4px solid',
                borderLeftColor: 'secondary.main',
              }}
            >
              <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 } }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <GroupsIcon sx={{ color: 'secondary.main' }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    Teams Summary
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip 
                    label={`Total: ${teamsSummary.total_messages || 0}`}
                    size="small"
                    sx={{ bgcolor: 'background.default', fontWeight: 500 }}
                  />
                  <Chip 
                    label={`Unread: ${teamsSummary.unread || 0}`}
                    size="small"
                    sx={{ bgcolor: 'primary.main', color: 'white', fontWeight: 600 }}
                  />
                  {teamsSummary.urgent > 0 && (
                    <Chip 
                      label={`Urgent: ${teamsSummary.urgent || 0}`}
                      size="small"
                      sx={{ bgcolor: 'error.main', color: 'white', fontWeight: 600 }}
                    />
                  )}
                </Box>
              </CardContent>
            </Card>
          )}
        </Box>
      )}

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
            transition: 'all 0.3s ease',
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 } }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography 
                variant="h6" 
                sx={{ 
                  fontWeight: 600,
                  color: 'text.primary',
                }}
              >
                All Messages
              </Typography>
              <Button 
                variant="outlined" 
                onClick={loadAllCommunications} 
                disabled={loading}
                size="small"
              >
                Refresh
              </Button>
            </Box>
            {allMessages.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <EmailIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.5 }} />
                <Typography variant="h6" color="text.secondary" sx={{ mb: 1, fontWeight: 500 }}>
                  No communications found
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Your emails and Teams messages will appear here once loaded.
                </Typography>
                <Button
                  variant="outlined"
                  onClick={loadAllCommunications}
                  startIcon={<EmailIcon />}
                >
                  Refresh Communications
                </Button>
              </Box>
            ) : (
              <List sx={{ p: 0 }}>
                {allMessages.map((message, idx) => (
                  <ListItem
                    key={message.id || message.message_id || idx}
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
                          {message.type === 'email' ? (
                            <EmailIcon sx={{ color: 'primary.main', fontSize: '1.2rem' }} />
                          ) : (
                            <GroupsIcon sx={{ color: 'secondary.main', fontSize: '1.2rem' }} />
                          )}
                          <Typography 
                            variant="subtitle1"
                            sx={{ 
                              fontWeight: 600,
                              color: 'text.primary',
                            }}
                          >
                            {message.type === 'email' 
                              ? (message.subject || '(No Subject)')
                              : (message.sender || 'Unknown')
                            }
                          </Typography>
                          <Chip 
                            label={message.type === 'email' ? 'Email' : 'Teams'}
                            size="small"
                            sx={{ 
                              bgcolor: message.type === 'email' ? 'primary.main' : 'secondary.main',
                              color: 'white',
                              fontWeight: 600,
                            }}
                          />
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
                        </Box>
                      }
                      secondary={
                        <Box>
                          {message.type === 'email' ? (
                            <>
                              <Typography 
                                variant="body2" 
                                color="text.secondary"
                                sx={{ mb: 0.5 }}
                              >
                                From: {message.sender}
                              </Typography>
                              {message.summary && (
                                <Typography 
                                  variant="body2" 
                                  sx={{ 
                                    mt: 1,
                                    color: 'text.primary',
                                    lineHeight: 1.6,
                                  }}
                                >
                                  {message.summary}
                                </Typography>
                              )}
                            </>
                          ) : (
                            <>
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
                            </>
                          )}
                          {message.displayDate && (
                            <Typography 
                              variant="caption" 
                              color="text.secondary"
                              sx={{ 
                                mt: 0.5,
                                display: 'block',
                              }}
                            >
                              {formatDate(message.displayDate)}
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

      {/* Context Menu */}
      <ContextMenu
        anchorEl={contextMenu.anchorEl}
        open={contextMenu.open}
        onClose={handleCloseContextMenu}
        data={contextMenu.data}
        sourceType={contextMenu.data?.type || 'email'}
      />
    </Box>
  )
}

export default CommunicationsView

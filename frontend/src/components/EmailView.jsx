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
  Tab,
  Divider,
  IconButton,
  Collapse,
  Avatar,
  Tooltip,
  Switch,
  FormControlLabel,
  LinearProgress
} from '@mui/material'
import EmailIcon from '@mui/icons-material/Email'
import InboxIcon from '@mui/icons-material/Inbox'
import GroupsIcon from '@mui/icons-material/Groups'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import AttachFileIcon from '@mui/icons-material/AttachFile'
import AccessTimeIcon from '@mui/icons-material/AccessTime'
import PersonIcon from '@mui/icons-material/Person'
import PriorityHighIcon from '@mui/icons-material/PriorityHigh'
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward'
import MarkEmailReadIcon from '@mui/icons-material/MarkEmailRead'
import MarkEmailUnreadIcon from '@mui/icons-material/MarkEmailUnread'
import AddTaskIcon from '@mui/icons-material/AddTask'
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
  const [summarizingEmails, setSummarizingEmails] = useState(new Set())
  const [generatingTodos, setGeneratingTodos] = useState(new Set())
  const [expandedEmails, setExpandedEmails] = useState(new Set())
  const [includeSentiment, setIncludeSentiment] = useState(false)
  const [includePriorityScore, setIncludePriorityScore] = useState(false)
  
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
      const response = await emailAPI.getInbox(50, false, includeSentiment, includePriorityScore)
      setSummary(response.data)
      setEmails(response.data.emails || [])
    } catch (err) {
      setError('Failed to load inbox: ' + err.message)
    } finally {
      setLoading(false)
    }
  }, [includeSentiment, includePriorityScore])

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

  const handleSummarizeEmail = async (emailId) => {
    // Check if already has summary
    const email = emails.find(e => e.id === emailId)
    if (email && email.summary) {
      return // Already summarized
    }

    setSummarizingEmails(prev => new Set(prev).add(emailId))
    setError(null)
    
    try {
      const response = await emailAPI.summarizeEmail(emailId)
      const summaryText = response.data.summary
      
      // Update the email in the list with the summary
      setEmails(prevEmails => 
        prevEmails.map(e => 
          e.id === emailId ? { ...e, summary: summaryText } : e
        )
      )
    } catch (err) {
      setError('Failed to summarize email: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSummarizingEmails(prev => {
        const next = new Set(prev)
        next.delete(emailId)
        return next
      })
    }
  }

  const handleGenerateTodos = async (emailId) => {
    setGeneratingTodos(prev => new Set(prev).add(emailId))
    setError(null)
    
    try {
      const response = await emailAPI.generateTodos(emailId)
      const todos = response.data
      
      // Show success message
      setError(null)
      // You could also show a success notification here
      alert(`Successfully generated ${todos.length} todo${todos.length !== 1 ? 's' : ''} from email!`)
      
      // Optionally navigate to todos view
      // navigate('/todos')
    } catch (err) {
      setError('Failed to generate todos: ' + (err.response?.data?.detail || err.message))
    } finally {
      setGeneratingTodos(prev => {
        const next = new Set(prev)
        next.delete(emailId)
        return next
      })
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

  const toggleEmailExpansion = (emailId) => {
    setExpandedEmails(prev => {
      const next = new Set(prev)
      if (next.has(emailId)) {
        next.delete(emailId)
      } else {
        next.add(emailId)
      }
      return next
    })
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown date'
    try {
      const date = new Date(dateString)
      const now = new Date()
      const diffMs = now - date
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)
      const diffDays = Math.floor(diffMs / 86400000)

      if (diffMins < 1) return 'Just now'
      if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`
      if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
      if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
      
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
      })
    } catch (e) {
      return dateString
    }
  }

  const getInitials = (name) => {
    if (!name) return '?'
    const parts = name.trim().split(/\s+/)
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    }
    return name.substring(0, 2).toUpperCase()
  }

  const getImportanceColor = (importance) => {
    switch (importance?.toLowerCase()) {
      case 'high':
        return 'error.main'
      case 'low':
        return 'text.secondary'
      default:
        return 'primary.main'
    }
  }

  const getImportanceIcon = (importance) => {
    switch (importance?.toLowerCase()) {
      case 'high':
        return <PriorityHighIcon fontSize="small" />
      case 'low':
        return <ArrowDownwardIcon fontSize="small" />
      default:
        return null
    }
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
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={includeSentiment}
                    onChange={(e) => {
                      setIncludeSentiment(e.target.checked)
                      setTimeout(() => loadInbox(), 100)
                    }}
                    size="small"
                  />
                }
                label="Sentiment Analysis"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={includePriorityScore}
                    onChange={(e) => {
                      setIncludePriorityScore(e.target.checked)
                      setTimeout(() => loadInbox(), 100)
                    }}
                    size="small"
                  />
                }
                label="Priority Scoring"
              />
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
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {emails.map((email) => {
                  const isExpanded = expandedEmails.has(email.id)
                  const hasBodyPreview = email.body_preview && email.body_preview.trim().length > 0
                  
                  return (
                    <Card
                      key={email.id}
                      onContextMenu={(e) => handleContextMenu(e, email)}
                      sx={{
                        border: '1px solid',
                        borderColor: email.is_urgent 
                          ? 'error.main' 
                          : email.importance === 'high'
                          ? 'warning.main'
                          : 'divider',
                        borderRadius: 2,
                        bgcolor: email.is_urgent 
                          ? (mode === 'dark' ? 'rgba(211, 47, 47, 0.1)' : 'rgba(211, 47, 47, 0.05)')
                          : email.importance === 'high'
                          ? (mode === 'dark' ? 'rgba(255, 152, 0, 0.1)' : 'rgba(255, 152, 0, 0.05)')
                          : !email.is_read
                          ? (mode === 'dark' ? 'rgba(33, 150, 243, 0.1)' : 'rgba(33, 150, 243, 0.05)')
                          : 'background.paper',
                        transition: 'all 0.3s ease',
                        boxShadow: isExpanded 
                          ? (mode === 'dark' ? '0 4px 20px rgba(0,0,0,0.3)' : '0 4px 20px rgba(0,0,0,0.1)')
                          : '0 1px 3px rgba(0,0,0,0.1)',
                        '&:hover': {
                          boxShadow: mode === 'dark' 
                            ? '0 6px 24px rgba(0,0,0,0.4)' 
                            : '0 6px 24px rgba(0,0,0,0.15)',
                          transform: 'translateY(-2px)',
                        },
                        borderLeft: email.is_urgent || email.importance === 'high' ? '4px solid' : 'none',
                        borderLeftColor: email.is_urgent 
                          ? 'error.main' 
                          : email.importance === 'high'
                          ? 'warning.main'
                          : 'transparent',
                        cursor: 'pointer',
                      }}
                      onClick={() => toggleEmailExpansion(email.id)}
                    >
                      <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
                        {/* Header Section */}
                        <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
                          {/* Avatar */}
                          <Avatar
                            sx={{
                              bgcolor: email.is_urgent 
                                ? 'error.main' 
                                : email.importance === 'high'
                                ? 'warning.main'
                                : 'primary.main',
                              width: 48,
                              height: 48,
                              fontSize: '1.1rem',
                              fontWeight: 600,
                            }}
                          >
                            {getInitials(email.sender)}
                          </Avatar>

                          {/* Main Content */}
                          <Box sx={{ flex: 1, minWidth: 0 }}>
                            {/* Subject and Badges Row */}
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
                              <Typography 
                                variant="h6"
                                sx={{ 
                                  fontWeight: email.is_read ? 500 : 700,
                                  color: 'text.primary',
                                  fontSize: '1.1rem',
                                  flex: 1,
                                  minWidth: 200,
                                }}
                              >
                                {email.subject || '(No Subject)'}
                              </Typography>
                              
                              <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', flexWrap: 'wrap' }}>
                                {!email.is_read && (
                                  <Tooltip title="Unread">
                                    <Chip 
                                      icon={<MarkEmailUnreadIcon />}
                                      label="Unread" 
                                      size="small"
                                      sx={{ 
                                        bgcolor: 'primary.main',
                                        color: 'white',
                                        fontWeight: 600,
                                        height: 24,
                                      }}
                                    />
                                  </Tooltip>
                                )}
                                {email.is_urgent && (
                                  <Tooltip title="Urgent">
                                    <Chip 
                                      icon={<PriorityHighIcon />}
                                      label="Urgent" 
                                      size="small"
                                      sx={{ 
                                        bgcolor: 'error.main',
                                        color: 'white',
                                        fontWeight: 600,
                                        height: 24,
                                      }}
                                    />
                                  </Tooltip>
                                )}
                                {email.importance && email.importance !== 'normal' && (
                                  <Tooltip title={`Importance: ${email.importance}`}>
                                    <Chip 
                                      icon={getImportanceIcon(email.importance)}
                                      label={email.importance.charAt(0).toUpperCase() + email.importance.slice(1)}
                                      size="small"
                                      sx={{ 
                                        bgcolor: getImportanceColor(email.importance),
                                        color: 'white',
                                        fontWeight: 600,
                                        height: 24,
                                      }}
                                    />
                                  </Tooltip>
                                )}
                                {email.has_attachments && (
                                  <Tooltip title="Has attachments">
                                    <Chip 
                                      icon={<AttachFileIcon />}
                                      label="Attachment"
                                      size="small"
                                      variant="outlined"
                                      sx={{ 
                                        height: 24,
                                        borderColor: 'text.secondary',
                                        color: 'text.secondary',
                                      }}
                                    />
                                  </Tooltip>
                                )}
                                {email.needs_approval && (
                                  <Tooltip title="Needs approval">
                                    <Chip 
                                      label="Approval" 
                                      size="small"
                                      sx={{ 
                                        bgcolor: 'warning.main',
                                        color: 'white',
                                        fontWeight: 600,
                                        height: 24,
                                      }}
                                    />
                                  </Tooltip>
                                )}
                                {email.sentiment && (
                                  <Tooltip title={`Sentiment: ${email.sentiment.sentiment || 'neutral'}`}>
                                    <Chip 
                                      label={`${email.sentiment.sentiment || 'neutral'}`}
                                      size="small"
                                      sx={{ 
                                        bgcolor: email.sentiment.sentiment === 'positive' 
                                          ? 'success.main' 
                                          : email.sentiment.sentiment === 'negative' || email.sentiment.sentiment === 'frustrated'
                                          ? 'error.main'
                                          : 'info.main',
                                        color: 'white',
                                        fontWeight: 600,
                                        height: 24,
                                      }}
                                    />
                                  </Tooltip>
                                )}
                                {email.priority_score && (
                                  <Tooltip title={`Priority Score: ${email.priority_score.priority_score}/100`}>
                                    <Chip 
                                      label={`Priority: ${email.priority_score.priority_level || 'medium'}`}
                                      size="small"
                                      sx={{ 
                                        bgcolor: email.priority_score.priority_score >= 80
                                          ? 'error.main'
                                          : email.priority_score.priority_score >= 60
                                          ? 'warning.main'
                                          : 'info.main',
                                        color: 'white',
                                        fontWeight: 600,
                                        height: 24,
                                      }}
                                    />
                                  </Tooltip>
                                )}
                              </Box>
                            </Box>

                            {/* Sender and Date Row */}
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1, flexWrap: 'wrap' }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <PersonIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                                <Typography 
                                  variant="body2" 
                                  sx={{ 
                                    color: 'text.primary',
                                    fontWeight: email.is_read ? 400 : 600,
                                  }}
                                >
                                  {email.sender || 'Unknown Sender'}
                                </Typography>
                                {email.sender_email && email.sender_email !== email.sender && (
                                  <Typography 
                                    variant="caption" 
                                    sx={{ 
                                      color: 'text.secondary',
                                      ml: 0.5,
                                    }}
                                  >
                                    &lt;{email.sender_email}&gt;
                                  </Typography>
                                )}
                              </Box>
                              
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <AccessTimeIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                                <Typography 
                                  variant="body2" 
                                  color="text.secondary"
                                >
                                  {formatDate(email.received_at)}
                                </Typography>
                              </Box>
                            </Box>

                            {/* Body Preview (Collapsed View) */}
                            {!isExpanded && hasBodyPreview && (
                              <Typography 
                                variant="body2" 
                                sx={{ 
                                  color: 'text.secondary',
                                  lineHeight: 1.6,
                                  display: '-webkit-box',
                                  WebkitLineClamp: 2,
                                  WebkitBoxOrient: 'vertical',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  mt: 0.5,
                                }}
                              >
                                {email.body_preview}
                              </Typography>
                            )}

                            {/* Summary (if available) */}
                            {email.summary && (
                              <Box sx={{ mt: 1.5, p: 1.5, bgcolor: 'background.default', borderRadius: 1 }}>
                                <Typography 
                                  variant="caption" 
                                  sx={{ 
                                    color: 'text.secondary',
                                    fontWeight: 600,
                                    textTransform: 'uppercase',
                                    letterSpacing: 0.5,
                                    mb: 0.5,
                                    display: 'block',
                                  }}
                                >
                                  AI Summary
                                </Typography>
                                <Typography 
                                  variant="body2" 
                                  sx={{ 
                                    color: 'text.primary',
                                    lineHeight: 1.7,
                                  }}
                                >
                                  {email.summary}
                                </Typography>
                              </Box>
                            )}

                            {/* Expanded Content */}
                            <Collapse in={isExpanded}>
                              <Box sx={{ mt: 2 }}>
                                <Divider sx={{ mb: 2 }} />
                                
                                {/* Full Body Preview */}
                                {hasBodyPreview && (
                                  <Box sx={{ mb: 2 }}>
                                    <Typography 
                                      variant="caption" 
                                      sx={{ 
                                        color: 'text.secondary',
                                        fontWeight: 600,
                                        textTransform: 'uppercase',
                                        letterSpacing: 0.5,
                                        mb: 1,
                                        display: 'block',
                                      }}
                                    >
                                      Preview
                                    </Typography>
                                    <Typography 
                                      variant="body2" 
                                      sx={{ 
                                        color: 'text.primary',
                                        lineHeight: 1.8,
                                        whiteSpace: 'pre-wrap',
                                        wordBreak: 'break-word',
                                      }}
                                    >
                                      {email.body_preview}
                                    </Typography>
                                  </Box>
                                )}

                                {/* Email Metadata */}
                                <Box sx={{ 
                                  display: 'flex', 
                                  flexDirection: 'column', 
                                  gap: 1,
                                  p: 1.5,
                                  bgcolor: 'background.default',
                                  borderRadius: 1,
                                }}>
                                  <Box sx={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
                                    <Typography variant="caption" color="text.secondary">
                                      <strong>Status:</strong> {email.is_read ? 'Read' : 'Unread'}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                      <strong>Importance:</strong> {email.importance || 'Normal'}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                      <strong>Attachments:</strong> {email.has_attachments ? 'Yes' : 'No'}
                                    </Typography>
                                  </Box>
                                  {email.received_at && (
                                    <Typography variant="caption" color="text.secondary">
                                      <strong>Received:</strong> {new Date(email.received_at).toLocaleString()}
                                    </Typography>
                                  )}
                                  
                                  {/* Sentiment Analysis */}
                                  {email.sentiment && (
                                    <Box sx={{ mt: 1, p: 1.5, bgcolor: 'background.paper', borderRadius: 1, borderLeft: '3px solid', borderLeftColor: 'primary.main' }}>
                                      <Typography variant="caption" sx={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
                                        Sentiment Analysis
                                      </Typography>
                                      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
                                        <Chip 
                                          label={`Sentiment: ${email.sentiment.sentiment || 'neutral'}`}
                                          size="small"
                                          color={email.sentiment.sentiment === 'positive' ? 'success' : email.sentiment.sentiment === 'negative' || email.sentiment.sentiment === 'frustrated' ? 'error' : 'default'}
                                        />
                                        {email.sentiment.sentiment_score !== undefined && (
                                          <Box sx={{ flex: 1, minWidth: 100 }}>
                                            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                                              Score: {(email.sentiment.sentiment_score * 100).toFixed(0)}%
                                            </Typography>
                                            <LinearProgress 
                                              variant="determinate" 
                                              value={email.sentiment.sentiment_score * 100}
                                              sx={{ height: 6, borderRadius: 3 }}
                                            />
                                          </Box>
                                        )}
                                        {email.sentiment.urgency_detected && (
                                          <Chip label="Urgent" size="small" color="error" />
                                        )}
                                        {email.sentiment.frustration_detected && (
                                          <Chip label="Frustration Detected" size="small" color="warning" />
                                        )}
                                      </Box>
                                      {email.sentiment.tone && (
                                        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                                          Tone: {email.sentiment.tone}
                                        </Typography>
                                      )}
                                    </Box>
                                  )}

                                  {/* Priority Score */}
                                  {email.priority_score && (
                                    <Box sx={{ mt: 1, p: 1.5, bgcolor: 'background.paper', borderRadius: 1, borderLeft: '3px solid', borderLeftColor: 'warning.main' }}>
                                      <Typography variant="caption" sx={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
                                        Priority Score
                                      </Typography>
                                      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
                                        <Box sx={{ flex: 1, minWidth: 150 }}>
                                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                                            <Typography variant="caption" color="text.secondary">
                                              Score: {email.priority_score.priority_score}/100
                                            </Typography>
                                            <Typography variant="caption" color="text.secondary">
                                              {email.priority_score.priority_level || 'medium'}
                                            </Typography>
                                          </Box>
                                          <LinearProgress 
                                            variant="determinate" 
                                            value={email.priority_score.priority_score}
                                            color={email.priority_score.priority_score >= 80 ? 'error' : email.priority_score.priority_score >= 60 ? 'warning' : 'info'}
                                            sx={{ height: 8, borderRadius: 4 }}
                                          />
                                        </Box>
                                      </Box>
                                      {email.priority_score.factors && email.priority_score.factors.length > 0 && (
                                        <Box sx={{ mt: 1 }}>
                                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                                            Factors:
                                          </Typography>
                                          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                                            {email.priority_score.factors.map((factor, idx) => (
                                              <Chip key={idx} label={factor} size="small" variant="outlined" />
                                            ))}
                                          </Box>
                                        </Box>
                                      )}
                                      {email.priority_score.reasoning && (
                                        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', fontStyle: 'italic' }}>
                                          {email.priority_score.reasoning}
                                        </Typography>
                                      )}
                                    </Box>
                                  )}
                                </Box>

                                {/* Action Buttons */}
                                <Box sx={{ display: 'flex', gap: 1, mt: 2, flexWrap: 'wrap' }}>
                                  <Button
                                    size="small"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handleSummarizeEmail(email.id)
                                    }}
                                    variant="outlined"
                                    disabled={summarizingEmails.has(email.id)}
                                    startIcon={summarizingEmails.has(email.id) ? <CircularProgress size={16} /> : null}
                                  >
                                    {summarizingEmails.has(email.id) ? 'Summarizing...' : 'Summarize'}
                                  </Button>
                                  <Button
                                    size="small"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handleSuggestReply(email.id)
                                    }}
                                    variant="outlined"
                                  >
                                    Suggest Reply
                                  </Button>
                                  <Button
                                    size="small"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handleGenerateTodos(email.id)
                                    }}
                                    variant="contained"
                                    color="primary"
                                    disabled={generatingTodos.has(email.id)}
                                    startIcon={generatingTodos.has(email.id) ? <CircularProgress size={16} /> : <AddTaskIcon />}
                                  >
                                    {generatingTodos.has(email.id) ? 'Generating...' : 'Generate Todos'}
                                  </Button>
                                </Box>
                              </Box>
                            </Collapse>
                          </Box>

                          {/* Expand/Collapse Icon */}
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation()
                              toggleEmailExpansion(email.id)
                            }}
                            sx={{
                              color: 'text.secondary',
                              '&:hover': {
                                bgcolor: 'action.hover',
                              },
                            }}
                          >
                            {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                          </IconButton>
                        </Box>
                      </CardContent>
                    </Card>
                  )
                })}
              </Box>
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





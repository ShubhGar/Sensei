import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Box,
  CircularProgress,
  Alert,
  Chip,
  Paper,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material'
import MicIcon from '@mui/icons-material/Mic'
import EmailIcon from '@mui/icons-material/Email'
import GroupsIcon from '@mui/icons-material/Groups'
import InboxIcon from '@mui/icons-material/Inbox'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import SummarizeIcon from '@mui/icons-material/Summarize'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer'
import CalendarTodayIcon from '@mui/icons-material/CalendarToday'
import { transcriptionAPI, aiAPI, emailAPI, teamsAPI } from '../services/api'
import { useTheme } from '../ThemeContext'
import ContextMenu from './ContextMenu'

const Home = () => {
  const navigate = useNavigate()
  const { mode } = useTheme()
  const [activeSession, setActiveSession] = useState(null)
  const [transcript, setTranscript] = useState('')
  const [mom, setMom] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [emailSummary, setEmailSummary] = useState(null)
  const [teamsSummary, setTeamsSummary] = useState(null)
  const [latestMeetings, setLatestMeetings] = useState([])
  const [selectedMeeting, setSelectedMeeting] = useState(null)
  const [meetingDialogOpen, setMeetingDialogOpen] = useState(false)
  const [loadingMeetings, setLoadingMeetings] = useState(false)
  const [contextMenu, setContextMenu] = useState({ open: false, anchorEl: null, data: null })
  
  // Theme-aware card background values
  const cardBackground = mode === 'dark' 
    ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)'
  
  const highlightCardBackground = mode === 'dark'
    ? 'linear-gradient(135deg, #1E1E1E 0%, #1E3A3A 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #E8F5E9 100%)'

  const loadEmailSummary = useCallback(async () => {
    try {
      const response = await emailAPI.getInbox(10, false)
      if (response.data) {
        setEmailSummary(response.data)
      }
    } catch (err) {
      console.error('Error loading email summary:', err)
      // On error, UI will show empty state prompting user to authenticate
    }
  }, [])

  const loadTeamsSummary = useCallback(async () => {
    try {
      const response = await teamsAPI.getMessages(10)
      if (response.data) {
        setTeamsSummary(response.data)
      }
    } catch (err) {
      console.error('Error loading Teams summary:', err)
      // On error, UI will show empty state prompting user to authenticate
    }
  }, [])

  const loadLatestMeetings = useCallback(async () => {
    setLoadingMeetings(true)
    try {
      const response = await transcriptionAPI.listMeetings()
      const meetings = response.data.meetings || []
      // Get the latest 2 meetings (assuming they're sorted by date, most recent first)
      const latest = meetings.slice(0, 2)
      setLatestMeetings(latest)
    } catch (err) {
      console.error('Error loading latest meetings:', err)
      setLatestMeetings([])
    } finally {
      setLoadingMeetings(false)
    }
  }, [])

  useEffect(() => {
    loadEmailSummary()
    loadTeamsSummary()
    loadLatestMeetings()
  }, [loadEmailSummary, loadTeamsSummary, loadLatestMeetings])

  const handleMeetingClick = (meeting) => {
    setSelectedMeeting(meeting)
    setMeetingDialogOpen(true)
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

  const startTranscription = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await transcriptionAPI.startSession('New Meeting')
      setActiveSession(response.data)
    } catch (err) {
      setError('Failed to start transcription: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const stopTranscription = async () => {
    if (!activeSession) return
    
    setLoading(true)
    try {
      await transcriptionAPI.stopSession(activeSession.id)
      setActiveSession(null)
    } catch (err) {
      setError('Failed to stop transcription: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const generateMOM = async () => {
    if (!activeSession) return
    
    setLoading(true)
    try {
      const response = await aiAPI.processTranscript(activeSession.id)
      setMom(response.data)
    } catch (err) {
      setError('Failed to generate MOM: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleContextMenu = (event, item, sourceType = 'action_item') => {
    event.preventDefault()
    setContextMenu({
      open: true,
      anchorEl: event.currentTarget,
      data: item
    })
  }

  const handleCloseContextMenu = () => {
    setContextMenu({ open: false, anchorEl: null, data: null })
  }

  return (
    <Box>
      <Typography 
        variant="h4" 
        gutterBottom
        sx={{ 
          mb: 3,
          fontWeight: 700,
          color: 'text.primary',
        }}
      >
        Home
      </Typography>

      {/* App Summary */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          mb: 3,
          background: mode === 'dark' 
            ? 'linear-gradient(135deg, #1E3A3A 0%, #2A3A3A 100%)'
            : 'linear-gradient(135deg, #E8F5E9 0%, #F1F8E9 100%)',
          borderLeft: '4px solid',
          borderLeftColor: 'primary.main',
          borderRadius: 2,
        }}
      >
        <Typography 
          variant="h6" 
          gutterBottom
          sx={{ 
            fontWeight: 600,
            color: 'text.primary',
            mb: 1.5,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            fontSize: '1rem',
          }}
        >
          <AutoAwesomeIcon sx={{ color: 'primary.main', fontSize: '1.2rem' }} />
          About PayU Sensei
        </Typography>
        <Typography 
          variant="body2" 
          sx={{ 
            color: 'text.secondary',
            lineHeight: 1.6,
            fontSize: '0.875rem',
          }}
        >
          PayU Sensei is an AI-powered meeting and workday intelligence platform that helps you stay on top of your professional communications. 
          The app automatically transcribes meetings, generates intelligent summaries and action items, analyzes your email inbox, and monitors 
          Microsoft Teams messages. With AI-driven insights, you can quickly identify urgent items, track action items, and never miss important 
          information across all your communication channels.
        </Typography>
      </Paper>

      {error && (
        <Alert 
          severity="error" 
          sx={{ 
            mb: 2.875,
            borderRadius: 2,
          }} 
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}

      <Divider sx={{ mb: 3, borderWidth: 2, borderColor: 'primary.light' }} />
      
      <Typography 
        variant="h6" 
        gutterBottom
        sx={{ 
          mb: 3,
          fontWeight: 700,
          color: 'text.primary',
        }}
      >
        Quick Access
      </Typography>

      <Grid container spacing={{ xs: 2, sm: 2.5, md: 3 }}>
        {/* Transcription Control */}
        <Grid item xs={12} md={4}>
          <Card
            sx={{
              height: '100%',
              background: cardBackground,
              borderLeft: '4px solid',
              borderLeftColor: 'primary.main',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: mode === 'dark' 
                  ? '0 4px 16px rgba(38, 166, 154, 0.25)'
                  : '0 4px 16px rgba(0, 150, 136, 0.15)',
              },
            }}
          >
            <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 }, display: 'flex', flexDirection: 'column', height: '100%', flexGrow: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Box
                  sx={{
                    p: 0.875,
                    borderRadius: 1.5,
                    bgcolor: 'primary.main',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 2px 8px rgba(0, 150, 136, 0.2)',
                  }}
                >
                  <MicIcon sx={{ fontSize: '1.2rem' }} />
                </Box>
                <Typography 
                  variant="h6" 
                  sx={{ 
                    fontWeight: 600,
                    color: 'text.primary',
                    fontSize: '1rem',
                  }}
                >
                  Meeting Transcription
                </Typography>
              </Box>
              <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                {loadingMeetings ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                    <CircularProgress size={24} />
                  </Box>
                ) : latestMeetings.length > 0 ? (
                  <Box sx={{ mb: 2 }}>
                    {latestMeetings.map((meeting) => (
                      <Card
                        key={meeting.id}
                        onClick={() => handleMeetingClick(meeting)}
                        sx={{
                          mb: 1.5,
                          cursor: 'pointer',
                          background: mode === 'dark' 
                            ? 'rgba(38, 166, 154, 0.1)'
                            : 'rgba(0, 150, 136, 0.08)',
                          border: '1px solid',
                          borderColor: 'primary.light',
                          transition: 'all 0.2s ease',
                          '&:hover': {
                            transform: 'translateX(4px)',
                            borderColor: 'primary.main',
                            boxShadow: mode === 'dark' 
                              ? '0 2px 8px rgba(38, 166, 154, 0.2)'
                              : '0 2px 8px rgba(0, 150, 136, 0.15)',
                          },
                        }}
                      >
                        <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                          <Typography 
                            variant="subtitle2" 
                            sx={{ 
                              fontWeight: 600,
                              color: 'text.primary',
                              mb: 0.5,
                            }}
                          >
                            {meeting.title || 'Untitled Meeting'}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                            <Chip
                              icon={<CalendarTodayIcon />}
                              label={formatDate(meeting.started_at)}
                              size="small"
                              sx={{ 
                                fontSize: '0.7rem',
                                height: '20px',
                                bgcolor: 'background.default' 
                              }}
                            />
                            {meeting.mom && (
                              <Chip
                                icon={<SummarizeIcon />}
                                label="MOM"
                                size="small"
                                sx={{ 
                                  fontSize: '0.7rem',
                                  height: '20px',
                                  bgcolor: 'primary.main', 
                                  color: 'white' 
                                }}
                              />
                            )}
                          </Box>
                        </CardContent>
                      </Card>
                    ))}
                  </Box>
                ) : (
                    <Typography 
                    variant="body2" 
                    color="text.secondary" 
                    sx={{ 
                      mb: 2, 
                      fontSize: { xs: '0.75rem', sm: '0.875rem' },
                      textAlign: 'center'
                    }}
                  >
                    No recent meetings
                  </Typography>
                )}
                <Box sx={{ mt: 'auto', textAlign: 'center' }}>
                  <Typography 
                    variant="body2" 
                    color="text.secondary" 
                    sx={{ 
                      mb: 2, 
                      fontSize: { xs: '0.75rem', sm: '0.875rem' },
                      textAlign: 'center'
                    }}
                  >
                    Click to start a new meeting transcription session
                  </Typography>
                  <Button
                    variant="contained"
                    onClick={() => navigate('/transcription')}
                    fullWidth
                    sx={{
                      bgcolor: 'primary.main',
                      py: 1.125,
                      fontSize: { xs: '0.875rem', sm: '0.9rem' },
                      fontWeight: 600,
                      textTransform: 'none',
                      borderRadius: 2,
                      boxShadow: '0 2px 8px rgba(0, 150, 136, 0.25)',
                      '&:hover': {
                        bgcolor: 'primary.dark',
                        boxShadow: '0 4px 12px rgba(0, 150, 136, 0.35)',
                        transform: 'translateY(-1px)',
                      },
                      transition: 'all 0.2s ease',
                    }}
                  >
                    Start Transcription
                  </Button>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Email Summary */}
        <Grid item xs={12} md={4}>
          <Card
            sx={{
              height: '100%',
              background: cardBackground,
              borderLeft: '4px solid',
              borderLeftColor: 'secondary.main',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: mode === 'dark' 
                  ? '0 4px 16px rgba(38, 166, 154, 0.25)'
                  : '0 4px 16px rgba(0, 150, 136, 0.15)',
              },
            }}
          >
            <CardContent sx={{ p: { xs: 1.875, sm: 2.375 }, display: 'flex', flexDirection: 'column', height: '100%', flexGrow: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.625, mt: 0.125 }}>
                <Box
                  sx={{
                    p: 0.875,
                    borderRadius: 1.5,
                    bgcolor: 'secondary.main',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 2px 8px rgba(0, 150, 136, 0.2)',
                  }}
                >
                  <EmailIcon sx={{ fontSize: '1.2rem' }} />
                </Box>
                <Typography 
                  variant="h6" 
                  sx={{ 
                    fontWeight: 600,
                    color: 'text.primary',
                    fontSize: '1rem',
                  }}
                >
                  Email Summary
                </Typography>
              </Box>
              {emailSummary && emailSummary.total_emails > 0 ? (
                <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                    <Chip 
                      label={`Total: ${emailSummary.total_emails}`}
                      sx={{ bgcolor: 'background.default', fontWeight: 500 }}
                    />
                    <Chip 
                      label={`Unread: ${emailSummary.unread}`}
                      sx={{ 
                        bgcolor: 'primary.main',
                        color: 'white',
                        fontWeight: 600,
                        boxShadow: '0 1px 3px rgba(0, 150, 136, 0.2)',
                      }}
                    />
                    <Chip 
                      label={`Urgent: ${emailSummary.urgent}`}
                      sx={{ 
                        bgcolor: 'error.main',
                        color: 'white',
                        fontWeight: 600,
                        boxShadow: '0 1px 3px rgba(255, 82, 82, 0.2)',
                      }}
                    />
                  </Box>
                  {emailSummary.mailbox_summary && (
                    <Box 
                      sx={{ 
                        mb: 2,
                        p: 1.5,
                        bgcolor: mode === 'dark' ? 'rgba(38, 166, 154, 0.1)' : 'rgba(0, 150, 136, 0.08)',
                        borderRadius: 1.5,
                        borderLeft: '3px solid',
                        borderLeftColor: 'primary.main',
                      }}
                    >
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          color: 'text.primary',
                          lineHeight: 1.6,
                          fontSize: '0.8rem',
                          fontStyle: 'italic',
                        }}
                      >
                        {emailSummary.mailbox_summary}
                      </Typography>
                    </Box>
                  )}
                  {emailSummary.pending_approvals > 0 && (
                    <Alert 
                      severity="warning" 
                      sx={{ 
                        mt: 2,
                        mb: 2,
                        borderRadius: 2,
                        bgcolor: mode === 'dark' ? '#3A2A1E' : '#FFF8E1',
                      }}
                    >
                      {emailSummary.pending_approvals} pending approvals
                    </Alert>
                  )}
                  <Box sx={{ mt: 'auto' }}>
                    <Button
                      variant="contained"
                      onClick={() => navigate('/email')}
                      fullWidth
                      sx={{
                        mt: 2,
                        bgcolor: 'primary.main',
                        py: 1.25,
                        fontSize: { xs: '0.875rem', sm: '0.9rem' },
                        fontWeight: 600,
                        textTransform: 'none',
                        borderRadius: 2,
                        boxShadow: '0 2px 8px rgba(0, 150, 136, 0.25)',
                        '&:hover': {
                          bgcolor: 'primary.dark',
                          boxShadow: '0 4px 12px rgba(0, 150, 136, 0.35)',
                          transform: 'translateY(-1px)',
                        },
                        transition: 'all 0.2s ease',
                      }}
                    >
                      View Details
                    </Button>
                  </Box>
                </Box>
              ) : (
                <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                  <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', py: 3 }}>
                    <InboxIcon sx={{ fontSize: 36, color: 'text.secondary', mb: 1, opacity: 0.5 }} />
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem', mb: 2, textAlign: 'center' }}>
                      No email data available
                    </Typography>
                  </Box>
                  <Box sx={{ mt: 'auto' }}>
                    <Button
                      variant="contained"
                      onClick={() => navigate('/email')}
                      fullWidth
                      sx={{
                        mt: 2,
                        bgcolor: 'primary.main',
                        py: 1.25,
                        fontSize: { xs: '0.875rem', sm: '0.9rem' },
                        fontWeight: 600,
                        textTransform: 'none',
                        borderRadius: 2,
                        boxShadow: '0 2px 8px rgba(0, 150, 136, 0.25)',
                        '&:hover': {
                          bgcolor: 'primary.dark',
                          boxShadow: '0 4px 12px rgba(0, 150, 136, 0.35)',
                          transform: 'translateY(-1px)',
                        },
                        transition: 'all 0.2s ease',
                      }}
                    >
                      View Details
                    </Button>
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Teams Summary */}
        <Grid item xs={12} md={4}>
          <Card
            sx={{
              height: '100%',
              background: cardBackground,
              borderLeft: '4px solid',
              borderLeftColor: 'secondary.main',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: mode === 'dark' 
                  ? '0 4px 16px rgba(38, 166, 154, 0.25)'
                  : '0 4px 16px rgba(0, 150, 136, 0.15)',
              },
            }}
          >
            <CardContent sx={{ p: { xs: 1.875, sm: 2.375 }, display: 'flex', flexDirection: 'column', height: '100%', flexGrow: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.625, mt: 0.125 }}>
                <Box
                  sx={{
                    p: 0.875,
                    borderRadius: 1.5,
                    bgcolor: 'secondary.main',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 2px 8px rgba(0, 150, 136, 0.2)',
                  }}
                >
                  <GroupsIcon sx={{ fontSize: '1.2rem' }} />
                </Box>
                <Typography 
                  variant="h6" 
                  sx={{ 
                    fontWeight: 600,
                    color: 'text.primary',
                    fontSize: '1rem',
                  }}
                >
                  Teams Summary
                </Typography>
              </Box>
              {teamsSummary && teamsSummary.total_messages > 0 ? (
                <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                    <Chip 
                      label={`Total: ${teamsSummary.total_messages}`}
                      sx={{ bgcolor: 'background.default', fontWeight: 500 }}
                    />
                    {teamsSummary.unread > 0 && (
                      <Chip 
                        label={`Unread: ${teamsSummary.unread}`}
                        sx={{ 
                          bgcolor: 'primary.main',
                          color: 'white',
                          fontWeight: 600,
                          boxShadow: '0 1px 3px rgba(0, 150, 136, 0.2)',
                        }}
                      />
                    )}
                    {teamsSummary.urgent > 0 && (
                      <Chip 
                        label={`Urgent: ${teamsSummary.urgent}`}
                        sx={{ 
                          bgcolor: 'error.main',
                          color: 'white',
                          fontWeight: 600,
                          boxShadow: '0 1px 3px rgba(255, 82, 82, 0.2)',
                        }}
                      />
                    )}
                  </Box>
                  {teamsSummary.teams_summary && (
                    <Box 
                      sx={{ 
                        mb: 2,
                        p: 1.5,
                        bgcolor: mode === 'dark' ? 'rgba(38, 166, 154, 0.1)' : 'rgba(0, 150, 136, 0.08)',
                        borderRadius: 1.5,
                        borderLeft: '3px solid',
                        borderLeftColor: 'primary.main',
                      }}
                    >
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          color: 'text.primary',
                          lineHeight: 1.6,
                          fontSize: '0.8rem',
                          fontStyle: 'italic',
                        }}
                      >
                        {teamsSummary.teams_summary}
                      </Typography>
                    </Box>
                  )}
                  <Box sx={{ mt: 'auto' }}>
                    <Button
                      variant="contained"
                      onClick={() => navigate('/teams')}
                      fullWidth
                      sx={{
                        mt: 1.25,
                        mb: 0.25,
                        bgcolor: 'primary.main',
                        py: 1.25,
                        fontSize: { xs: '0.875rem', sm: '0.9rem' },
                        fontWeight: 600,
                        textTransform: 'none',
                        borderRadius: 2,
                        boxShadow: '0 2px 8px rgba(0, 150, 136, 0.25)',
                        '&:hover': {
                          bgcolor: 'primary.dark',
                          boxShadow: '0 4px 12px rgba(0, 150, 136, 0.35)',
                          transform: 'translateY(-1px)',
                        },
                        transition: 'all 0.2s ease',
                      }}
                    >
                      View Details
                    </Button>
                  </Box>
                </Box>
              ) : (
                <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                  <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', py: 3 }}>
                    <GroupsIcon sx={{ fontSize: 36, color: 'text.secondary', mb: 1, opacity: 0.5 }} />
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem', mb: 2, textAlign: 'center' }}>
                      No Teams data available
                    </Typography>
                  </Box>
                  <Box sx={{ mt: 'auto' }}>
                    <Button
                      variant="contained"
                      onClick={() => navigate('/teams')}
                      fullWidth
                      sx={{
                        mt: 2,
                        bgcolor: 'primary.main',
                        py: 1.25,
                        fontSize: { xs: '0.875rem', sm: '0.9rem' },
                        fontWeight: 600,
                        textTransform: 'none',
                        borderRadius: 2,
                        boxShadow: '0 2px 8px rgba(0, 150, 136, 0.25)',
                        '&:hover': {
                          bgcolor: 'primary.dark',
                          boxShadow: '0 4px 12px rgba(0, 150, 136, 0.35)',
                          transform: 'translateY(-1px)',
                        },
                        transition: 'all 0.2s ease',
                      }}
                    >
                      View Details
                    </Button>
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* MOM Preview */}
        {mom && mom.mom && (
          <Grid item xs={12}>
            <Card
              sx={{
                background: highlightCardBackground,
                border: '2px solid',
                borderColor: 'primary.main',
                boxShadow: mode === 'dark' 
                  ? '0 2px 8px rgba(38, 166, 154, 0.2)'
                  : '0 2px 8px rgba(0, 150, 136, 0.1)',
              }}
            >
              <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 }, display: 'flex', flexDirection: 'column', height: '100%' }}>
                <Typography 
                  variant="h6" 
                  gutterBottom
                  sx={{ 
                    fontWeight: 600,
                    color: 'primary.dark',
                    mb: 2,
                  }}
                >
                  Minutes of Meeting
                </Typography>
                <Box 
                  sx={{ 
                    p: 2, 
                    bgcolor: 'background.paper', 
                    borderRadius: 2,
                    mb: 2,
                    border: '1px solid',
                    borderColor: 'secondary.light',
                  }}
                >
                  <Typography variant="body2" paragraph sx={{ color: 'text.primary', lineHeight: 1.7, m: 0 }}>
                    {mom.mom.summary || 'No summary available'}
                  </Typography>
                </Box>
                {mom.mom.action_items && mom.mom.action_items.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography 
                      variant="subtitle2" 
                      gutterBottom
                      sx={{ 
                        fontWeight: 600,
                        color: 'text.primary',
                        mb: 1.5,
                      }}
                    >
                      Action Items:
                    </Typography>
                    <Box 
                      component="ul" 
                      sx={{ 
                        listStyle: 'none',
                        p: 0,
                        m: 0,
                        '& li': {
                          p: 1.5,
                          mb: 1,
                          bgcolor: 'background.default',
                          borderRadius: 1,
                          borderLeft: '3px solid',
                          borderLeftColor: 'primary.main',
                        }
                      }}
                    >
                      {mom.mom.action_items.map((item, idx) => (
                        <li 
                          key={idx}
                          onContextMenu={(e) => handleContextMenu(e, item, 'action_item')}
                          style={{ cursor: 'context-menu' }}
                        >
                          <Typography variant="body2" sx={{ fontWeight: 500, mb: 0.5 }}>
                            {item.task}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Owner: {item.owner || 'Unassigned'}
                          </Typography>
                        </li>
                      ))}
                    </Box>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      {/* Meeting Details Dialog */}
      <Dialog
        open={meetingDialogOpen}
        onClose={() => setMeetingDialogOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            background: cardBackground,
            borderRadius: 3,
          }
        }}
      >
        {selectedMeeting && (
          <>
            <DialogTitle 
              sx={{ 
                pb: 1,
                bgcolor: 'primary.main',
                color: 'white',
                fontWeight: 600,
                background: 'linear-gradient(135deg, #009688 0%, #00796B 100%)',
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  {selectedMeeting.title || 'Untitled Meeting'}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip
                    icon={<CalendarTodayIcon />}
                    label={`Started: ${formatDate(selectedMeeting.started_at)}`}
                    size="small"
                    sx={{ bgcolor: 'background.default' }}
                  />
                  {selectedMeeting.ended_at && (
                    <Chip
                      icon={<CalendarTodayIcon />}
                      label={`Ended: ${formatDate(selectedMeeting.ended_at)}`}
                      size="small"
                      sx={{ bgcolor: 'background.default' }}
                    />
                  )}
                </Box>
              </Box>
            </DialogTitle>
            <DialogContent>
              <Box sx={{ mt: 1 }}>
                {/* MOM Section */}
                {selectedMeeting.mom && (
                  <Accordion defaultExpanded sx={{ mb: 2, bgcolor: 'background.default' }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <SummarizeIcon sx={{ color: 'primary.main' }} />
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          Minutes of Meeting
                        </Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                          Summary
                        </Typography>
                        <Paper sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
                          <Typography variant="body2" sx={{ lineHeight: 1.7 }}>
                            {selectedMeeting.mom.summary || 'No summary available'}
                          </Typography>
                        </Paper>
                      </Box>

                      {selectedMeeting.mom.decisions && selectedMeeting.mom.decisions.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                            Decisions
                          </Typography>
                          {selectedMeeting.mom.decisions.map((decision, idx) => (
                            <Paper key={idx} sx={{ p: 1.5, mb: 1, bgcolor: 'background.paper', borderRadius: 1, borderLeft: '3px solid', borderLeftColor: 'primary.light' }}>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                {decision.decision || 'No decision text'}
                              </Typography>
                              {decision.context && (
                                <Typography variant="caption" color="text.secondary">
                                  {decision.context}
                                </Typography>
                              )}
                            </Paper>
                          ))}
                        </Box>
                      )}

                      {selectedMeeting.mom.action_items && selectedMeeting.mom.action_items.length > 0 && (
                        <Box>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                            Action Items
                          </Typography>
                          {selectedMeeting.mom.action_items.map((item, idx) => (
                            <Paper 
                              key={idx} 
                              onContextMenu={(e) => handleContextMenu(e, item, 'action_item')}
                              sx={{ 
                                p: 1.5, 
                                mb: 1, 
                                bgcolor: 'background.paper', 
                                borderRadius: 1, 
                                borderLeft: '3px solid', 
                                borderLeftColor: 'primary.main',
                                cursor: 'context-menu',
                              }}
                            >
                              <Typography variant="body2" sx={{ fontWeight: 500, mb: 0.5 }}>
                                {item.task || 'No task description'}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                Owner: {item.owner || 'Unassigned'} | Deadline: {item.deadline || 'TBD'} | Priority: {item.priority || 'Medium'}
                              </Typography>
                            </Paper>
                          ))}
                        </Box>
                      )}
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* FAQs Section */}
                {selectedMeeting.faqs && selectedMeeting.faqs.length > 0 && (
                  <Accordion sx={{ mb: 2, bgcolor: 'background.default' }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <QuestionAnswerIcon sx={{ color: 'secondary.main' }} />
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          FAQs ({selectedMeeting.faqs.length})
                        </Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      {selectedMeeting.faqs.map((faq, idx) => (
                        <Paper key={idx} sx={{ p: 2, mb: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'primary.dark', mb: 1 }}>
                            Q: {faq.question || 'No question'}
                          </Typography>
                          <Typography variant="body2" sx={{ lineHeight: 1.7 }}>
                            A: {faq.answer || 'No answer'}
                          </Typography>
                          {faq.context && (
                            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                              Context: {faq.context}
                            </Typography>
                          )}
                        </Paper>
                      ))}
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Email Draft Section */}
                {selectedMeeting.email_draft && (
                  <Accordion sx={{ mb: 2, bgcolor: 'background.default' }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <EmailIcon sx={{ color: 'success.main' }} />
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          Follow-up Email Draft
                        </Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Paper sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
                        <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', lineHeight: 1.7 }}>
                          To: {selectedMeeting.email_draft.to && selectedMeeting.email_draft.to.length > 0 ? selectedMeeting.email_draft.to.join(', ') : 'N/A'}
                          {selectedMeeting.email_draft.cc && selectedMeeting.email_draft.cc.length > 0 && (
                            <>
                              {'\n'}CC: {selectedMeeting.email_draft.cc.join(', ')}
                            </>
                          )}
                          {'\n'}Subject: {selectedMeeting.email_draft.subject || 'No Subject'}
                          {'\n\n'}{selectedMeeting.email_draft.body || 'No body content'}
                        </Typography>
                      </Paper>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* Transcript Section */}
                {(selectedMeeting.full_transcript || selectedMeeting.transcript) && (
                  <Accordion sx={{ bgcolor: 'background.default' }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Full Transcript
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Paper sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 1, maxHeight: 400, overflow: 'auto' }}>
                        <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', lineHeight: 1.7 }}>
                          {selectedMeeting.full_transcript || selectedMeeting.transcript || 'No transcript available'}
                        </Typography>
                      </Paper>
                    </AccordionDetails>
                  </Accordion>
                )}
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => navigate('/meetings')} color="primary">
                View All Meetings
              </Button>
              <Button onClick={() => setMeetingDialogOpen(false)} color="primary" variant="contained">
                Close
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Context Menu */}
      <ContextMenu
        anchorEl={contextMenu.anchorEl}
        open={contextMenu.open}
        onClose={handleCloseContextMenu}
        data={contextMenu.data}
        sourceType="action_item"
      />
    </Box>
  )
}

export default Home


import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Divider,
  Grid,
  Tabs,
  Tab
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import EmailIcon from '@mui/icons-material/Email'
import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer'
import SummarizeIcon from '@mui/icons-material/Summarize'
import CalendarTodayIcon from '@mui/icons-material/CalendarToday'
import MicIcon from '@mui/icons-material/Mic'
import HistoryIcon from '@mui/icons-material/History'
import { transcriptionAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const OldMeetingsView = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { mode } = useTheme()
  const [meetings, setMeetings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedMeeting, setExpandedMeeting] = useState(null)
  
  // Set nav tab based on current route
  const getNavTab = () => {
    if (location.pathname === '/transcription') return 'transcription'
    if (location.pathname === '/meetings') return 'meetings'
    return 'meetings'
  }
  const [navTab, setNavTab] = useState(getNavTab())

  useEffect(() => {
    loadMeetings()
  }, [])

  useEffect(() => {
    const currentTab = getNavTab()
    setNavTab(currentTab)
  }, [location.pathname])

  const loadMeetings = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await transcriptionAPI.listMeetings()
      setMeetings(response.data.meetings || [])
    } catch (err) {
      setError('Failed to load meetings: ' + err.message)
      console.error('Error loading meetings:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleExpand = (meetingId) => {
    setExpandedMeeting(expandedMeeting === meetingId ? null : meetingId)
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

  const getCardBackground = () => {
    return mode === 'dark' 
      ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
      : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)'
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    )
  }

  const handleNavChange = (event, newValue) => {
    setNavTab(newValue)
    if (newValue === 'transcription') {
      navigate('/transcription')
    } else if (newValue === 'meetings') {
      navigate('/meetings')
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
            icon={<MicIcon />}
            iconPosition="start"
            label="New Transcription"
            value="transcription"
            sx={{
              '&.Mui-selected': {
                color: 'primary.main',
              },
            }}
          />
          <Tab
            icon={<HistoryIcon />}
            iconPosition="start"
            label="Past Meetings"
            value="meetings"
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
        Past Meetings
      </Typography>

      {error && (
        <Alert 
          severity="warning" 
          sx={{ 
            mb: 3,
            borderRadius: 2,
          }} 
          onClose={() => setError(null)}
        >
          {error}. Showing available data.
        </Alert>
      )}

      {meetings.length === 0 ? (
        <Card
          sx={{
            background: getCardBackground(),
            borderLeft: '4px solid',
            borderLeftColor: 'primary.main',
            transition: 'all 0.3s ease',
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 }, textAlign: 'center' }}>
            <Typography 
              variant="h6" 
              color="text.secondary" 
              gutterBottom
              sx={{ 
                fontWeight: 600,
                mb: 1,
              }}
            >
              No meetings found
            </Typography>
            <Typography 
              variant="body2" 
              color="text.secondary"
              sx={{ 
                lineHeight: 1.7,
              }}
            >
              Start a new meeting to see it here
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Box>
          {meetings.map((meeting) => (
            <Card
              key={meeting.id}
              sx={{
                mb: 3,
                background: getCardBackground(),
                borderLeft: '4px solid',
                borderLeftColor: 'primary.main',
                transition: 'all 0.3s ease',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: mode === 'dark' 
                    ? '0 4px 16px rgba(38, 166, 154, 0.25)'
                    : '0 4px 16px rgba(0, 150, 136, 0.15)',
                },
              }}
            >
              <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 } }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography 
                      variant="h6" 
                      sx={{ 
                        fontWeight: 600,
                        color: 'text.primary',
                        mb: 1,
                      }}
                    >
                      {meeting.title || 'Untitled Meeting'}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
                      <Chip
                        icon={<CalendarTodayIcon />}
                        label={`Started: ${formatDate(meeting.started_at)}`}
                        size="small"
                        sx={{ bgcolor: 'background.default' }}
                      />
                      {meeting.ended_at && (
                        <Chip
                          icon={<CalendarTodayIcon />}
                          label={`Ended: ${formatDate(meeting.ended_at)}`}
                          size="small"
                          sx={{ bgcolor: 'background.default' }}
                        />
                      )}
                      {meeting.mom && (
                        <Chip
                          icon={<SummarizeIcon />}
                          label="MOM Available"
                          size="small"
                          sx={{ bgcolor: 'primary.main', color: 'white' }}
                        />
                      )}
                      {meeting.faqs && meeting.faqs.length > 0 && (
                        <Chip
                          icon={<QuestionAnswerIcon />}
                          label={`${meeting.faqs.length} FAQs`}
                          size="small"
                          sx={{ bgcolor: 'secondary.main', color: 'white' }}
                        />
                      )}
                      {meeting.email_draft && (
                        <Chip
                          icon={<EmailIcon />}
                          label="Email Draft"
                          size="small"
                          sx={{ bgcolor: 'success.main', color: 'white' }}
                        />
                      )}
                    </Box>
                  </Box>
                  <Button
                    variant="outlined"
                    onClick={() => handleExpand(meeting.id)}
                    endIcon={<ExpandMoreIcon />}
                    sx={{
                      transform: expandedMeeting === meeting.id ? 'rotate(180deg)' : 'rotate(0deg)',
                      transition: 'transform 0.3s',
                    }}
                  >
                    {expandedMeeting === meeting.id ? 'Hide' : 'View Details'}
                  </Button>
                </Box>

                {expandedMeeting === meeting.id && (
                  <Box sx={{ mt: 2 }}>
                    <Divider sx={{ mb: 2 }} />

                    {/* MOM Section */}
                    {meeting.mom && (
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
                            <Paper sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, border: '1px solid', borderColor: 'secondary.light' }}>
                              <Typography variant="body2" sx={{ lineHeight: 1.7, color: 'text.primary' }}>
                                {meeting.mom.summary || 'No summary available'}
                              </Typography>
                            </Paper>
                          </Box>

                          {meeting.mom.decisions && meeting.mom.decisions.length > 0 && (
                            <Box sx={{ mb: 2 }}>
                              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                                Decisions
                              </Typography>
                              {meeting.mom.decisions.map((decision, idx) => (
                                <Paper key={idx} sx={{ p: 1.5, mb: 1, bgcolor: 'background.paper', borderRadius: 2, borderLeft: '3px solid', borderLeftColor: 'primary.light' }}>
                                  <Typography variant="body2" sx={{ fontWeight: 500, color: 'text.primary' }}>
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

                          {meeting.mom.action_items && meeting.mom.action_items.length > 0 && (
                            <Box>
                              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                                Action Items
                              </Typography>
                              {meeting.mom.action_items.map((item, idx) => (
                                <Paper key={idx} sx={{ p: 1.5, mb: 1, bgcolor: 'background.paper', borderRadius: 2, borderLeft: '3px solid', borderLeftColor: 'primary.main' }}>
                                  <Typography variant="body2" sx={{ fontWeight: 500, mb: 0.5, color: 'text.primary' }}>
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
                    {meeting.faqs && meeting.faqs.length > 0 && (
                      <Accordion sx={{ mb: 2, bgcolor: 'background.default' }}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <QuestionAnswerIcon sx={{ color: 'secondary.main' }} />
                            <Typography variant="h6" sx={{ fontWeight: 600 }}>
                              FAQs ({meeting.faqs.length})
                            </Typography>
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                          {meeting.faqs.map((faq, idx) => (
                            <Paper key={idx} sx={{ p: 2, mb: 2, bgcolor: 'background.paper', borderRadius: 2, border: '1px solid', borderColor: 'secondary.light' }}>
                              <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'primary.dark', mb: 1 }}>
                                Q: {faq.question || 'No question'}
                              </Typography>
                              <Typography variant="body2" sx={{ lineHeight: 1.7, color: 'text.primary' }}>
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
                    {meeting.email_draft && (
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
                          <Paper sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, border: '1px solid', borderColor: 'secondary.light' }}>
                            <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', lineHeight: 1.7, color: 'text.primary' }}>
                              To: {meeting.email_draft.to && meeting.email_draft.to.length > 0 ? meeting.email_draft.to.join(', ') : 'N/A'}
                              {meeting.email_draft.cc && meeting.email_draft.cc.length > 0 && (
                                <>
                                  {'\n'}CC: {meeting.email_draft.cc.join(', ')}
                                </>
                              )}
                              {'\n'}Subject: {meeting.email_draft.subject || 'No Subject'}
                              {'\n\n'}{meeting.email_draft.body || 'No body content'}
                            </Typography>
                          </Paper>
                        </AccordionDetails>
                      </Accordion>
                    )}

                    {/* Transcript Section */}
                    {(meeting.full_transcript || meeting.transcript) && (
                      <Accordion sx={{ bgcolor: 'background.default' }}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            Full Transcript
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Paper sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, maxHeight: 400, overflow: 'auto', border: '1px solid', borderColor: 'secondary.light' }}>
                            <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', lineHeight: 1.7, color: 'text.primary' }}>
                              {meeting.full_transcript || meeting.transcript || 'No transcript available'}
                            </Typography>
                          </Paper>
                        </AccordionDetails>
                      </Accordion>
                    )}
                  </Box>
                )}
              </CardContent>
            </Card>
          ))}
        </Box>
      )}
    </Box>
  )
}

export default OldMeetingsView



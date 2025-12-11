import React, { useState, useEffect } from 'react'
import {
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Button,
  List,
  ListItem,
  ListItemText,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import LinkIcon from '@mui/icons-material/Link'
import EmailIcon from '@mui/icons-material/Email'
import GroupsIcon from '@mui/icons-material/Groups'
import { aiAPI, emailAPI, teamsAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const CrossPlatformCorrelation = ({ emails: providedEmails = null, teamsMessages: providedTeamsMessages = null }) => {
  const { mode } = useTheme()
  const [correlations, setCorrelations] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadCorrelations = async () => {
    setLoading(true)
    setError(null)
    try {
      let emails = providedEmails
      let teamsMessages = providedTeamsMessages
      
      // Only fetch if not provided as props
      if (!emails || !teamsMessages) {
        const [emailsResponse, teamsResponse] = await Promise.all([
          providedEmails ? Promise.resolve({ data: { emails: providedEmails } }) : emailAPI.getInbox(20, false).catch(() => ({ data: { emails: [] } })),
          providedTeamsMessages ? Promise.resolve({ data: { messages: providedTeamsMessages } }) : teamsAPI.getMessages(20).catch(() => ({ data: { messages: [] } }))
        ])

        emails = emails || emailsResponse.data?.emails || []
        teamsMessages = teamsMessages || teamsResponse.data?.messages || []
      }

      if (emails.length === 0 && teamsMessages.length === 0) {
        setError('No emails or Teams messages available for correlation')
        setLoading(false)
        return
      }

      const response = await aiAPI.correlateCrossPlatform(emails, teamsMessages)
      setCorrelations(response.data)
    } catch (err) {
      console.error('Error loading correlations:', err)
      // Better error handling for network issues
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Request timed out. Please check your connection and try again.')
      } else if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        setError('Network error. Please ensure the backend server is running.')
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to load cross-platform correlations')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCorrelations()
  }, [providedEmails, providedTeamsMessages])

  const cardBackground = mode === 'dark'
    ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)'

  if (loading) {
    return (
      <Card sx={{ background: cardBackground, p: 3 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
          <CircularProgress />
        </Box>
      </Card>
    )
  }

  if (error) {
    return (
      <Card sx={{ background: cardBackground, p: 3 }}>
        <Alert severity="error">{error}</Alert>
        <Button onClick={loadCorrelations} sx={{ mt: 2 }}>Retry</Button>
      </Card>
    )
  }

  if (!correlations || (correlations.correlations?.length === 0 && correlations.related_items?.length === 0)) {
    return (
      <Card sx={{ background: cardBackground, p: 3 }}>
        <Box display="flex" alignItems="center" mb={2}>
          <LinkIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6">Cross-Platform Correlation</Typography>
          <Button onClick={loadCorrelations} size="small" sx={{ ml: 'auto' }}>
            Refresh
          </Button>
        </Box>
        <Typography variant="body2" color="text.secondary">
          No correlations found between emails and Teams messages.
        </Typography>
      </Card>
    )
  }

  return (
    <Card sx={{ background: cardBackground, p: 3 }}>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Box display="flex" alignItems="center">
          <LinkIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6">Cross-Platform Correlation</Typography>
        </Box>
        <Button onClick={loadCorrelations} size="small">Refresh</Button>
      </Box>

      {correlations.correlations && correlations.correlations.length > 0 && (
        <Accordion defaultExpanded sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              Direct Correlations ({correlations.correlations.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <List>
              {correlations.correlations.map((correlation, index) => (
                <React.Fragment key={index}>
                  <ListItem
                    sx={{
                      borderLeft: `4px solid ${
                        correlation.confidence >= 0.7 ? '#4caf50' : correlation.confidence >= 0.5 ? '#ff9800' : '#9e9e9e'
                      }`,
                      bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
                      borderRadius: 1,
                      mb: 1
                    }}
                  >
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                          <EmailIcon fontSize="small" />
                          <Typography variant="subtitle1">Email ↔ Teams</Typography>
                          <Chip
                            label={`${(correlation.confidence * 100).toFixed(0)}% match`}
                            size="small"
                            color={correlation.confidence >= 0.7 ? 'success' : correlation.confidence >= 0.5 ? 'warning' : 'default'}
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            <strong>Topic:</strong> {correlation.topic}
                          </Typography>
                          {correlation.reasoning && (
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, fontStyle: 'italic' }}>
                              {correlation.reasoning}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < correlations.correlations.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}

      {correlations.related_items && correlations.related_items.length > 0 && (
        <Accordion sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              Related Items ({correlations.related_items.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <List>
              {correlations.related_items.map((item, index) => (
                <React.Fragment key={index}>
                  <ListItem
                    sx={{
                      borderLeft: '4px solid #2196f3',
                      bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
                      borderRadius: 1,
                      mb: 1
                    }}
                  >
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                          <LinkIcon fontSize="small" />
                          <Typography variant="subtitle1">{item.topic}</Typography>
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            {item.summary}
                          </Typography>
                          {item.items && item.items.length > 0 && (
                            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
                              {item.items.map((itemId, idx) => (
                                <Chip
                                  key={idx}
                                  label={itemId.includes('email') ? 'Email' : 'Teams'}
                                  size="small"
                                  icon={itemId.includes('email') ? <EmailIcon /> : <GroupsIcon />}
                                />
                              ))}
                            </Box>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < correlations.related_items.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}
    </Card>
  )
}

export default CrossPlatformCorrelation


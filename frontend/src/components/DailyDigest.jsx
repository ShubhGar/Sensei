import React, { useState, useEffect } from 'react'
import {
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Button
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import SummarizeIcon from '@mui/icons-material/Summarize'
import PriorityHighIcon from '@mui/icons-material/PriorityHigh'
import AssignmentIcon from '@mui/icons-material/Assignment'
import WarningIcon from '@mui/icons-material/Warning'
import { aiAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const DailyDigest = () => {
  const { mode } = useTheme()
  const [digest, setDigest] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadDigest = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await aiAPI.getDailyDigest()
      setDigest(response.data)
    } catch (err) {
      console.error('Error loading daily digest:', err)
      // Better error handling for network issues
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Request timed out. Please check your connection and try again.')
      } else if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        setError('Network error. Please ensure the backend server is running.')
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to load daily digest')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDigest()
  }, [])

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
        <Button onClick={loadDigest} sx={{ mt: 2 }}>Retry</Button>
      </Card>
    )
  }

  if (!digest) {
    return null
  }

  return (
    <Card sx={{ background: cardBackground, p: 3 }}>
      <Box display="flex" alignItems="center" mb={2}>
        <SummarizeIcon sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h5" component="h2">
          Daily Digest
        </Typography>
        <Button onClick={loadDigest} size="small" sx={{ ml: 'auto' }}>
          Refresh
        </Button>
      </Box>

      {digest.summary && (
        <Box mb={3}>
          <Typography variant="body1" sx={{ mb: 2, fontStyle: 'italic' }}>
            {digest.summary}
          </Typography>
        </Box>
      )}

      {digest.highlights && digest.highlights.length > 0 && (
        <Box mb={3}>
          <Typography variant="h6" gutterBottom>
            Highlights
          </Typography>
          <List>
            {digest.highlights.map((highlight, index) => (
              <ListItem key={index}>
                <ListItemText primary={highlight} />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {digest.action_items && digest.action_items.length > 0 && (
        <Accordion sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center">
              <AssignmentIcon sx={{ mr: 1 }} />
              <Typography variant="h6">
                Action Items ({digest.action_items.length})
              </Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <List>
              {digest.action_items.map((item, index) => (
                <React.Fragment key={index}>
                  <ListItem>
                    <ListItemText
                      primary={item.item || item.task || 'Action item'}
                      secondary={
                        <Box>
                          {item.source && (
                            <Chip label={item.source} size="small" sx={{ mr: 1 }} />
                          )}
                          {item.priority && (
                            <Chip 
                              label={item.priority} 
                              size="small" 
                              color={item.priority === 'critical' ? 'error' : 'default'}
                            />
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < digest.action_items.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}

      {digest.urgent_items && digest.urgent_items.length > 0 && (
        <Accordion sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center">
              <PriorityHighIcon sx={{ mr: 1, color: 'error.main' }} />
              <Typography variant="h6" color="error">
                Urgent Items ({digest.urgent_items.length})
              </Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <List>
              {digest.urgent_items.map((item, index) => (
                <ListItem key={index}>
                  <ListItemText primary={item} />
                </ListItem>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}

      {digest.dependencies && digest.dependencies.length > 0 && (
        <Accordion sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center">
              <WarningIcon sx={{ mr: 1, color: 'warning.main' }} />
              <Typography variant="h6">
                Dependencies ({digest.dependencies.length})
              </Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <List>
              {digest.dependencies.map((dep, index) => (
                <React.Fragment key={index}>
                  <ListItem>
                    <ListItemText
                      primary={dep.item || 'Dependency'}
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            Waiting on: {dep.waiting_on || 'Unknown'}
                          </Typography>
                          {dep.deadline && (
                            <Typography variant="body2" color="text.secondary">
                              Deadline: {dep.deadline}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < digest.dependencies.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}

      {digest.recommendations && digest.recommendations.length > 0 && (
        <Box mt={3}>
          <Typography variant="h6" gutterBottom>
            Recommendations
          </Typography>
          <List>
            {digest.recommendations.map((rec, index) => (
              <ListItem key={index}>
                <ListItemText primary={rec} />
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Card>
  )
}

export default DailyDigest


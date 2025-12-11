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
  ListItemIcon,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material'
import WarningIcon from '@mui/icons-material/Warning'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { aiAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const DeadlineRisks = () => {
  const { mode } = useTheme()
  const [risks, setRisks] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadRisks = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await aiAPI.predictDeadlineRisks()
      setRisks(response.data)
    } catch (err) {
      console.error('Error loading deadline risks:', err)
      // Better error handling for network issues
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Request timed out. Please check your connection and try again.')
      } else if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        setError('Network error. Please ensure the backend server is running.')
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to load deadline risks')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRisks()
  }, [])

  const cardBackground = mode === 'dark'
    ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)'

  const getRiskColor = (riskLevel) => {
    switch (riskLevel?.toLowerCase()) {
      case 'high':
        return 'error'
      case 'medium':
        return 'warning'
      default:
        return 'default'
    }
  }

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
        <Button onClick={loadRisks} sx={{ mt: 2 }}>Retry</Button>
      </Card>
    )
  }

  if (!risks) {
    return null
  }

  const hasRisks = (risks.at_risk && risks.at_risk.length > 0) || 
                   (risks.warnings && risks.warnings.length > 0)

  if (!hasRisks) {
    return (
      <Card sx={{ background: cardBackground, p: 3 }}>
        <Box display="flex" alignItems="center" mb={2}>
          <WarningIcon sx={{ mr: 1, color: 'success.main' }} />
          <Typography variant="h6">Deadline Risks</Typography>
        </Box>
        <Typography variant="body2" color="text.secondary">
          No deadline risks detected. All items are on track!
        </Typography>
      </Card>
    )
  }

  return (
    <Card sx={{ background: cardBackground, p: 3 }}>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Box display="flex" alignItems="center">
          <WarningIcon sx={{ mr: 1, color: 'warning.main' }} />
          <Typography variant="h6">Deadline Risks</Typography>
        </Box>
        <Button onClick={loadRisks} size="small">Refresh</Button>
      </Box>

      {risks.at_risk && risks.at_risk.length > 0 && (
        <Accordion defaultExpanded sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center" width="100%">
              <Typography variant="h6" color="error" sx={{ flexGrow: 1 }}>
                At Risk ({risks.at_risk.length})
              </Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <List>
              {risks.at_risk.map((risk, index) => (
                <ListItem
                  key={index}
                  sx={{
                    mb: 1,
                    borderLeft: `4px solid ${
                      risk.risk_level === 'high' ? '#f44336' : '#ff9800'
                    }`,
                    bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
                    borderRadius: 1
                  }}
                >
                  <ListItemIcon>
                    <WarningIcon color={getRiskColor(risk.risk_level)} />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="subtitle1">
                          {risk.item || 'Unknown item'}
                        </Typography>
                        <Chip
                          label={risk.risk_level}
                          size="small"
                          color={getRiskColor(risk.risk_level)}
                        />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          {risk.reason}
                        </Typography>
                        {risk.suggested_action && (
                          <Typography variant="body2" color="primary" sx={{ mt: 1 }}>
                            Suggested: {risk.suggested_action}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}

      {risks.warnings && risks.warnings.length > 0 && (
        <Accordion sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center" width="100%">
              <Typography variant="h6" color="warning.main" sx={{ flexGrow: 1 }}>
                Warnings ({risks.warnings.length})
              </Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <List>
              {risks.warnings.map((warning, index) => (
                <ListItem
                  key={index}
                  sx={{
                    mb: 1,
                    borderLeft: '4px solid #ff9800',
                    bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
                    borderRadius: 1
                  }}
                >
                  <ListItemText
                    primary={warning.item || 'Unknown item'}
                    secondary={
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          {warning.warning}
                        </Typography>
                        {warning.deadline && (
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                            Deadline: {warning.deadline}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}

      {risks.recommendations && risks.recommendations.length > 0 && (
        <Box mt={3}>
          <Typography variant="h6" gutterBottom>
            Recommendations
          </Typography>
          <List>
            {risks.recommendations.map((rec, index) => (
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

export default DeadlineRisks


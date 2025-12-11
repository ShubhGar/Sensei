import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  CircularProgress,
  Alert,
  Grid,
  LinearProgress,
  Paper
} from '@mui/material'
import InsightsIcon from '@mui/icons-material/Insights'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import SentimentSatisfiedIcon from '@mui/icons-material/SentimentSatisfied'
import SentimentNeutralIcon from '@mui/icons-material/SentimentNeutral'
import SentimentDissatisfiedIcon from '@mui/icons-material/SentimentDissatisfied'
import { aiAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const MeetingInsights = ({ sessionId }) => {
  const { mode } = useTheme()
  const [insights, setInsights] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (sessionId) {
      loadInsights()
    }
  }, [sessionId])

  const loadInsights = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await aiAPI.getMeetingInsights(sessionId)
      setInsights(response.data)
    } catch (err) {
      setError(err.message || 'Failed to load insights')
    } finally {
      setLoading(false)
    }
  }

  const getSentimentIcon = (sentiment) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
        return <SentimentSatisfiedIcon sx={{ color: 'success.main' }} />
      case 'negative':
        return <SentimentDissatisfiedIcon sx={{ color: 'error.main' }} />
      default:
        return <SentimentNeutralIcon sx={{ color: 'warning.main' }} />
    }
  }

  const getEffectivenessColor = (effectiveness) => {
    switch (effectiveness?.toLowerCase()) {
      case 'high':
        return 'success'
      case 'medium':
        return 'warning'
      case 'low':
        return 'error'
      default:
        return 'default'
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    )
  }

  if (!insights) {
    return null
  }

  return (
    <Card
      sx={{
        background: mode === 'dark'
          ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
          : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)',
        borderLeft: '4px solid',
        borderLeftColor: 'primary.main',
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <InsightsIcon sx={{ color: 'primary.main' }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Meeting Insights
          </Typography>
        </Box>

        <Grid container spacing={2}>
          {/* Sentiment */}
          <Grid item xs={12} md={6}>
            <Paper
              sx={{
                p: 2,
                bgcolor: mode === 'dark' ? 'rgba(38, 166, 154, 0.1)' : 'rgba(0, 150, 136, 0.08)',
                borderRadius: 2,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                {getSentimentIcon(insights.sentiment)}
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Sentiment
                </Typography>
              </Box>
              <Chip
                label={insights.sentiment || 'Neutral'}
                color={insights.sentiment === 'positive' ? 'success' : insights.sentiment === 'negative' ? 'error' : 'default'}
                sx={{ mb: 1 }}
              />
              {insights.sentiment_score !== undefined && (
                <Box>
                  <LinearProgress
                    variant="determinate"
                    value={(insights.sentiment_score || 0) * 100}
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    Score: {(insights.sentiment_score * 100).toFixed(0)}%
                  </Typography>
                </Box>
              )}
            </Paper>
          </Grid>

          {/* Engagement */}
          <Grid item xs={12} md={6}>
            <Paper
              sx={{
                p: 2,
                bgcolor: mode === 'dark' ? 'rgba(38, 166, 154, 0.1)' : 'rgba(0, 150, 136, 0.08)',
                borderRadius: 2,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <TrendingUpIcon sx={{ color: 'primary.main' }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Engagement
                </Typography>
              </Box>
              {insights.engagement_score !== undefined && (
                <Box>
                  <LinearProgress
                    variant="determinate"
                    value={(insights.engagement_score || 0) * 100}
                    color="primary"
                    sx={{ height: 8, borderRadius: 1, mb: 1 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    Score: {(insights.engagement_score * 100).toFixed(0)}%
                  </Typography>
                </Box>
              )}
              {insights.meeting_effectiveness && (
                <Chip
                  label={`Effectiveness: ${insights.meeting_effectiveness}`}
                  color={getEffectivenessColor(insights.meeting_effectiveness)}
                  size="small"
                  sx={{ mt: 1 }}
                />
              )}
            </Paper>
          </Grid>

          {/* Topics */}
          {insights.topics && insights.topics.length > 0 && (
            <Grid item xs={12}>
              <Paper
                sx={{
                  p: 2,
                  bgcolor: mode === 'dark' ? 'rgba(38, 166, 154, 0.1)' : 'rgba(0, 150, 136, 0.08)',
                  borderRadius: 2,
                }}
              >
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Key Topics
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {insights.topics.map((topic, idx) => (
                    <Chip
                      key={idx}
                      label={topic}
                      size="small"
                      sx={{ bgcolor: 'primary.main', color: 'white' }}
                    />
                  ))}
                </Box>
              </Paper>
            </Grid>
          )}

          {/* Key Insights */}
          {insights.key_insights && insights.key_insights.length > 0 && (
            <Grid item xs={12}>
              <Paper
                sx={{
                  p: 2,
                  bgcolor: mode === 'dark' ? 'rgba(38, 166, 154, 0.1)' : 'rgba(0, 150, 136, 0.08)',
                  borderRadius: 2,
                }}
              >
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Key Insights
                </Typography>
                <Box component="ul" sx={{ m: 0, pl: 2 }}>
                  {insights.key_insights.map((insight, idx) => (
                    <li key={idx}>
                      <Typography variant="body2" sx={{ mb: 0.5 }}>
                        {insight}
                      </Typography>
                    </li>
                  ))}
                </Box>
              </Paper>
            </Grid>
          )}

          {/* Recommendations */}
          {insights.recommendations && insights.recommendations.length > 0 && (
            <Grid item xs={12}>
              <Paper
                sx={{
                  p: 2,
                  bgcolor: mode === 'dark' ? 'rgba(255, 152, 0, 0.1)' : 'rgba(255, 152, 0, 0.08)',
                  borderRadius: 2,
                  borderLeft: '3px solid',
                  borderLeftColor: 'warning.main',
                }}
              >
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Recommendations
                </Typography>
                <Box component="ul" sx={{ m: 0, pl: 2 }}>
                  {insights.recommendations.map((rec, idx) => (
                    <li key={idx}>
                      <Typography variant="body2" sx={{ mb: 0.5 }}>
                        {rec}
                      </Typography>
                    </li>
                  ))}
                </Box>
              </Paper>
            </Grid>
          )}
        </Grid>
      </CardContent>
    </Card>
  )
}

export default MeetingInsights


import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Grid,
  Paper,
  Chip,
  Button
} from '@mui/material'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import InsightsIcon from '@mui/icons-material/Insights'
import { aiAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const TrendsView = () => {
  const { mode } = useTheme()
  const [trends, setTrends] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadTrends()
  }, [])

  const loadTrends = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await aiAPI.analyzeTrends(10)
      setTrends(response.data)
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to load trends'
      setError(errorMessage)
      console.error('Error loading trends:', err)
    } finally {
      setLoading(false)
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
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Box sx={{ textAlign: 'center', mt: 2 }}>
          <Button
            variant="contained"
            onClick={loadTrends}
            sx={{
              bgcolor: 'primary.main',
              '&:hover': {
                bgcolor: 'primary.dark',
              },
            }}
          >
            Retry
          </Button>
        </Box>
      </Box>
    )
  }

  if (!trends) {
    return null
  }

  // Check if trends data is empty
  const hasData = 
    (trends.key_themes && trends.key_themes.length > 0) ||
    (trends.trends && trends.trends.length > 0) ||
    (trends.insights && trends.insights.length > 0) ||
    (trends.recommendations && trends.recommendations.length > 0) ||
    trends.action_item_trends ||
    trends.decision_patterns

  if (!hasData) {
    return (
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <TrendingUpIcon sx={{ color: 'primary.main', fontSize: '2rem' }} />
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            Meeting Trends & Analysis
          </Typography>
        </Box>
        <Alert severity="info" sx={{ mb: 2 }}>
          No trends data available. Please ensure you have meetings with minutes of meeting (MOM) data.
        </Alert>
        <Box sx={{ textAlign: 'center', mt: 2 }}>
          <Button
            variant="contained"
            onClick={loadTrends}
            sx={{
              bgcolor: 'primary.main',
              '&:hover': {
                bgcolor: 'primary.dark',
              },
            }}
          >
            Refresh Analysis
          </Button>
        </Box>
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <TrendingUpIcon sx={{ color: 'primary.main', fontSize: '2rem' }} />
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Meeting Trends & Analysis
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Key Themes */}
        {trends.key_themes && trends.key_themes.length > 0 && (
          <Grid item xs={12}>
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
                    Key Themes
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {trends.key_themes.map((theme, idx) => (
                    <Chip
                      key={idx}
                      label={theme}
                      sx={{
                        bgcolor: 'primary.main',
                        color: 'white',
                        fontWeight: 500,
                        fontSize: '0.9rem',
                        py: 2,
                      }}
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Trends */}
        {trends.trends && trends.trends.length > 0 && (
          <Grid item xs={12} md={6}>
            <Card
              sx={{
                background: mode === 'dark'
                  ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
                  : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)',
                borderLeft: '4px solid',
                borderLeftColor: 'secondary.main',
                height: '100%',
              }}
            >
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Trends
                </Typography>
                {trends.trends.map((trend, idx) => (
                  <Paper
                    key={idx}
                    sx={{
                      p: 2,
                      mb: 2,
                      bgcolor: mode === 'dark' ? 'rgba(38, 166, 154, 0.1)' : 'rgba(0, 150, 136, 0.08)',
                      borderRadius: 2,
                    }}
                  >
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                      {trend.trend}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {trend.description}
                    </Typography>
                    <Chip
                      label={`Impact: ${trend.impact || 'medium'}`}
                      size="small"
                      color={trend.impact === 'high' ? 'error' : trend.impact === 'low' ? 'default' : 'warning'}
                    />
                  </Paper>
                ))}
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Insights */}
        {trends.insights && trends.insights.length > 0 && (
          <Grid item xs={12} md={6}>
            <Card
              sx={{
                background: mode === 'dark'
                  ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
                  : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)',
                borderLeft: '4px solid',
                borderLeftColor: 'success.main',
                height: '100%',
              }}
            >
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Insights
                </Typography>
                <Box component="ul" sx={{ m: 0, pl: 2 }}>
                  {trends.insights.map((insight, idx) => (
                    <li key={idx}>
                      <Typography variant="body2" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                        {insight}
                      </Typography>
                    </li>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Recommendations */}
        {trends.recommendations && trends.recommendations.length > 0 && (
          <Grid item xs={12}>
            <Card
              sx={{
                background: mode === 'dark'
                  ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
                  : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)',
                borderLeft: '4px solid',
                borderLeftColor: 'warning.main',
              }}
            >
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Recommendations
                </Typography>
                <Box component="ul" sx={{ m: 0, pl: 2 }}>
                  {trends.recommendations.map((rec, idx) => (
                    <li key={idx}>
                      <Typography variant="body2" sx={{ mb: 1.5, lineHeight: 1.7 }}>
                        {rec}
                      </Typography>
                    </li>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Action Item Trends */}
        {trends.action_item_trends && (
          <Grid item xs={12} md={6}>
            <Card
              sx={{
                background: mode === 'dark'
                  ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
                  : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)',
                borderLeft: '4px solid',
                borderLeftColor: 'info.main',
              }}
            >
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Action Item Trends
                </Typography>
                <Paper
                  sx={{
                    p: 2,
                    bgcolor: mode === 'dark' ? 'rgba(38, 166, 154, 0.1)' : 'rgba(0, 150, 136, 0.08)',
                    borderRadius: 2,
                  }}
                >
                  <Typography variant="body2" sx={{ lineHeight: 1.7 }}>
                    {trends.action_item_trends}
                  </Typography>
                </Paper>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Decision Patterns */}
        {trends.decision_patterns && (
          <Grid item xs={12} md={6}>
            <Card
              sx={{
                background: mode === 'dark'
                  ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
                  : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)',
                borderLeft: '4px solid',
                borderLeftColor: 'info.main',
              }}
            >
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Decision Patterns
                </Typography>
                <Paper
                  sx={{
                    p: 2,
                    bgcolor: mode === 'dark' ? 'rgba(38, 166, 154, 0.1)' : 'rgba(0, 150, 136, 0.08)',
                    borderRadius: 2,
                  }}
                >
                  <Typography variant="body2" sx={{ lineHeight: 1.7 }}>
                    {trends.decision_patterns}
                  </Typography>
                </Paper>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      <Box sx={{ mt: 3, textAlign: 'center' }}>
        <Button
          variant="contained"
          onClick={loadTrends}
          sx={{
            bgcolor: 'primary.main',
            '&:hover': {
              bgcolor: 'primary.dark',
            },
          }}
        >
          Refresh Analysis
        </Button>
      </Box>
    </Box>
  )
}

export default TrendsView


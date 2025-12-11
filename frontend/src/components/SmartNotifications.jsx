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
  Badge,
  Button,
  IconButton
} from '@mui/material'
import NotificationsIcon from '@mui/icons-material/Notifications'
import EmailIcon from '@mui/icons-material/Email'
import GroupsIcon from '@mui/icons-material/Groups'
import AssignmentIcon from '@mui/icons-material/Assignment'
import RefreshIcon from '@mui/icons-material/Refresh'
import { aiAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const SmartNotifications = () => {
  const { mode } = useTheme()
  const [notifications, setNotifications] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadNotifications = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await aiAPI.getSmartNotifications()
      setNotifications(response.data)
    } catch (err) {
      console.error('Error loading smart notifications:', err)
      // Better error handling for network issues
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Request timed out. Please check your connection and try again.')
      } else if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        setError('Network error. Please ensure the backend server is running.')
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to load notifications')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadNotifications()
    // Auto-refresh every 5 minutes
    const interval = setInterval(loadNotifications, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  const cardBackground = mode === 'dark'
    ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)'

  const getIcon = (type) => {
    switch (type) {
      case 'email':
        return <EmailIcon />
      case 'teams':
        return <GroupsIcon />
      case 'todo':
        return <AssignmentIcon />
      default:
        return <NotificationsIcon />
    }
  }

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical':
        return 'error'
      case 'high':
        return 'warning'
      default:
        return 'default'
    }
  }

  if (loading && !notifications) {
    return (
      <Card sx={{ background: cardBackground, p: 3 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={100}>
          <CircularProgress />
        </Box>
      </Card>
    )
  }

  if (error) {
    return (
      <Card sx={{ background: cardBackground, p: 3 }}>
        <Alert severity="error">{error}</Alert>
        <Button onClick={loadNotifications} sx={{ mt: 2 }}>Retry</Button>
      </Card>
    )
  }

  if (!notifications || !notifications.notifications || notifications.notifications.length === 0) {
    return (
      <Card sx={{ background: cardBackground, p: 3 }}>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center">
            <Badge badgeContent={0} color="error">
              <NotificationsIcon sx={{ mr: 1, color: 'primary.main' }} />
            </Badge>
            <Typography variant="h6">Smart Notifications</Typography>
          </Box>
          <IconButton onClick={loadNotifications} size="small">
            <RefreshIcon />
          </IconButton>
        </Box>
        <Typography variant="body2" color="text.secondary">
          No urgent notifications at this time.
        </Typography>
      </Card>
    )
  }

  return (
    <Card sx={{ background: cardBackground, p: 3 }}>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Box display="flex" alignItems="center">
          <Badge badgeContent={notifications.total} color="error">
            <NotificationsIcon sx={{ mr: 1, color: 'primary.main' }} />
          </Badge>
          <Typography variant="h6">Smart Notifications</Typography>
        </Box>
        <IconButton onClick={loadNotifications} size="small">
          <RefreshIcon />
        </IconButton>
      </Box>

      {notifications.summary && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {notifications.summary}
        </Typography>
      )}

      <List>
        {notifications.notifications.map((notif, index) => (
          <ListItem
            key={index}
            sx={{
              mb: 1,
              borderLeft: `4px solid ${
                notif.priority === 'critical' ? '#f44336' : '#ff9800'
              }`,
              bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
              borderRadius: 1
            }}
          >
            <ListItemIcon>
              {getIcon(notif.type)}
            </ListItemIcon>
            <ListItemText
              primary={
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="subtitle1">
                    {notif.item?.subject || notif.item?.title || notif.item?.content?.substring(0, 50) || 'Notification'}
                  </Typography>
                  <Chip
                    label={notif.priority}
                    size="small"
                    color={getPriorityColor(notif.priority)}
                  />
                  {notif.action_required && (
                    <Chip label="Action Required" size="small" color="error" />
                  )}
                </Box>
              }
              secondary={
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    {notif.reason}
                  </Typography>
                  {notif.urgency_score && (
                    <Typography variant="caption" color="text.secondary">
                      Urgency: {(notif.urgency_score * 100).toFixed(0)}%
                    </Typography>
                  )}
                </Box>
              }
            />
          </ListItem>
        ))}
      </List>
    </Card>
  )
}

export default SmartNotifications


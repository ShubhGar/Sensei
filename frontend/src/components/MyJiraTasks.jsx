import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Tooltip,
  LinearProgress,
  Stack
} from '@mui/material'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import BugReportIcon from '@mui/icons-material/BugReport'
import TaskIcon from '@mui/icons-material/Task'
import BookIcon from '@mui/icons-material/Book'
import RefreshIcon from '@mui/icons-material/Refresh'
import PriorityHighIcon from '@mui/icons-material/PriorityHigh'
import ScheduleIcon from '@mui/icons-material/Schedule'
import { aiAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const MyJiraTasks = () => {
  const { mode } = useTheme()
  const [issues, setIssues] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  const fetchIssues = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await aiAPI.getMyJiraIssues(statusFilter || null, 100)
      setIssues(response.data.issues || [])
    } catch (err) {
      console.error('Error fetching JIRA issues:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch JIRA issues')
      setIssues([])
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchIssues()
  }, [statusFilter])

  const handleRefresh = () => {
    setRefreshing(true)
    fetchIssues()
  }

  const getPriorityColor = (priority) => {
    const priorityLower = priority?.toLowerCase() || ''
    if (priorityLower.includes('highest') || priorityLower.includes('critical')) {
      return 'error'
    } else if (priorityLower.includes('high') || priorityLower.includes('urgent')) {
      return 'warning'
    } else if (priorityLower.includes('medium') || priorityLower.includes('normal')) {
      return 'info'
    } else if (priorityLower.includes('low')) {
      return 'success'
    }
    return 'default'
  }

  const getStatusColor = (status) => {
    const statusLower = status?.toLowerCase() || ''
    if (statusLower.includes('done') || statusLower.includes('closed') || statusLower.includes('resolved')) {
      return 'success'
    } else if (statusLower.includes('progress') || statusLower.includes('in progress')) {
      return 'info'
    } else if (statusLower.includes('to do') || statusLower.includes('open')) {
      return 'default'
    } else if (statusLower.includes('blocked') || statusLower.includes('block')) {
      return 'error'
    }
    return 'default'
  }

  const getIssueTypeIcon = (issueType) => {
    const typeLower = issueType?.toLowerCase() || ''
    if (typeLower.includes('bug')) {
      return <BugReportIcon fontSize="small" />
    } else if (typeLower.includes('story')) {
      return <BookIcon fontSize="small" />
    } else {
      return <TaskIcon fontSize="small" />
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      })
    } catch {
      return dateString
    }
  }

  const getDaysUntilDue = (dueDate) => {
    if (!dueDate) return null
    try {
      const due = new Date(dueDate)
      const now = new Date()
      const diffTime = due - now
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      return diffDays
    } catch {
      return null
    }
  }

  const getUrgencyBadge = (issue) => {
    const urgencyScore = issue.urgency_score || 0
    const daysUntilDue = getDaysUntilDue(issue.due_date)
    
    if (daysUntilDue !== null && daysUntilDue < 0) {
      return <Chip label="OVERDUE" size="small" color="error" sx={{ fontWeight: 'bold' }} />
    } else if (daysUntilDue !== null && daysUntilDue === 0) {
      return <Chip label="Due Today" size="small" color="error" />
    } else if (daysUntilDue !== null && daysUntilDue <= 1) {
      return <Chip label="Due Tomorrow" size="small" color="warning" />
    } else if (urgencyScore >= 70) {
      return <Chip label="High Urgency" size="small" color="warning" />
    } else if (urgencyScore >= 40) {
      return <Chip label="Medium Urgency" size="small" color="info" />
    }
    return null
  }

  if (loading && !refreshing) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h4" component="h1" gutterBottom>
              My JIRA Tasks
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel>Filter by Status</InputLabel>
                <Select
                  value={statusFilter}
                  label="Filter by Status"
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <MenuItem value="">All Statuses</MenuItem>
                  <MenuItem value="To Do">To Do</MenuItem>
                  <MenuItem value="In Progress">In Progress</MenuItem>
                  <MenuItem value="In Review">In Review</MenuItem>
                  <MenuItem value="Done">Done</MenuItem>
                </Select>
              </FormControl>
              <Tooltip title="Refresh">
                <IconButton onClick={handleRefresh} disabled={refreshing}>
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {refreshing && <LinearProgress sx={{ mb: 2 }} />}

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {!loading && issues.length === 0 && !error && (
            <Alert severity="info">
              No JIRA issues found. You're all caught up! 🎉
            </Alert>
          )}

          {issues.length > 0 && (
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Issue</strong></TableCell>
                    <TableCell><strong>Summary</strong></TableCell>
                    <TableCell><strong>Status</strong></TableCell>
                    <TableCell><strong>Priority</strong></TableCell>
                    <TableCell><strong>Urgency</strong></TableCell>
                    <TableCell><strong>Due Date</strong></TableCell>
                    <TableCell><strong>Updated</strong></TableCell>
                    <TableCell><strong>Actions</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {issues.map((issue) => {
                    const daysUntilDue = getDaysUntilDue(issue.due_date)
                    return (
                      <TableRow 
                        key={issue.key}
                        sx={{
                          '&:hover': {
                            backgroundColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.04)'
                          },
                          backgroundColor: issue.urgency_score >= 70 
                            ? (mode === 'dark' ? 'rgba(244, 67, 54, 0.1)' : 'rgba(244, 67, 54, 0.05)')
                            : 'transparent'
                        }}
                      >
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {getIssueTypeIcon(issue.issue_type)}
                            <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                              {issue.key}
                            </Typography>
                            <Chip 
                              label={issue.project.key} 
                              size="small" 
                              variant="outlined"
                              sx={{ fontSize: '0.7rem' }}
                            />
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ maxWidth: '400px' }}>
                            {issue.summary}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={issue.status} 
                            size="small" 
                            color={getStatusColor(issue.status)}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip 
                            icon={<PriorityHighIcon />}
                            label={issue.priority || 'Unprioritized'} 
                            size="small" 
                            color={getPriorityColor(issue.priority)}
                          />
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                            {getUrgencyBadge(issue)}
                            {issue.urgency_score !== undefined && (
                              <Typography variant="caption" color="text.secondary">
                                Score: {Math.round(issue.urgency_score)}
                              </Typography>
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          {issue.due_date ? (
                            <Box>
                              <Typography variant="body2">
                                {formatDate(issue.due_date)}
                              </Typography>
                              {daysUntilDue !== null && (
                                <Typography 
                                  variant="caption" 
                                  color={daysUntilDue < 0 ? 'error' : daysUntilDue <= 1 ? 'warning' : 'text.secondary'}
                                  sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
                                >
                                  <ScheduleIcon fontSize="inherit" />
                                  {daysUntilDue < 0 
                                    ? `${Math.abs(daysUntilDue)} days overdue`
                                    : daysUntilDue === 0
                                    ? 'Due today'
                                    : `${daysUntilDue} days left`
                                  }
                                </Typography>
                              )}
                            </Box>
                          ) : (
                            <Typography variant="body2" color="text.secondary">
                              No due date
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {formatDate(issue.updated)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Tooltip title="Open in JIRA">
                            <IconButton 
                              size="small" 
                              onClick={() => window.open(issue.url, '_blank')}
                              color="primary"
                            >
                              <OpenInNewIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {issues.length > 0 && (
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                Showing {issues.length} issue{issues.length !== 1 ? 's' : ''} sorted by urgency and priority
              </Typography>
              <Stack direction="row" spacing={1}>
                <Chip 
                  label={`High Urgency: ${issues.filter(i => i.urgency_score >= 70).length}`} 
                  size="small" 
                  color="error" 
                  variant="outlined"
                />
                <Chip 
                  label={`Medium Urgency: ${issues.filter(i => i.urgency_score >= 40 && i.urgency_score < 70).length}`} 
                  size="small" 
                  color="warning" 
                  variant="outlined"
                />
                <Chip 
                  label={`Low Urgency: ${issues.filter(i => i.urgency_score < 40).length}`} 
                  size="small" 
                  color="info" 
                  variant="outlined"
                />
              </Stack>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  )
}

export default MyJiraTasks


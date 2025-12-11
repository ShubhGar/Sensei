import React, { useState, useEffect } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Chip,
  List,
  ListItem,
  ListItemText
} from '@mui/material'
import CodeIcon from '@mui/icons-material/Code'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import RefreshIcon from '@mui/icons-material/Refresh'
import { aiAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const JiraConversionDialog = ({ open, onClose, initialText = '' }) => {
  const { mode } = useTheme()
  const [inputText, setInputText] = useState('')
  const [jiraIssueType, setJiraIssueType] = useState('Task')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [jiraResult, setJiraResult] = useState(null)
  const [projectKey, setProjectKey] = useState('')
  const [creatingIssue, setCreatingIssue] = useState(false)
  const [createdIssue, setCreatedIssue] = useState(null)
  const [availableProjects, setAvailableProjects] = useState([])
  const [loadingProjects, setLoadingProjects] = useState(false)

  const cardBackground = mode === 'dark'
    ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)'

  // Load available projects when dialog opens
  const loadProjects = async () => {
    setLoadingProjects(true)
    try {
      const response = await aiAPI.getJiraProjects()
      setAvailableProjects(response.data.projects || [])
    } catch (err) {
      // Silently fail - user can still enter project key manually
      console.error('Failed to load JIRA projects:', err)
    } finally {
      setLoadingProjects(false)
    }
  }

  // Update input text when dialog opens or initialText changes
  useEffect(() => {
    if (open) {
      setInputText(initialText || '')
      setJiraResult(null)
      setError(null)
      setCreatedIssue(null)
      setProjectKey('')
      loadProjects()
    }
  }, [open, initialText])

  const handleConvertToJira = async () => {
    if (!inputText.trim()) {
      setError('Please enter text to convert')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await aiAPI.convertToJira(inputText, jiraIssueType)
      setJiraResult(response.data)
    } catch (err) {
      setError('Failed to convert to Jira: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleCreateJiraIssue = async () => {
    if (!jiraResult) {
      setError('Please convert to JIRA format first')
      return
    }
    if (!projectKey.trim()) {
      setError('Please enter a project key')
      return
    }
    
    setCreatingIssue(true)
    setError(null)
    try {
      const labels = jiraResult.labels && jiraResult.labels.length > 0 
        ? jiraResult.labels.join(',') 
        : null
      
      const response = await aiAPI.createJiraIssue(
        projectKey.trim(),
        jiraResult.title,
        jiraResult.description,
        jiraResult.issue_type || jiraIssueType,
        jiraResult.priority || null,
        labels,
        null // assignee - can be added later
      )
      
      setCreatedIssue(response.data)
    } catch (err) {
      setError('Failed to create JIRA issue: ' + (err.response?.data?.detail || err.message))
    } finally {
      setCreatingIssue(false)
    }
  }

  const handleClose = () => {
    setJiraResult(null)
    setError(null)
    setCreatedIssue(null)
    setProjectKey('')
    onClose()
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          background: cardBackground,
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CodeIcon />
          Convert to JIRA
        </Box>
      </DialogTitle>
      <DialogContent sx={{ mt: 2 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <TextField
          fullWidth
          multiline
          rows={6}
          label="Text to Convert"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Enter text to convert to Jira issue format..."
          variant="outlined"
          sx={{ mb: 2 }}
        />
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Issue Type</InputLabel>
          <Select
            value={jiraIssueType}
            onChange={(e) => setJiraIssueType(e.target.value)}
            label="Issue Type"
          >
            <MenuItem value="Task">Task</MenuItem>
            <MenuItem value="Bug">Bug</MenuItem>
            <MenuItem value="Story">Story</MenuItem>
            <MenuItem value="Epic">Epic</MenuItem>
            <MenuItem value="Subtask">Subtask</MenuItem>
          </Select>
        </FormControl>
        <Button
          variant="contained"
          onClick={handleConvertToJira}
          disabled={loading || !inputText.trim()}
          fullWidth
          startIcon={loading ? <CircularProgress size={16} /> : <CodeIcon />}
        >
          {loading ? 'Converting...' : 'Convert to Jira'}
        </Button>

        {jiraResult && (
          <Box sx={{ mt: 3, p: 2, bgcolor: 'background.default', borderRadius: 2 }}>
            <Typography variant="h6" gutterBottom>Jira Issue</Typography>
            <TextField
              fullWidth
              label="Title"
              value={jiraResult.title}
              variant="outlined"
              sx={{ mb: 2 }}
              InputProps={{ readOnly: true }}
            />
            <TextField
              fullWidth
              multiline
              rows={8}
              label="Description"
              value={jiraResult.description}
              variant="outlined"
              sx={{ mb: 2 }}
              InputProps={{ readOnly: true }}
            />
            {jiraResult.priority && (
              <Chip label={`Priority: ${jiraResult.priority}`} sx={{ mr: 1, mb: 1 }} />
            )}
            {jiraResult.labels && jiraResult.labels.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" mb={1}>Labels:</Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {jiraResult.labels.map((label, idx) => (
                    <Chip key={idx} label={label} size="small" />
                  ))}
                </Box>
              </Box>
            )}
            {jiraResult.acceptance_criteria && jiraResult.acceptance_criteria.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" mb={1}>Acceptance Criteria:</Typography>
                <List>
                  {jiraResult.acceptance_criteria.map((criterion, idx) => (
                    <ListItem key={idx}>
                      <ListItemText primary={criterion} />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
            
            {!createdIssue && (
              <Box sx={{ mt: 3, p: 2, bgcolor: 'background.paper', borderRadius: 2, border: '1px solid', borderColor: 'primary.main' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    Create JIRA Issue
                  </Typography>
                  <Button
                    size="small"
                    onClick={loadProjects}
                    disabled={loadingProjects}
                    startIcon={loadingProjects ? <CircularProgress size={14} /> : <RefreshIcon />}
                  >
                    {loadingProjects ? 'Loading...' : 'Refresh Projects'}
                  </Button>
                </Box>
                {availableProjects.length > 0 ? (
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>Project</InputLabel>
                    <Select
                      value={projectKey}
                      onChange={(e) => setProjectKey(e.target.value)}
                      label="Project"
                    >
                      {availableProjects.map((project) => (
                        <MenuItem key={project.key} value={project.key}>
                          {project.name} ({project.key})
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                ) : (
                  <TextField
                    fullWidth
                    label="Project Key"
                    value={projectKey}
                    onChange={(e) => setProjectKey(e.target.value.toUpperCase())}
                    placeholder="e.g., PROJ, INFPE"
                    variant="outlined"
                    sx={{ mb: 2 }}
                    helperText="Enter the JIRA project key. Make sure you have permission to create issues in this project."
                  />
                )}
                <Button
                  variant="contained"
                  color="success"
                  onClick={handleCreateJiraIssue}
                  disabled={creatingIssue || !projectKey.trim() || !jiraResult}
                  fullWidth
                  startIcon={creatingIssue ? <CircularProgress size={16} /> : <CheckCircleIcon />}
                >
                  {creatingIssue ? 'Creating Issue...' : 'Create JIRA Issue'}
                </Button>
              </Box>
            )}
            
            {createdIssue && (
              <Box sx={{ mt: 3, p: 2, bgcolor: 'success.light', borderRadius: 2, border: '2px solid', borderColor: 'success.main' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <CheckCircleIcon sx={{ color: 'success.main', fontSize: 28 }} />
                  <Typography variant="h6" sx={{ color: 'success.main', fontWeight: 600 }}>
                    Issue Created Successfully!
                  </Typography>
                </Box>
                <Typography variant="body1" sx={{ mb: 1 }}>
                  <strong>Issue Key:</strong> {createdIssue.issue_key}
                </Typography>
                <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
                  {createdIssue.message}
                </Typography>
                {createdIssue.issue_url && (
                  <Button
                    variant="contained"
                    color="success"
                    href={createdIssue.issue_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    startIcon={<OpenInNewIcon />}
                  >
                    Open in JIRA
                  </Button>
                )}
              </Box>
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={handleClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default JiraConversionDialog


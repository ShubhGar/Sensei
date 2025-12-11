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
import { aiAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const JiraConversionDialog = ({ open, onClose, initialText = '' }) => {
  const { mode } = useTheme()
  const [inputText, setInputText] = useState('')
  const [jiraIssueType, setJiraIssueType] = useState('Task')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [jiraResult, setJiraResult] = useState(null)

  const cardBackground = mode === 'dark'
    ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)'

  // Update input text when dialog opens or initialText changes
  useEffect(() => {
    if (open) {
      setInputText(initialText || '')
      setJiraResult(null)
      setError(null)
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

  const handleClose = () => {
    setJiraResult(null)
    setError(null)
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
              <Box>
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


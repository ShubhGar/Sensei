import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Tabs,
  Tab,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Chip,
  List,
  ListItem,
  ListItemText,
  Divider
} from '@mui/material'
import CodeIcon from '@mui/icons-material/Code'
import ArticleIcon from '@mui/icons-material/Article'
import FormatColorTextIcon from '@mui/icons-material/FormatColorText'
import { aiAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const UtilityTools = ({ open, onClose, initialText = '', initialTool = 'jira' }) => {
  const { mode } = useTheme()
  const [activeTab, setActiveTab] = useState(initialTool)
  const [inputText, setInputText] = useState(initialText)
  const [jiraIssueType, setJiraIssueType] = useState('Task')
  const [confluencePageType, setConfluencePageType] = useState('Documentation')
  const [targetAudience, setTargetAudience] = useState('colleagues')
  const [desiredTone, setDesiredTone] = useState('professional')
  const [context, setContext] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [jiraResult, setJiraResult] = useState(null)
  const [confluenceResult, setConfluenceResult] = useState(null)
  const [toneResult, setToneResult] = useState(null)

  const cardBackground = mode === 'dark'
    ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)'

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

  const handleConvertToConfluence = async () => {
    if (!inputText.trim()) {
      setError('Please enter text to convert')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await aiAPI.convertToConfluence(inputText, confluencePageType)
      setConfluenceResult(response.data)
    } catch (err) {
      setError('Failed to convert to Confluence: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleOptimizeTone = async () => {
    if (!inputText.trim()) {
      setError('Please enter text to optimize')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await aiAPI.optimizeTone(inputText, targetAudience, desiredTone, context || null)
      setToneResult(response.data)
    } catch (err) {
      setError('Failed to optimize tone: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue)
    setError(null)
    setJiraResult(null)
    setConfluenceResult(null)
    setToneResult(null)
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
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
        Utility Tools
      </DialogTitle>
      <DialogContent sx={{ mt: 2 }}>
        <Tabs value={activeTab} onChange={handleTabChange} sx={{ mb: 3 }}>
          <Tab icon={<CodeIcon />} iconPosition="start" label="Jira Converter" value="jira" />
          <Tab icon={<ArticleIcon />} iconPosition="start" label="Confluence Converter" value="confluence" />
          <Tab icon={<FormatColorTextIcon />} iconPosition="start" label="Tone Optimizer" value="tone" />
        </Tabs>

        {error && (
          <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Jira Converter Tab */}
        {activeTab === 'jira' && (
          <Box>
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
          </Box>
        )}

        {/* Confluence Converter Tab */}
        {activeTab === 'confluence' && (
          <Box>
            <TextField
              fullWidth
              multiline
              rows={6}
              label="Text to Convert"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Enter text to convert to Confluence page format..."
              variant="outlined"
              sx={{ mb: 2 }}
            />
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Page Type</InputLabel>
              <Select
                value={confluencePageType}
                onChange={(e) => setConfluencePageType(e.target.value)}
                label="Page Type"
              >
                <MenuItem value="Documentation">Documentation</MenuItem>
                <MenuItem value="Meeting Notes">Meeting Notes</MenuItem>
                <MenuItem value="Requirements">Requirements</MenuItem>
                <MenuItem value="Design Doc">Design Doc</MenuItem>
                <MenuItem value="Blog Post">Blog Post</MenuItem>
              </Select>
            </FormControl>
            <Button
              variant="contained"
              onClick={handleConvertToConfluence}
              disabled={loading || !inputText.trim()}
              fullWidth
              startIcon={loading ? <CircularProgress size={16} /> : <ArticleIcon />}
            >
              {loading ? 'Converting...' : 'Convert to Confluence'}
            </Button>

            {confluenceResult && (
              <Box sx={{ mt: 3, p: 2, bgcolor: 'background.default', borderRadius: 2 }}>
                <Typography variant="h6" gutterBottom>Confluence Page</Typography>
                <TextField
                  fullWidth
                  label="Title"
                  value={confluenceResult.title}
                  variant="outlined"
                  sx={{ mb: 2 }}
                  InputProps={{ readOnly: true }}
                />
                <TextField
                  fullWidth
                  multiline
                  rows={10}
                  label="Content"
                  value={confluenceResult.content}
                  variant="outlined"
                  sx={{ mb: 2 }}
                  InputProps={{ readOnly: true }}
                />
                {confluenceResult.labels && confluenceResult.labels.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" mb={1}>Labels:</Typography>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {confluenceResult.labels.map((label, idx) => (
                        <Chip key={idx} label={label} size="small" />
                      ))}
                    </Box>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        )}

        {/* Tone Optimizer Tab */}
        {activeTab === 'tone' && (
          <Box>
            <TextField
              fullWidth
              multiline
              rows={6}
              label="Text to Optimize"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Enter text to optimize for tone..."
              variant="outlined"
              sx={{ mb: 2 }}
            />
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <FormControl fullWidth>
                <InputLabel>Target Audience</InputLabel>
                <Select
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  label="Target Audience"
                >
                  <MenuItem value="colleagues">Colleagues</MenuItem>
                  <MenuItem value="executives">Executives</MenuItem>
                  <MenuItem value="clients">Clients</MenuItem>
                  <MenuItem value="team members">Team Members</MenuItem>
                  <MenuItem value="stakeholders">Stakeholders</MenuItem>
                </Select>
              </FormControl>
              <FormControl fullWidth>
                <InputLabel>Desired Tone</InputLabel>
                <Select
                  value={desiredTone}
                  onChange={(e) => setDesiredTone(e.target.value)}
                  label="Desired Tone"
                >
                  <MenuItem value="professional">Professional</MenuItem>
                  <MenuItem value="casual">Casual</MenuItem>
                  <MenuItem value="empathetic">Empathetic</MenuItem>
                  <MenuItem value="concise">Concise</MenuItem>
                  <MenuItem value="friendly">Friendly</MenuItem>
                  <MenuItem value="formal">Formal</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <TextField
              fullWidth
              multiline
              rows={2}
              label="Additional Context (Optional)"
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Any additional context for tone optimization..."
              variant="outlined"
              sx={{ mb: 2 }}
            />
            <Button
              variant="contained"
              onClick={handleOptimizeTone}
              disabled={loading || !inputText.trim()}
              fullWidth
              startIcon={loading ? <CircularProgress size={16} /> : <FormatColorTextIcon />}
            >
              {loading ? 'Optimizing...' : 'Optimize Tone'}
            </Button>

            {toneResult && (
              <Box sx={{ mt: 3, p: 2, bgcolor: 'background.default', borderRadius: 2 }}>
                <Typography variant="h6" gutterBottom>Optimized Text</Typography>
                <TextField
                  fullWidth
                  multiline
                  rows={8}
                  value={toneResult.optimized_text}
                  variant="outlined"
                  sx={{ mb: 2 }}
                  InputProps={{ readOnly: true }}
                />
                <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                  <Chip label={`Tone: ${toneResult.tone}`} />
                  {toneResult.tone_score && (
                    <Chip label={`Score: ${(toneResult.tone_score * 100).toFixed(0)}%`} />
                  )}
                </Box>
                {toneResult.changes && toneResult.changes.length > 0 && (
                  <Box>
                    <Typography variant="subtitle2" mb={1}>Changes Made:</Typography>
                    <List>
                      {toneResult.changes.map((change, idx) => (
                        <ListItem key={idx} sx={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                          <Typography variant="body2" color="text.secondary">
                            <strong>Original:</strong> {change.original}
                          </Typography>
                          <Typography variant="body2" color="primary">
                            <strong>Optimized:</strong> {change.optimized}
                          </Typography>
                          {change.reason && (
                            <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                              {change.reason}
                            </Typography>
                          )}
                          {idx < toneResult.changes.length - 1 && <Divider sx={{ width: '100%', mt: 1 }} />}
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
                {toneResult.recommendations && toneResult.recommendations.length > 0 && (
                  <Box mt={2}>
                    <Typography variant="subtitle2" mb={1}>Recommendations:</Typography>
                    <List>
                      {toneResult.recommendations.map((rec, idx) => (
                        <ListItem key={idx}>
                          <ListItemText primary={rec} />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default UtilityTools


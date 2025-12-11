import React, { useState, useRef, useEffect } from 'react'
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  Avatar,
  CircularProgress,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Menu,
  MenuItem
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import SmartToyIcon from '@mui/icons-material/SmartToy'
import PersonIcon from '@mui/icons-material/Person'
import EmailIcon from '@mui/icons-material/Email'
import MessageIcon from '@mui/icons-material/Message'
import { aiAPI, emailAPI, teamsAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const AIChatAssistant = () => {
  const { mode } = useTheme()
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m your AI assistant. I can help you understand your meetings, emails, and work communications. What would you like to know?',
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sendEmailDialog, setSendEmailDialog] = useState({ open: false, content: '', messageIndex: -1 })
  const [sendMessageDialog, setSendMessageDialog] = useState({ open: false, content: '', messageIndex: -1 })
  const [sendMenuAnchor, setSendMenuAnchor] = useState(null)
  const [sendMenuMessageIndex, setSendMenuMessageIndex] = useState(-1)
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState(null)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await aiAPI.chat(input)
      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        confidence: response.data.confidence,
        sources: response.data.sources || [],
        followUpQuestions: response.data.follow_up_questions || [],
        actionItems: response.data.action_items || [],
        timestamp: new Date()
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        error: true,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSendMenuOpen = (event, messageIndex) => {
    setSendMenuAnchor(event.currentTarget)
    setSendMenuMessageIndex(messageIndex)
  }

  const handleSendMenuClose = () => {
    setSendMenuAnchor(null)
    setSendMenuMessageIndex(-1)
  }

  const handleOpenEmailDialog = (messageIndex) => {
    const message = messages[messageIndex]
    setSendEmailDialog({
      open: true,
      content: message.content,
      messageIndex
    })
    handleSendMenuClose()
  }

  const handleOpenMessageDialog = (messageIndex) => {
    const message = messages[messageIndex]
    setSendMessageDialog({
      open: true,
      content: message.content,
      messageIndex
    })
    handleSendMenuClose()
  }

  const handleSendEmail = async (emailData) => {
    setSending(true)
    setSendError(null)
    try {
      await emailAPI.sendEmail(
        emailData.to,
        emailData.subject,
        emailData.body,
        'text',
        emailData.cc,
        emailData.bcc,
        emailData.importance || 'normal'
      )
      setSendEmailDialog({ open: false, content: '', messageIndex: -1 })
      // Show success message
      const successMessage = {
        role: 'assistant',
        content: `Email sent successfully to ${emailData.to.join(', ')}`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, successMessage])
    } catch (error) {
      setSendError(error.response?.data?.detail || error.message || 'Failed to send email')
    } finally {
      setSending(false)
    }
  }

  const handleSendTeamsMessage = async (messageData) => {
    setSending(true)
    setSendError(null)
    try {
      await teamsAPI.sendMessage(
        messageData.chatId,
        messageData.teamId,
        messageData.channelId,
        messageData.content,
        'text'
      )
      setSendMessageDialog({ open: false, content: '', messageIndex: -1 })
      // Show success message
      const successMessage = {
        role: 'assistant',
        content: 'Teams message sent successfully',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, successMessage])
    } catch (error) {
      setSendError(error.response?.data?.detail || error.message || 'Failed to send message')
    } finally {
      setSending(false)
    }
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Paper
        elevation={0}
        sx={{
          p: 2,
          mb: 2,
          background: mode === 'dark'
            ? 'linear-gradient(135deg, #1E3A3A 0%, #2A3A3A 100%)'
            : 'linear-gradient(135deg, #E8F5E9 0%, #F1F8E9 100%)',
          borderLeft: '4px solid',
          borderLeftColor: 'primary.main',
          borderRadius: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <SmartToyIcon sx={{ color: 'primary.main' }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            AI Assistant
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary">
          Ask me anything about your meetings, emails, or work communications
        </Typography>
      </Paper>

      <Box
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          mb: 2,
          p: 1,
          bgcolor: mode === 'dark' ? 'rgba(0,0,0,0.2)' : 'rgba(0,0,0,0.02)',
          borderRadius: 2,
          minHeight: 300,
          maxHeight: 500,
        }}
      >
        {messages.map((message, idx) => (
          <Box
            key={idx}
            sx={{
              display: 'flex',
              gap: 2,
              mb: 2,
              flexDirection: message.role === 'user' ? 'row-reverse' : 'row',
            }}
          >
            <Avatar
              sx={{
                bgcolor: message.role === 'user' ? 'primary.main' : 'secondary.main',
                width: 32,
                height: 32,
              }}
            >
              {message.role === 'user' ? (
                <PersonIcon fontSize="small" />
              ) : (
                <SmartToyIcon fontSize="small" />
              )}
            </Avatar>
            <Box sx={{ flex: 1 }}>
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  bgcolor: message.role === 'user'
                    ? (mode === 'dark' ? 'rgba(38, 166, 154, 0.2)' : 'rgba(0, 150, 136, 0.1)')
                    : (mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'),
                  borderRadius: 2,
                }}
              >
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {message.content}
                </Typography>
                {message.confidence !== undefined && (
                  <Chip
                    label={`Confidence: ${(message.confidence * 100).toFixed(0)}%`}
                    size="small"
                    sx={{ mt: 1, fontSize: '0.7rem' }}
                  />
                )}
                {message.sources && message.sources.length > 0 && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Sources:
                    </Typography>
                    {message.sources.map((source, i) => (
                      <Chip
                        key={i}
                        label={source}
                        size="small"
                        sx={{ ml: 0.5, mt: 0.5, fontSize: '0.7rem' }}
                      />
                    ))}
                  </Box>
                )}
                {message.followUpQuestions && message.followUpQuestions.length > 0 && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                      Suggested questions:
                    </Typography>
                    {message.followUpQuestions.map((question, i) => (
                      <Button
                        key={i}
                        size="small"
                        variant="outlined"
                        onClick={() => setInput(question)}
                        sx={{ mr: 0.5, mb: 0.5, fontSize: '0.7rem', textTransform: 'none' }}
                      >
                        {question}
                      </Button>
                    ))}
                  </Box>
                )}
                {message.role === 'assistant' && !message.error && (
                  <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
                    <IconButton
                      size="small"
                      onClick={(e) => handleSendMenuOpen(e, idx)}
                      sx={{ fontSize: '0.7rem' }}
                    >
                      <SendIcon fontSize="small" />
                    </IconButton>
                  </Box>
                )}
              </Paper>
            </Box>
          </Box>
        ))}
        {loading && (
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <Avatar sx={{ bgcolor: 'secondary.main', width: 32, height: 32 }}>
              <SmartToyIcon fontSize="small" />
            </Avatar>
            <CircularProgress size={20} sx={{ mt: 1 }} />
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Box>

      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          multiline
          maxRows={4}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask me anything..."
          disabled={loading}
          sx={{
            '& .MuiOutlinedInput-root': {
              bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
            }
          }}
        />
        <IconButton
          color="primary"
          onClick={handleSend}
          disabled={!input.trim() || loading}
          sx={{
            bgcolor: 'primary.main',
            color: 'white',
            '&:hover': {
              bgcolor: 'primary.dark',
            },
            '&:disabled': {
              bgcolor: 'action.disabledBackground',
            }
          }}
        >
          <SendIcon />
        </IconButton>
      </Box>

      {/* Send Menu */}
      <Menu
        anchorEl={sendMenuAnchor}
        open={Boolean(sendMenuAnchor)}
        onClose={handleSendMenuClose}
      >
        <MenuItem onClick={() => handleOpenEmailDialog(sendMenuMessageIndex)}>
          <EmailIcon sx={{ mr: 1 }} fontSize="small" />
          Send as Email
        </MenuItem>
        <MenuItem onClick={() => handleOpenMessageDialog(sendMenuMessageIndex)}>
          <MessageIcon sx={{ mr: 1 }} fontSize="small" />
          Send as Teams Message
        </MenuItem>
      </Menu>

      {/* Send Email Dialog */}
      <SendEmailDialog
        open={sendEmailDialog.open}
        onClose={() => {
          setSendEmailDialog({ open: false, content: '', messageIndex: -1 })
          setSendError(null)
        }}
        content={sendEmailDialog.content}
        onSend={handleSendEmail}
        sending={sending}
        error={sendError}
      />

      {/* Send Teams Message Dialog */}
      <SendMessageDialog
        open={sendMessageDialog.open}
        onClose={() => {
          setSendMessageDialog({ open: false, content: '', messageIndex: -1 })
          setSendError(null)
        }}
        content={sendMessageDialog.content}
        onSend={handleSendTeamsMessage}
        sending={sending}
        error={sendError}
      />
    </Box>
  )
}

// Send Email Dialog Component
const SendEmailDialog = ({ open, onClose, content, onSend, sending, error }) => {
  const [to, setTo] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState(content)
  const [cc, setCc] = useState('')
  const [bcc, setBcc] = useState('')
  const [importance, setImportance] = useState('normal')

  useEffect(() => {
    if (open) {
      setBody(content)
      // Try to extract subject from content (first line or first sentence)
      const firstLine = content.split('\n')[0]
      if (firstLine.length < 100) {
        setSubject(firstLine)
      }
    }
  }, [open, content])

  const handleSubmit = () => {
    const toList = to.split(',').map(email => email.trim()).filter(email => email)
    if (toList.length === 0) {
      return
    }
    onSend({
      to: toList,
      subject: subject || 'AI Generated Response',
      body: body,
      cc: cc ? cc.split(',').map(email => email.trim()).filter(email => email) : null,
      bcc: bcc ? bcc.split(',').map(email => email.trim()).filter(email => email) : null,
      importance
    })
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Send as Email</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <TextField
          fullWidth
          label="To"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          placeholder="email@example.com"
          required
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          label="Subject"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          multiline
          rows={6}
          label="Body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          label="CC (optional)"
          value={cc}
          onChange={(e) => setCc(e.target.value)}
          placeholder="email@example.com"
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          label="BCC (optional)"
          value={bcc}
          onChange={(e) => setBcc(e.target.value)}
          placeholder="email@example.com"
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          select
          label="Importance"
          value={importance}
          onChange={(e) => setImportance(e.target.value)}
          SelectProps={{ native: true }}
        >
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
        </TextField>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={sending}>Cancel</Button>
        <Button onClick={handleSubmit} variant="contained" disabled={sending || !to.trim()}>
          {sending ? 'Sending...' : 'Send Email'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// Send Teams Message Dialog Component
const SendMessageDialog = ({ open, onClose, content, onSend, sending, error }) => {
  const [messageType, setMessageType] = useState('chat') // 'chat' or 'channel'
  const [chatId, setChatId] = useState('')
  const [teamId, setTeamId] = useState('')
  const [channelId, setChannelId] = useState('')
  const [body, setBody] = useState(content)

  useEffect(() => {
    if (open) {
      setBody(content)
    }
  }, [open, content])

  const handleSubmit = () => {
    if (messageType === 'chat') {
      if (!chatId.trim()) return
      onSend({
        chatId: chatId.trim(),
        teamId: null,
        channelId: null,
        content: body
      })
    } else {
      if (!teamId.trim() || !channelId.trim()) return
      onSend({
        chatId: null,
        teamId: teamId.trim(),
        channelId: channelId.trim(),
        content: body
      })
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Send as Teams Message</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <TextField
          fullWidth
          select
          label="Message Type"
          value={messageType}
          onChange={(e) => setMessageType(e.target.value)}
          SelectProps={{ native: true }}
          sx={{ mb: 2 }}
        >
          <option value="chat">Chat Message</option>
          <option value="channel">Channel Message</option>
        </TextField>
        {messageType === 'chat' ? (
          <TextField
            fullWidth
            label="Chat ID"
            value={chatId}
            onChange={(e) => setChatId(e.target.value)}
            placeholder="Enter Teams chat ID"
            required
            sx={{ mb: 2 }}
            helperText="You can find the chat ID from the Teams API or URL"
          />
        ) : (
          <>
            <TextField
              fullWidth
              label="Team ID"
              value={teamId}
              onChange={(e) => setTeamId(e.target.value)}
              placeholder="Enter Teams team ID"
              required
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Channel ID"
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              placeholder="Enter Teams channel ID"
              required
              sx={{ mb: 2 }}
            />
          </>
        )}
        <TextField
          fullWidth
          multiline
          rows={6}
          label="Message"
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={sending}>Cancel</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={sending || (messageType === 'chat' ? !chatId.trim() : !teamId.trim() || !channelId.trim())}
        >
          {sending ? 'Sending...' : 'Send Message'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default AIChatAssistant


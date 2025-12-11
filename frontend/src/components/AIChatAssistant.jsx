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
  Button
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import SmartToyIcon from '@mui/icons-material/SmartToy'
import PersonIcon from '@mui/icons-material/Person'
import { aiAPI } from '../services/api'
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
    </Box>
  )
}

export default AIChatAssistant


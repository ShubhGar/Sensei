import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  CircularProgress,
  Alert,
  Paper,
  ToggleButton,
  ToggleButtonGroup,
  FormControl,
  FormLabel,
  Grid,
  Divider,
  Tabs,
  Tab,
  InputAdornment
} from '@mui/material'
import MicIcon from '@mui/icons-material/Mic'
import SummarizeIcon from '@mui/icons-material/Summarize'
import HistoryIcon from '@mui/icons-material/History'
import { transcriptionAPI, aiAPI, exportAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const TranscriptionView = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { mode } = useTheme()
  const [sessionId, setSessionId] = useState(null)
  const [transcript, setTranscript] = useState('')
  const [fullTranscript, setFullTranscript] = useState('')
  const [editedTranscript, setEditedTranscript] = useState('') // Editable transcript state
  const [hasUserEdited, setHasUserEdited] = useState(false) // Track if user has manually edited
  const [title, setTitle] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [showOptions, setShowOptions] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [mom, setMom] = useState(null)
  const [faqs, setFaqs] = useState([])
  const [emailDraft, setEmailDraft] = useState(null)
  const [risks, setRisks] = useState([])
  const [audioSource, setAudioSource] = useState('user') // 'user', 'system', or 'both'
  const [voiceActivity, setVoiceActivity] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const saveTimeoutRef = useRef(null)
  const wsRef = useRef(null)
  const wsSystemRef = useRef(null) // Separate WebSocket for system audio
  const mediaRecorderRef = useRef(null)
  const audioStreamRef = useRef(null)
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const animationFrameRef = useRef(null)
  
  // Set nav tab based on current route
  const getNavTab = useCallback(() => {
    if (location.pathname === '/transcription') return 'transcription'
    if (location.pathname === '/meetings') return 'meetings'
    return 'transcription'
  }, [location.pathname])
  const [navTab, setNavTab] = useState(() => {
    if (location.pathname === '/transcription') return 'transcription'
    if (location.pathname === '/meetings') return 'meetings'
    return 'transcription'
  })
  
  // Theme-aware card background
  const getCardBackground = () => {
    return mode === 'dark' 
      ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
      : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)'
  }
  
  const getHighlightCardBackground = () => {
    return mode === 'dark'
      ? 'linear-gradient(135deg, #1E1E1E 0%, #1E3A3A 100%)'
      : 'linear-gradient(135deg, #FFFFFF 0%, #E8F5E9 100%)'
  }
  
  const getRiskCardBackground = () => {
    return mode === 'dark'
      ? 'linear-gradient(135deg, #1E1E1E 0%, #3A2A1E 100%)'
      : 'linear-gradient(135deg, #FFFFFF 0%, #FFF3E0 100%)'
  }

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (wsSystemRef.current) {
        wsSystemRef.current.close()
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach(track => track.stop())
      }
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close()
      }
      // Clear save timeout
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [])
  
  // Initialize editedTranscript when fullTranscript changes (but only if user hasn't edited)
  useEffect(() => {
    if (fullTranscript && !hasUserEdited) {
      setEditedTranscript(fullTranscript)
    }
  }, [fullTranscript, hasUserEdited])

  useEffect(() => {
    const currentTab = getNavTab()
    setNavTab(currentTab)
  }, [location.pathname, getNavTab])

  // Voice activity detection using Web Audio API
  const startVoiceActivityDetection = (stream) => {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      const analyser = audioContext.createAnalyser()
      const microphone = audioContext.createMediaStreamSource(stream)
      
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.8
      microphone.connect(analyser)
      
      audioContextRef.current = audioContext
      analyserRef.current = analyser
      
      const dataArray = new Uint8Array(analyser.frequencyBinCount)
      const threshold = 30 // Adjust this value to tune sensitivity
      
      const detectVoice = () => {
        if (!analyserRef.current) return
        
        analyserRef.current.getByteFrequencyData(dataArray)
        
        // Calculate average volume
        let sum = 0
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i]
        }
        const average = sum / dataArray.length
        
        // Check if voice is detected (volume above threshold)
        const isVoiceActive = average > threshold
        setVoiceActivity(isVoiceActive)
        
        if (isRecording) {
          animationFrameRef.current = requestAnimationFrame(detectVoice)
        }
      }
      
      detectVoice()
    } catch (err) {
      console.error('Error setting up voice activity detection:', err)
    }
  }

  const startTranscription = async () => {
    setLoading(true)
    setError(null)
    try {
      // Start transcription session
      const response = await transcriptionAPI.startSession(title || 'Untitled Meeting')
      const newSessionId = response.data.id
      setSessionId(newSessionId)
      setIsRecording(true)
      
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      
      // Connect to user microphone if needed
      if (audioSource === 'user' || audioSource === 'both') {
        // User microphone capture
        // Request microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            channelCount: 1,
            sampleRate: 16000,
            echoCancellation: true,
            noiseSuppression: true
          } 
        })
        audioStreamRef.current = stream
        
        // Start voice activity detection
        startVoiceActivityDetection(stream)
        
        // Connect WebSocket for real-time transcription
        const wsUrl = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://') + `/api/transcribe/ws/${newSessionId}`
        const ws = new WebSocket(wsUrl)
        
        ws.onopen = () => {
          console.log('WebSocket connected (User Microphone)')
          
          // Set up MediaRecorder to capture audio
          const mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
          })
          mediaRecorderRef.current = mediaRecorder
          
          mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
              // Send audio data as binary
              ws.send(event.data)
            }
          }
          
          // Start recording and send chunks every 1 second
          mediaRecorder.start(1000) // 1 second chunks
        }
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            console.log('[User Microphone] WebSocket message received:', data.type, data)
            if (data.type === 'transcript') {
              console.log('[User Microphone] Received transcript:', data.speaker, data.text?.substring(0, 50))
              console.log('[User Microphone] Full transcript length:', data.full_transcript?.length || 0)
              // Use full_transcript from server which is already merged
              if (data.full_transcript) {
                setFullTranscript(data.full_transcript)
                // Only update editedTranscript if user hasn't manually edited
                if (!hasUserEdited) {
                  setEditedTranscript(data.full_transcript)
                }
                console.log('[User Microphone] Updated fullTranscript state')
              }
              // Show latest transcript with speaker label
              if (data.speaker && data.text) {
                setTranscript(`"${data.speaker}": ${data.text}`)
                console.log('[User Microphone] Updated transcript state with speaker')
              } else if (data.text) {
                setTranscript(data.text)
                console.log('[User Microphone] Updated transcript state')
              }
            } else if (data.type === 'error') {
              console.error('[User Microphone] Transcription error:', data.message)
              setError(data.message || 'Transcription service error')
            } else {
              console.log('[User Microphone] Unknown message type:', data.type)
            }
          } catch (err) {
            console.error('Error parsing WebSocket message:', err, event.data)
          }
        }
        
        ws.onerror = (err) => {
          console.error('WebSocket error:', err)
          setError('WebSocket connection error')
        }
        
        ws.onclose = () => {
          console.log('WebSocket closed (User Microphone)')
          if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop()
          }
          if (audioStreamRef.current) {
            audioStreamRef.current.getTracks().forEach(track => track.stop())
          }
          // Stop voice activity detection
          if (animationFrameRef.current) {
            cancelAnimationFrame(animationFrameRef.current)
            animationFrameRef.current = null
          }
          if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
            audioContextRef.current.close()
            audioContextRef.current = null
          }
          analyserRef.current = null
          setVoiceActivity(false)
          if (audioSource === 'user') {
            setIsRecording(false)
          }
        }
        
        wsRef.current = ws
      }
      
      // Connect to system audio if needed
      if (audioSource === 'system' || audioSource === 'both') {
        const wsSystemUrl = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://') + `/api/transcribe/ws-system/${newSessionId}`
        const wsSystem = new WebSocket(wsSystemUrl)
        
        wsSystem.onopen = () => {
          console.log('WebSocket connected (System Audio)')
        }
        
        wsSystem.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            console.log('[System Audio] WebSocket message received:', data.type, data)
            if (data.type === 'transcript') {
              console.log('[System Audio] Received transcript:', data.speaker, data.text?.substring(0, 50))
              console.log('[System Audio] Full transcript length:', data.full_transcript?.length || 0)
              // Use full_transcript from server which is already merged
              if (data.full_transcript) {
                setFullTranscript(data.full_transcript)
                // Only update editedTranscript if user hasn't manually edited
                if (!hasUserEdited) {
                  setEditedTranscript(data.full_transcript)
                }
                console.log('[System Audio] Updated fullTranscript state')
              }
              // Show latest transcript with speaker label
              if (data.speaker && data.text) {
                setTranscript(`"${data.speaker}": ${data.text}`)
                console.log('[System Audio] Updated transcript state with speaker')
              } else if (data.text) {
                setTranscript(data.text)
                console.log('[System Audio] Updated transcript state')
              }
            } else if (data.type === 'error') {
              console.error('[System Audio] Transcription error:', data.message)
              setError(data.message || 'System audio capture error')
            } else {
              console.log('[System Audio] Unknown message type:', data.type)
            }
          } catch (err) {
            console.error('Error parsing WebSocket message:', err, event.data)
          }
        }
        
        wsSystem.onerror = (err) => {
          console.error('WebSocket error (System Audio):', err)
          setError('System audio capture error.')
        }
        
        wsSystem.onclose = () => {
          console.log('WebSocket closed (System Audio)')
          if (audioSource === 'system') {
            setIsRecording(false)
          }
        }
        
        wsSystemRef.current = wsSystem
      }
    } catch (err) {
      if (audioSource === 'user' || audioSource === 'both') {
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          setError('Microphone access denied. Please allow microphone access and try again.')
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
          setError('No microphone found. Please connect a microphone and try again.')
        } else {
          setError('Failed to start transcription: ' + err.message)
        }
      } else {
        setError('Failed to start system audio capture: ' + err.message)
      }
      setIsRecording(false)
    } finally {
      setLoading(false)
    }
  }

  const stopTranscription = async () => {
    if (!sessionId) return
    
    setLoading(true)
    try {
      // Stop media recorder
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
      
      // Stop audio stream
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach(track => track.stop())
        audioStreamRef.current = null
      }
      
      // Stop voice activity detection
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
        animationFrameRef.current = null
      }
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close()
        audioContextRef.current = null
      }
      analyserRef.current = null
      setVoiceActivity(false)
      
      // Close WebSockets
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (wsSystemRef.current) {
        // Send stop message for system audio
        if (wsSystemRef.current.readyState === WebSocket.OPEN) {
          wsSystemRef.current.send(JSON.stringify({ type: 'stop' }))
        }
        wsSystemRef.current.close()
        wsSystemRef.current = null
      }
      
      await transcriptionAPI.stopSession(sessionId)
      setIsRecording(false)
    } catch (err) {
      setError('Failed to stop transcription: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  // Auto-save transcript when edited
  const saveTranscript = async (transcriptText) => {
    if (!sessionId || !transcriptText) return
    
    setIsSaving(true)
    try {
      await transcriptionAPI.updateTranscript(sessionId, transcriptText)
      setFullTranscript(transcriptText)
      console.log('[Transcription] Transcript saved successfully')
    } catch (err) {
      console.error('Failed to save transcript:', err)
      setError('Failed to save transcript: ' + err.message)
    } finally {
      setIsSaving(false)
    }
  }

  // Handle transcript edit with debounced auto-save
  const handleTranscriptChange = (event) => {
    const newValue = event.target.value
    setEditedTranscript(newValue)
    setHasUserEdited(true) // Mark that user has manually edited
    
    // Clear existing timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    
    // Debounce auto-save (save after 2 seconds of no typing)
    saveTimeoutRef.current = setTimeout(() => {
      saveTranscript(newValue)
    }, 2000)
  }

  const generateInsights = async () => {
    if (!sessionId) return
    
    setLoading(true)
    try {
      // Save the edited transcript first if it's different from the stored one
      const transcriptToUse = editedTranscript || fullTranscript || transcript
      if (editedTranscript && editedTranscript !== fullTranscript) {
        await saveTranscript(editedTranscript)
        // Wait a bit for the save to complete
        await new Promise(resolve => setTimeout(resolve, 500))
      }
      
      const response = await aiAPI.processTranscript(sessionId, true, true)
      setMom(response.data.mom)
      setFaqs(response.data.faqs || [])
      setEmailDraft(response.data.email_draft)
      setRisks(response.data.risks || [])
    } catch (err) {
      setError('Failed to generate insights: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const exportDocument = async (format) => {
    if (!sessionId) return
    
    try {
      let response
      let filename
      let mimeType
      
      switch (format) {
        case 'pdf':
          response = await exportAPI.exportPDF(sessionId)
          filename = `meeting_${sessionId}.pdf`
          mimeType = 'application/pdf'
          break
        case 'docx':
          response = await exportAPI.exportDOCX(sessionId)
          filename = `meeting_${sessionId}.docx`
          mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
          break
        case 'json':
          response = await exportAPI.exportJSON(sessionId)
          filename = `meeting_${sessionId}.json`
          mimeType = 'application/json'
          break
        default:
          return
      }
      
      const blob = new Blob([response.data], { type: mimeType })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError('Failed to export: ' + err.message)
    }
  }

  const handleNavChange = (event, newValue) => {
    setNavTab(newValue)
    if (newValue === 'meetings') {
      navigate('/meetings')
    } else if (newValue === 'transcription') {
      navigate('/transcription')
    }
  }

  return (
    <Box>
      {/* Navigation Tabs - Only show after selection is made */}
      {(!showOptions || sessionId || isRecording) && (
        <Box sx={{ mb: 3 }}>
          <Tabs
            value={navTab}
            onChange={handleNavChange}
            sx={{
              borderBottom: 1,
              borderColor: 'divider',
              mb: 3,
              '& .MuiTab-root': {
                textTransform: 'none',
                fontWeight: 600,
                fontSize: '1rem',
                minHeight: 48,
              },
            }}
          >
            <Tab
              icon={<MicIcon />}
              iconPosition="start"
              label="New Transcription"
              value="transcription"
              sx={{
                '&.Mui-selected': {
                  color: 'primary.main',
                },
              }}
            />
            <Tab
              icon={<HistoryIcon />}
              iconPosition="start"
              label="Past Meetings"
              value="meetings"
              sx={{
                '&.Mui-selected': {
                  color: 'primary.main',
                },
              }}
            />
          </Tabs>
        </Box>
      )}

      <Typography 
        variant="h4" 
        gutterBottom
        sx={{ 
          mb: 3,
          fontWeight: 700,
          color: 'text.primary',
        }}
      >
        Real-Time Transcription
      </Typography>

      {error && (
        <Alert 
          severity="error" 
          sx={{ 
            mb: 3,
            borderRadius: 2,
          }} 
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}

      {/* Main Action Buttons - Show when no active session and showOptions is true */}
      {!sessionId && !isRecording && showOptions && (
        <>
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} md={6}>
              <Card
                sx={{
                  height: '100%',
                  background: mode === 'dark' 
                    ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
                    : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)',
                  borderLeft: '4px solid',
                  borderLeftColor: 'primary.main',
                  transition: 'all 0.3s ease',
                  cursor: 'pointer',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: mode === 'dark' 
                      ? '0 4px 16px rgba(38, 166, 154, 0.25)'
                      : '0 4px 16px rgba(0, 150, 136, 0.15)',
                  },
                }}
                onClick={() => setShowOptions(false)}
              >
                <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 }, textAlign: 'center' }}>
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      bgcolor: 'primary.main',
                      color: 'white',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      mb: 2,
                      boxShadow: '0 2px 8px rgba(0, 150, 136, 0.2)',
                    }}
                  >
                    <MicIcon sx={{ fontSize: '2rem' }} />
                  </Box>
                  <Typography 
                    variant="h5" 
                    sx={{ 
                      fontWeight: 600,
                      color: 'text.primary',
                      mb: 1,
                    }}
                  >
                    Start New Meeting
                  </Typography>
                  <Typography 
                    variant="body2" 
                    color="text.secondary"
                    sx={{ 
                      lineHeight: 1.7,
                    }}
                  >
                    Begin a new transcription session and generate meeting insights
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card
                sx={{
                  height: '100%',
                  background: mode === 'dark' 
                    ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
                    : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)',
                  borderLeft: '4px solid',
                  borderLeftColor: 'secondary.main',
                  transition: 'all 0.3s ease',
                  cursor: 'pointer',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: mode === 'dark' 
                      ? '0 4px 16px rgba(38, 166, 154, 0.25)'
                      : '0 4px 16px rgba(0, 150, 136, 0.15)',
                  },
                }}
                onClick={() => navigate('/meetings')}
              >
                <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 }, textAlign: 'center' }}>
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      bgcolor: 'secondary.main',
                      color: 'white',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      mb: 2,
                      boxShadow: '0 2px 8px rgba(0, 150, 136, 0.2)',
                    }}
                  >
                    <SummarizeIcon sx={{ fontSize: '2rem' }} />
                  </Box>
                  <Typography 
                    variant="h5" 
                    sx={{ 
                      fontWeight: 600,
                      color: 'text.primary',
                      mb: 1,
                    }}
                  >
                    View Old Meetings
                  </Typography>
                  <Typography 
                    variant="body2" 
                    color="text.secondary"
                    sx={{ 
                      lineHeight: 1.7,
                    }}
                  >
                    Browse past meetings, MOMs, FAQs, and follow-up emails
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          <Divider sx={{ mb: 4, borderWidth: 2, borderColor: 'primary.light' }} />
        </>
      )}

      {/* Transcription Controls - Show when starting new or have active session */}
      {(showOptions === false || sessionId || isRecording) && (
        <>
      <Card 
        sx={{ 
          mb: 3,
          background: getCardBackground(),
          borderLeft: '4px solid',
          borderLeftColor: 'primary.main',
          transition: 'all 0.3s ease',
        }}
      >
        <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 } }}>
          <TextField
            fullWidth
            label="Meeting Title (Optional)"
            placeholder="Leave empty to auto-generate from transcript"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            sx={{ mb: 2 }}
            disabled={isRecording}
            helperText="Title will be automatically generated from transcript content if left empty"
          />
          <FormControl component="fieldset" sx={{ mb: 2 }} disabled={isRecording}>
            <FormLabel component="legend">Audio Source</FormLabel>
            <ToggleButtonGroup
              value={audioSource}
              exclusive
              onChange={(e, newValue) => {
                if (newValue !== null) {
                  setAudioSource(newValue)
                }
              }}
              aria-label="audio source"
            >
              <ToggleButton value="user" aria-label="user microphone">
                User Microphone
              </ToggleButton>
              <ToggleButton value="system" aria-label="system audio">
                System Audio
              </ToggleButton>
              <ToggleButton value="both" aria-label="both audio sources">
                Both
              </ToggleButton>
            </ToggleButtonGroup>
          </FormControl>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            {!isRecording ? (
              <Button
                variant="contained"
                color="primary"
                onClick={startTranscription}
                disabled={loading}
              >
                Start Recording
              </Button>
            ) : (
              <>
                <Button
                  variant="contained"
                  color="error"
                  onClick={stopTranscription}
                  disabled={loading}
                >
                  Stop Recording
                </Button>
                {(audioSource === 'user' || audioSource === 'both') && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Box
                      sx={{
                        width: 14,
                        height: 14,
                        borderRadius: '50%',
                        backgroundColor: voiceActivity ? '#009688' : '#9e9e9e',
                        boxShadow: voiceActivity
                          ? `0 0 10px #009688, 0 0 20px rgba(0, 150, 136, 0.5)`
                          : 'none',
                        transition: 'all 0.2s ease-in-out',
                        animation: voiceActivity ? 'pulse 1.5s ease-in-out infinite' : 'none',
                        '@keyframes pulse': {
                          '0%, 100%': {
                            transform: 'scale(1)',
                            opacity: 1,
                          },
                          '50%': {
                            transform: 'scale(1.3)',
                            opacity: 0.7,
                          },
                        },
                      }}
                    />
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        color: voiceActivity ? 'primary.main' : 'text.secondary',
                        fontWeight: voiceActivity ? 600 : 400,
                      }}
                    >
                      {voiceActivity ? 'Voice detected' : 'Listening...'}
                    </Typography>
                  </Box>
                )}
              </>
            )}
            {sessionId && !isRecording && (
              <>
                <Button
                  variant="outlined"
                    onClick={generateInsights}
                    disabled={loading}
                  >
                  Generate Insights
                </Button>
                <Button
                  variant="outlined"
                    onClick={() => exportDocument('pdf')}
                  >
                  Export PDF
                </Button>
                <Button
                  variant="outlined"
                    onClick={() => exportDocument('docx')}
                  >
                  Export DOCX
                </Button>
              </>
            )}
          </Box>
          {loading && <CircularProgress sx={{ mt: 2 }} />}
        </CardContent>
      </Card>

      {/* Live Transcript - Show when recording or have session */}
      {(isRecording || sessionId) && (
        <Card 
          sx={{ 
            mb: 3,
            background: getCardBackground(),
            borderLeft: '4px solid',
            borderLeftColor: 'primary.main',
            transition: 'all 0.3s ease',
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 } }}>
            <Typography 
              variant="h6" 
              gutterBottom
              sx={{ 
                fontWeight: 600,
                color: 'text.primary',
                mb: 2,
              }}
            >
              Live Transcript
            </Typography>
            <TextField
              fullWidth
              multiline
              minRows={8}
              maxRows={15}
              value={editedTranscript || fullTranscript || transcript || (isRecording ? 'Listening... Transcript will appear here as you speak.' : 'Transcript will appear here...')}
              onChange={handleTranscriptChange}
              placeholder={isRecording ? 'Listening... Transcript will appear here as you speak.' : 'Transcript will appear here...'}
              disabled={isRecording}
              sx={{
                '& .MuiInputBase-root': {
                  bgcolor: 'background.default',
                  fontFamily: 'inherit',
                  fontSize: '0.95rem',
                  lineHeight: 1.7,
                },
                '& .MuiInputBase-input': {
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                },
              }}
              InputProps={{
                endAdornment: isSaving ? (
                  <InputAdornment position="end">
                    <CircularProgress size={20} />
                  </InputAdornment>
                ) : null,
              }}
            />
            {/* Debug info in development */}
            {process.env.NODE_ENV === 'development' && (
              <Box sx={{ mt: 2, p: 1, bgcolor: 'grey.100', borderRadius: 1, fontSize: '0.75rem' }}>
                <Typography variant="caption" component="div">
                  Debug: fullTranscript length: {fullTranscript.length}, transcript length: {transcript.length}
                  <br />
                  Session ID: {sessionId || 'None'}, Recording: {isRecording ? 'Yes' : 'No'}
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* MOM */}
      {mom && (
        <Card 
          sx={{ 
            mb: 3,
            background: getHighlightCardBackground(),
            border: '2px solid',
            borderColor: 'primary.main',
            boxShadow: '0 2px 8px rgba(0, 150, 136, 0.1)',
            transition: 'all 0.3s ease',
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 } }}>
            <Typography 
              variant="h6" 
              gutterBottom
              sx={{ 
                fontWeight: 600,
                color: 'primary.dark',
                mb: 2,
              }}
            >
              Minutes of Meeting
            </Typography>
            <Box 
              sx={{ 
                p: 2, 
                bgcolor: 'background.paper', 
                borderRadius: 2,
                mb: 2,
                border: '1px solid',
                borderColor: 'secondary.light',
              }}
            >
              <Typography 
                variant="body2" 
                paragraph
                sx={{ 
                  color: 'text.primary',
                  lineHeight: 1.7,
                  m: 0,
                }}
              >
                {mom.summary || 'No summary available'}
              </Typography>
            </Box>
            
            {mom.decisions && mom.decisions.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography 
                  variant="subtitle2" 
                  gutterBottom
                  sx={{ 
                    fontWeight: 600,
                    color: 'text.primary',
                    mb: 1.5,
                  }}
                >
                  Decisions:
                </Typography>
                <Box 
                  component="ul" 
                  sx={{ 
                    listStyle: 'none',
                    p: 0,
                    m: 0,
                    '& li': {
                      p: 1.5,
                      mb: 1,
                      bgcolor: 'background.default',
                      borderRadius: 1,
                      borderLeft: '3px solid',
                      borderLeftColor: 'primary.light',
                    }
                  }}
                >
                  {mom.decisions.map((decision, idx) => (
                    <li key={idx}>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {decision.decision || 'No decision text'}
                      </Typography>
                    </li>
                  ))}
                </Box>
              </Box>
            )}
            
            {mom.action_items && mom.action_items.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography 
                  variant="subtitle2" 
                  gutterBottom
                  sx={{ 
                    fontWeight: 600,
                    color: 'text.primary',
                    mb: 1.5,
                  }}
                >
                  Action Items:
                </Typography>
                <Box 
                  component="ul" 
                  sx={{ 
                    listStyle: 'none',
                    p: 0,
                    m: 0,
                    '& li': {
                      p: 1.5,
                      mb: 1,
                      bgcolor: 'background.default',
                      borderRadius: 1,
                      borderLeft: '3px solid',
                      borderLeftColor: 'primary.main',
                    }
                  }}
                >
                  {mom.action_items.map((item, idx) => (
                    <li key={idx}>
                      <Typography variant="body2" sx={{ fontWeight: 500, mb: 0.5 }}>
                        {item.task}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Owner: {item.owner || 'Unassigned'} | Deadline: {item.deadline || 'TBD'}
                      </Typography>
                    </li>
                  ))}
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* FAQs */}
      {faqs && faqs.length > 0 && (
        <Card 
          sx={{ 
            mb: 3,
            background: getCardBackground(),
            borderLeft: '4px solid',
            borderLeftColor: 'primary.main',
            transition: 'all 0.3s ease',
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 } }}>
            <Typography 
              variant="h6" 
              gutterBottom
              sx={{ 
                fontWeight: 600,
                color: 'text.primary',
                mb: 2,
              }}
            >
              FAQs
            </Typography>
            {faqs.map((faq, idx) => (
              <Box 
                key={idx} 
                sx={{ 
                  mb: 2.5,
                  p: 2,
                  bgcolor: 'background.default',
                  borderRadius: 2,
                  border: '1px solid',
                  borderColor: 'secondary.light',
                }}
              >
                <Typography 
                  variant="subtitle2" 
                  sx={{ 
                    fontWeight: 600,
                    color: 'primary.dark',
                    mb: 1,
                  }}
                >
                  Q: {faq.question || 'No question'}
                </Typography>
                <Typography 
                  variant="body2"
                  sx={{ 
                    color: 'text.primary',
                    lineHeight: 1.7,
                  }}
                >
                  A: {faq.answer || 'No answer'}
                </Typography>
              </Box>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Email Draft */}
      {emailDraft && (
        <Card 
          sx={{ 
            mb: 3,
            background: getCardBackground(),
            borderLeft: '4px solid',
            borderLeftColor: 'primary.main',
            transition: 'all 0.3s ease',
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 } }}>
            <Typography 
              variant="h6" 
              gutterBottom
              sx={{ 
                fontWeight: 600,
                color: 'text.primary',
                mb: 2,
              }}
            >
              Follow-up Email Draft
            </Typography>
            <Box
              sx={{
                bgcolor: 'background.default',
                p: 2.5,
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'secondary.light',
              }}
            >
              <Typography 
                variant="body2" 
                component="pre" 
                sx={{ 
                  whiteSpace: 'pre-wrap',
                  color: 'text.primary',
                  lineHeight: 1.7,
                  m: 0,
                  fontFamily: 'inherit',
                }}
              >
                To: {emailDraft.to && emailDraft.to.length > 0 ? emailDraft.to.join(', ') : 'N/A'}
{emailDraft.cc && emailDraft.cc.length > 0 ? `\nCC: ${emailDraft.cc.join(', ')}` : ''}
{'\n'}Subject: {emailDraft.subject || 'No Subject'}

{emailDraft.body || 'No body content'}
              </Typography>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Risks */}
      {risks && risks.length > 0 && (
        <Card
          sx={{
            border: '2px solid',
            borderColor: 'error.main',
            background: getRiskCardBackground(),
            transition: 'all 0.3s ease',
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 } }}>
            <Typography 
              variant="h6" 
              gutterBottom
              sx={{ 
                fontWeight: 600,
                color: 'error.main',
                mb: 2,
              }}
            >
              Risk Alerts
            </Typography>
            {risks.map((risk, idx) => (
              <Alert 
                key={idx} 
                severity="warning" 
                sx={{ 
                  mb: 1.5,
                  borderRadius: 2,
                  bgcolor: mode === 'dark' ? '#3A2A1E' : '#FFF8E1',
                }}
              >
                {risk || 'Unknown risk'}
              </Alert>
            ))}
          </CardContent>
        </Card>
      )}
        </>
      )}
    </Box>
  )
}

export default TranscriptionView


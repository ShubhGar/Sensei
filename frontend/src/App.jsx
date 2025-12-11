import React, { useState, useEffect, useCallback } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom'
import {
  Container,
  AppBar,
  Toolbar,
  Typography,
  Box,
  Button,
  CssBaseline,
  IconButton,
  Divider,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Switch,
  Chip,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress
} from '@mui/material'
import HomeIcon from '@mui/icons-material/Home'
import MicIcon from '@mui/icons-material/Mic'
import EmailIcon from '@mui/icons-material/Email'
import GroupsIcon from '@mui/icons-material/Groups'
import ForumIcon from '@mui/icons-material/Forum'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import SmartToyIcon from '@mui/icons-material/SmartToy'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import AssignmentIcon from '@mui/icons-material/Assignment'
import AccountCircleIcon from '@mui/icons-material/AccountCircle'
import SettingsIcon from '@mui/icons-material/Settings'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import LightModeIcon from '@mui/icons-material/LightMode'
import LoginIcon from '@mui/icons-material/Login'
import LogoutIcon from '@mui/icons-material/Logout'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import { ThemeContextProvider, useTheme } from './ThemeContext'
import Home from './components/Home'
import TranscriptionView from './components/TranscriptionView'
import EmailView from './components/EmailView'
import TeamsView from './components/TeamsView'
import CommunicationsView from './components/CommunicationsView'
import OldMeetingsView from './components/OldMeetingsView'
import TodoView from './components/TodoView'
import AIChatAssistant from './components/AIChatAssistant'
import TrendsView from './components/TrendsView'
import MyJiraTasks from './components/MyJiraTasks'
import { authAPI } from './services/api'

function AppContent() {
  const location = useLocation()
  const navigate = useNavigate()
  const { mode, toggleTheme } = useTheme()
  const [settingsAnchorEl, setSettingsAnchorEl] = useState(null)
  const settingsOpen = Boolean(settingsAnchorEl)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [authLoading, setAuthLoading] = useState(true)
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' })
  const [tokenDialogOpen, setTokenDialogOpen] = useState(false)
  const [tokenInput, setTokenInput] = useState('')
  const [tokenLoading, setTokenLoading] = useState(false)

  const isActive = (path) => {
    if (path === '/communications') {
      return location.pathname === '/communications' || location.pathname === '/email' || location.pathname === '/teams'
    }
    return location.pathname === path
  }

  const checkAuthStatus = useCallback(async () => {
    try {
      setAuthLoading(true)
      const response = await authAPI.getAuthStatus()
      setIsAuthenticated(response.data.authenticated || false)
    } catch (err) {
      setIsAuthenticated(false)
    } finally {
      setAuthLoading(false)
    }
  }, [])

  useEffect(() => {
    checkAuthStatus()
    
    // Handle OAuth success/error redirects
    if (location.pathname === '/auth/success') {
      setSnackbar({ open: true, message: 'Successfully logged in with Microsoft!', severity: 'success' })
      checkAuthStatus()
      setTimeout(() => navigate('/'), 2000)
    } else if (location.pathname === '/auth/error') {
      const params = new URLSearchParams(location.search)
      const error = params.get('error') || 'Authentication failed'
      setSnackbar({ open: true, message: `Login error: ${error}`, severity: 'error' })
      setTimeout(() => navigate('/'), 3000)
    }
  }, [location.pathname, checkAuthStatus, navigate])

  const handleMicrosoftLogin = async () => {
    try {
      const response = await authAPI.getMicrosoftLoginUrl()
      // Redirect to Microsoft login page
      window.location.href = response.data.auth_url
    } catch (err) {
      setSnackbar({ open: true, message: 'Failed to initiate login: ' + err.message, severity: 'error' })
    }
  }

  const handleLogout = async () => {
    try {
      await authAPI.logout()
      setIsAuthenticated(false)
      setSnackbar({ open: true, message: 'Successfully logged out', severity: 'success' })
    } catch (err) {
      setSnackbar({ open: true, message: 'Logout failed: ' + err.message, severity: 'error' })
    }
  }

  const handleSetToken = async () => {
    if (!tokenInput.trim()) {
      setSnackbar({ open: true, message: 'Please enter a token', severity: 'error' })
      return
    }
    
    setTokenLoading(true)
    try {
      await authAPI.setToken(tokenInput.trim())
      setTokenDialogOpen(false)
      setTokenInput('')
      await checkAuthStatus()
      setSnackbar({ open: true, message: 'Token set successfully!', severity: 'success' })
    } catch (err) {
      setSnackbar({ open: true, message: 'Failed to set token: ' + (err.response?.data?.detail || err.message), severity: 'error' })
    } finally {
      setTokenLoading(false)
    }
  }

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false })
  }

  const handleSettingsClick = (event) => {
    setSettingsAnchorEl(event.currentTarget)
  }

  const handleSettingsClose = () => {
    setSettingsAnchorEl(null)
  }

  const handlePopOutWindow = (event) => {
    // Prevent any default behavior
    if (event) {
      event.preventDefault()
      event.stopPropagation()
    }
    
    // Open window immediately in direct response to user click
    const currentUrl = window.location.href
    console.log('Opening popup window:', currentUrl)
    
    const popup = window.open(
      currentUrl,
      'PayU Sensei',
      'width=1200,height=800,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes,resizable=yes'
    )
    
    console.log('Popup result:', popup)
    
    // Close menu
    handleSettingsClose()
    
    if (popup && !popup.closed) {
      // Focus the popup window
      try {
        popup.focus()
        console.log('Popup focused successfully')
      } catch (e) {
        // Some browsers may block focus, that's okay
        console.log('Could not focus popup:', e)
      }
      setSnackbar({ open: true, message: 'Window popped out successfully', severity: 'success' })
    } else {
      console.warn('Popup was blocked or failed to open')
      setSnackbar({ open: true, message: 'Popup blocked. Please allow popups for this site in your browser settings.', severity: 'warning' })
    }
  }

  return (
    <>
      <CssBaseline />
      <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'background.default' }}>
        <AppBar 
          position="static" 
          elevation={0}
          sx={{
            bgcolor: 'background.paper',
            borderBottom: '2px solid',
            borderBottomColor: 'secondary.light',
          }}
        >
          <Toolbar sx={{ py: 2, px: { xs: 1.5, sm: 2.5, md: 3 }, flexWrap: { xs: 'wrap', md: 'nowrap' }, gap: { xs: 1.5, md: 0 } }}>
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: { xs: 1.5, sm: 2, md: 2.5 },
                flexGrow: { xs: 1, md: 1 },
                minWidth: 0,
              }}
            >
              <Box
                component={Link}
                to="/"
                sx={{
                  px: { xs: 1.5, sm: 2, md: 2.5 },
                  py: { xs: 0.8, sm: 1, md: 1.2 },
                  borderRadius: 2,
                  background: 'linear-gradient(135deg, #009688 0%, #00796B 100%)',
                  boxShadow: '0 2px 8px rgba(0, 150, 136, 0.25)',
                  cursor: 'pointer',
                  textDecoration: 'none',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    transform: 'translateY(-1px)',
                    boxShadow: '0 4px 12px rgba(0, 150, 136, 0.35)',
                  },
                  flexShrink: 0,
                }}
              >
                <Typography 
                  variant="h5" 
                  component="div" 
                  sx={{ 
                    fontWeight: 700,
                    letterSpacing: '-0.5px',
                    color: 'white',
                    fontSize: { xs: '1rem', sm: '1.25rem', md: '1.5rem' },
                  }}
                >
                  PayU Sensei
                </Typography>
              </Box>
            </Box>
            <Box 
              sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: { xs: 0.25, sm: 0.5, md: 0.75 },
                flexWrap: { xs: 'wrap', sm: 'nowrap' },
                flexGrow: { xs: 1, md: 0 },
                justifyContent: { xs: 'flex-start', md: 'flex-end' },
                width: { xs: '100%', md: 'auto' },
                order: { xs: 3, md: 0 },
                mt: { xs: 1, md: 0 },
              }}
            >
              <Button
                component={Link}
                to="/"
                startIcon={<HomeIcon />}
                sx={{
                  color: isActive('/') ? 'primary.main' : 'text.secondary',
                  fontWeight: isActive('/') ? 700 : 500,
                  bgcolor: isActive('/') ? 'rgba(0, 150, 136, 0.12)' : 'transparent',
                  borderRadius: isActive('/') ? 2 : 0,
                  px: { xs: 0.75, sm: 1, md: 1.5 },
                  py: { xs: 0.5, sm: 0.625, md: 0.75 },
                  fontSize: { xs: '0.7rem', sm: '0.8rem', md: '0.875rem' },
                  borderBottom: isActive('/') ? '3px solid' : 'none',
                  borderBottomColor: 'primary.main',
                  transition: 'all 0.2s ease',
                  minWidth: { xs: 'auto', sm: '64px' },
                  '& .MuiButton-startIcon': {
                    marginRight: { xs: 0, sm: 0.25, md: 0.5 },
                  },
                  '&:hover': {
                    bgcolor: isActive('/') ? 'rgba(0, 150, 136, 0.18)' : 'rgba(0, 150, 136, 0.08)',
                    borderRadius: 2,
                  },
                }}
              >
                <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
                  Home
                </Box>
              </Button>
              <Button
                component={Link}
                to="/transcription"
                startIcon={<MicIcon />}
                sx={{
                  color: isActive('/transcription') ? 'primary.main' : 'text.secondary',
                  fontWeight: isActive('/transcription') ? 700 : 500,
                  bgcolor: isActive('/transcription') ? 'rgba(0, 150, 136, 0.12)' : 'transparent',
                  borderRadius: isActive('/transcription') ? 2 : 0,
                  px: { xs: 0.75, sm: 1, md: 1.5 },
                  py: { xs: 0.5, sm: 0.625, md: 0.75 },
                  fontSize: { xs: '0.7rem', sm: '0.8rem', md: '0.875rem' },
                  borderBottom: isActive('/transcription') ? '3px solid' : 'none',
                  borderBottomColor: 'primary.main',
                  transition: 'all 0.2s ease',
                  minWidth: { xs: 'auto', sm: '64px' },
                  '& .MuiButton-startIcon': {
                    marginRight: { xs: 0, sm: 0.25, md: 0.5 },
                  },
                  '&:hover': {
                    bgcolor: isActive('/transcription') ? 'rgba(0, 150, 136, 0.18)' : 'rgba(0, 150, 136, 0.08)',
                    borderRadius: 2,
                  },
                }}
              >
                <Box component="span" sx={{ display: { xs: 'none', md: 'inline' } }}>
                  Transcription
                </Box>
              </Button>
              <Button
                component={Link}
                to="/communications"
                startIcon={<ForumIcon />}
                sx={{
                  color: isActive('/communications') ? 'primary.main' : 'text.secondary',
                  fontWeight: isActive('/communications') ? 700 : 500,
                  bgcolor: isActive('/communications') ? 'rgba(0, 150, 136, 0.12)' : 'transparent',
                  borderRadius: isActive('/communications') ? 2 : 0,
                  px: { xs: 0.75, sm: 1, md: 1.5 },
                  py: { xs: 0.5, sm: 0.625, md: 0.75 },
                  fontSize: { xs: '0.7rem', sm: '0.8rem', md: '0.875rem' },
                  borderBottom: isActive('/communications') ? '3px solid' : 'none',
                  borderBottomColor: 'primary.main',
                  transition: 'all 0.2s ease',
                  minWidth: { xs: 'auto', sm: '64px' },
                  '& .MuiButton-startIcon': {
                    marginRight: { xs: 0, sm: 0.25, md: 0.5 },
                  },
                  '&:hover': {
                    bgcolor: isActive('/communications') ? 'rgba(0, 150, 136, 0.18)' : 'rgba(0, 150, 136, 0.08)',
                    borderRadius: 2,
                  },
                }}
              >
                <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
                  Communications
                </Box>
              </Button>
              <Button
                component={Link}
                to="/todos"
                startIcon={<CheckCircleIcon />}
                sx={{
                  color: isActive('/todos') ? 'primary.main' : 'text.secondary',
                  fontWeight: isActive('/todos') ? 700 : 500,
                  bgcolor: isActive('/todos') ? 'rgba(0, 150, 136, 0.12)' : 'transparent',
                  borderRadius: isActive('/todos') ? 2 : 0,
                  px: { xs: 0.75, sm: 1, md: 1.5 },
                  py: { xs: 0.5, sm: 0.625, md: 0.75 },
                  fontSize: { xs: '0.7rem', sm: '0.8rem', md: '0.875rem' },
                  borderBottom: isActive('/todos') ? '3px solid' : 'none',
                  borderBottomColor: 'primary.main',
                  transition: 'all 0.2s ease',
                  minWidth: { xs: 'auto', sm: '64px' },
                  '& .MuiButton-startIcon': {
                    marginRight: { xs: 0, sm: 0.25, md: 0.5 },
                  },
                  '&:hover': {
                    bgcolor: isActive('/todos') ? 'rgba(0, 150, 136, 0.18)' : 'rgba(0, 150, 136, 0.08)',
                    borderRadius: 2,
                  },
                }}
              >
                <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
                  Todos
                </Box>
              </Button>
              <Button
                component={Link}
                to="/jira-tasks"
                startIcon={<AssignmentIcon />}
                sx={{
                  color: isActive('/jira-tasks') ? 'primary.main' : 'text.secondary',
                  fontWeight: isActive('/jira-tasks') ? 700 : 500,
                  bgcolor: isActive('/jira-tasks') ? 'rgba(0, 150, 136, 0.12)' : 'transparent',
                  borderRadius: isActive('/jira-tasks') ? 2 : 0,
                  px: { xs: 0.75, sm: 1, md: 1.5 },
                  py: { xs: 0.5, sm: 0.625, md: 0.75 },
                  fontSize: { xs: '0.7rem', sm: '0.8rem', md: '0.875rem' },
                  borderBottom: isActive('/jira-tasks') ? '3px solid' : 'none',
                  borderBottomColor: 'primary.main',
                  transition: 'all 0.2s ease',
                  minWidth: { xs: 'auto', sm: '64px' },
                  '& .MuiButton-startIcon': {
                    marginRight: { xs: 0, sm: 0.25, md: 0.5 },
                  },
                  '&:hover': {
                    bgcolor: isActive('/jira-tasks') ? 'rgba(0, 150, 136, 0.18)' : 'rgba(0, 150, 136, 0.08)',
                    borderRadius: 2,
                  },
                }}
              >
                <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
                  JIRA Tasks
                </Box>
              </Button>
              <Button
                component={Link}
                to="/ai-assistant"
                startIcon={<SmartToyIcon />}
                sx={{
                  color: isActive('/ai-assistant') ? 'primary.main' : 'text.secondary',
                  fontWeight: isActive('/ai-assistant') ? 700 : 500,
                  bgcolor: isActive('/ai-assistant') ? 'rgba(0, 150, 136, 0.12)' : 'transparent',
                  borderRadius: isActive('/ai-assistant') ? 2 : 0,
                  px: { xs: 0.75, sm: 1, md: 1.5 },
                  py: { xs: 0.5, sm: 0.625, md: 0.75 },
                  fontSize: { xs: '0.7rem', sm: '0.8rem', md: '0.875rem' },
                  borderBottom: isActive('/ai-assistant') ? '3px solid' : 'none',
                  borderBottomColor: 'primary.main',
                  transition: 'all 0.2s ease',
                  minWidth: { xs: 'auto', sm: '64px' },
                  '& .MuiButton-startIcon': {
                    marginRight: { xs: 0, sm: 0.25, md: 0.5 },
                  },
                  '&:hover': {
                    bgcolor: isActive('/ai-assistant') ? 'rgba(0, 150, 136, 0.18)' : 'rgba(0, 150, 136, 0.08)',
                    borderRadius: 2,
                  },
                }}
              >
                <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
                  AI Assistant
                </Box>
              </Button>
              <Button
                component={Link}
                to="/trends"
                startIcon={<TrendingUpIcon />}
                sx={{
                  color: isActive('/trends') ? 'primary.main' : 'text.secondary',
                  fontWeight: isActive('/trends') ? 700 : 500,
                  bgcolor: isActive('/trends') ? 'rgba(0, 150, 136, 0.12)' : 'transparent',
                  borderRadius: isActive('/trends') ? 2 : 0,
                  px: { xs: 0.75, sm: 1, md: 1.5 },
                  py: { xs: 0.5, sm: 0.625, md: 0.75 },
                  fontSize: { xs: '0.7rem', sm: '0.8rem', md: '0.875rem' },
                  borderBottom: isActive('/trends') ? '3px solid' : 'none',
                  borderBottomColor: 'primary.main',
                  transition: 'all 0.2s ease',
                  minWidth: { xs: 'auto', sm: '64px' },
                  '& .MuiButton-startIcon': {
                    marginRight: { xs: 0, sm: 0.25, md: 0.5 },
                  },
                  '&:hover': {
                    bgcolor: isActive('/trends') ? 'rgba(0, 150, 136, 0.18)' : 'rgba(0, 150, 136, 0.08)',
                    borderRadius: 2,
                  },
                }}
              >
                <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
                  Trends
                </Box>
              </Button>
            </Box>
            <Box 
              sx={{ 
                display: 'flex', 
                gap: { xs: 0.5, sm: 0.75 }, 
                alignItems: 'center', 
                flexWrap: 'nowrap',
                flexShrink: 0,
                order: { xs: 2, md: 0 },
                ml: { xs: 0, md: 0.5 },
              }}
            >
              <Divider orientation="vertical" flexItem sx={{ display: { xs: 'none', sm: 'block' }, height: 32, mx: { xs: 0.25, sm: 0.5 } }} />
              {isAuthenticated ? (
                <>
                  <Chip
                    icon={<AccountCircleIcon />}
                    label="Microsoft"
                    size="small"
                    sx={{
                      bgcolor: 'success.main',
                      color: 'white',
                      fontWeight: 600,
                      display: { xs: 'none', sm: 'flex' }
                    }}
                  />
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<LogoutIcon />}
                    onClick={handleLogout}
                    sx={{
                      color: 'text.secondary',
                      borderColor: 'text.secondary',
                      fontSize: { xs: '0.7rem', sm: '0.875rem' },
                      px: { xs: 1, sm: 1.5 },
                      '&:hover': {
                        bgcolor: 'rgba(0, 150, 136, 0.08)',
                        borderColor: 'primary.main',
                        color: 'primary.main',
                      },
                    }}
                  >
                    <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
                      Logout
                    </Box>
                  </Button>
                </>
              ) : (
                <Button
                  size="small"
                  variant="contained"
                  onClick={() => setTokenDialogOpen(true)}
                  disabled={authLoading}
                  sx={{
                    bgcolor: '#0078d4',
                    color: 'white',
                    fontWeight: 600,
                    fontSize: { xs: '0.7rem', sm: '0.875rem' },
                    px: { xs: 1, sm: 1.5 },
                    '&:hover': {
                      bgcolor: '#106ebe',
                    },
                  }}
                >
                  Use Token
                </Button>
              )}
              <IconButton
                size="small"
                onClick={handleSettingsClick}
                sx={{
                  color: 'text.secondary',
                  '&:hover': {
                    bgcolor: 'rgba(0, 150, 136, 0.08)',
                    color: 'primary.main',
                  },
                }}
                aria-label="settings"
                aria-controls={settingsOpen ? 'settings-menu' : undefined}
                aria-haspopup="true"
                aria-expanded={settingsOpen ? 'true' : undefined}
              >
                <SettingsIcon fontSize="small" />
              </IconButton>
            </Box>
            <Menu
              id="settings-menu"
              anchorEl={settingsAnchorEl}
              open={settingsOpen}
              onClose={handleSettingsClose}
              MenuListProps={{
                'aria-labelledby': 'settings-button',
              }}
              anchorOrigin={{
                vertical: 'bottom',
                horizontal: 'right',
              }}
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              PaperProps={{
                sx: {
                  mt: 1.5,
                  minWidth: 200,
                  borderRadius: 2,
                  boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
                },
              }}
            >
              <Box
                sx={{ 
                  py: 1.5,
                  px: 2,
                  display: 'flex',
                  alignItems: 'center',
                  cursor: 'default',
                  '&:hover': {
                    bgcolor: 'action.hover',
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: 40 }}>
                  {mode === 'dark' ? (
                    <LightModeIcon fontSize="small" />
                  ) : (
                    <DarkModeIcon fontSize="small" />
                  )}
                </ListItemIcon>
                <ListItemText 
                  primary={mode === 'dark' ? 'Light Mode' : 'Dark Mode'}
                  secondary={mode === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
                />
                <Switch
                  checked={mode === 'dark'}
                  onChange={(e) => {
                    e.stopPropagation()
                    toggleTheme()
                  }}
                  onClick={(e) => {
                    e.stopPropagation()
                  }}
                  size="small"
                  sx={{ ml: 2 }}
                />
              </Box>
              <Box
                component="button"
                onClick={handlePopOutWindow}
                sx={{
                  width: '100%',
                  py: 1.5,
                  px: 2,
                  display: 'flex',
                  alignItems: 'center',
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontFamily: 'inherit',
                  fontSize: 'inherit',
                  color: 'inherit',
                  '&:hover': {
                    bgcolor: 'action.hover',
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: 40 }}>
                  <OpenInNewIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText 
                  primary="Pop Out Window"
                  secondary="Open in a new popup window"
                />
              </Box>
            </Menu>
          </Toolbar>
        </AppBar>
        
        <Container maxWidth="xl" sx={{ mt: 2, mb: 2 }}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/transcription" element={<TranscriptionView />} />
            <Route path="/communications" element={<CommunicationsView />} />
            <Route path="/email" element={<EmailView />} />
            <Route path="/teams" element={<TeamsView />} />
            <Route path="/meetings" element={<OldMeetingsView />} />
            <Route path="/todos" element={<TodoView />} />
            <Route path="/jira-tasks" element={<MyJiraTasks />} />
            <Route path="/ai-assistant" element={<AIChatAssistant />} />
            <Route path="/trends" element={<TrendsView />} />
            <Route path="/auth/success" element={<Box sx={{ textAlign: 'center', py: 4 }}><Typography>Authentication successful! Redirecting...</Typography></Box>} />
            <Route path="/auth/error" element={<Box sx={{ textAlign: 'center', py: 4 }}><Typography>Authentication failed. Redirecting...</Typography></Box>} />
          </Routes>
        </Container>
        
        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={handleCloseSnackbar}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
            {snackbar.message}
          </Alert>
        </Snackbar>

        {/* Token Input Dialog */}
        <Dialog
          open={tokenDialogOpen}
          onClose={() => {
            setTokenDialogOpen(false)
            setTokenInput('')
          }}
          maxWidth="sm"
          fullWidth
          PaperProps={{
            sx: {
              borderRadius: 3,
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
            Enter Graph Explorer Token
          </DialogTitle>
          <DialogContent sx={{ mt: 2 }}>
            <Alert severity="info" sx={{ mb: 2, borderRadius: 2 }}>
              <Typography variant="body2" sx={{ mb: 1 }}>
                <strong>How to get your token:</strong>
              </Typography>
              <Typography variant="body2" component="div">
                1. Go to <a href="https://developer.microsoft.com/en-us/graph/graph-explorer" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>Graph Explorer</a>
                <br />
                2. Sign in with your Microsoft account
                <br />
                3. Click on "Access token" tab or check the request headers
                <br />
                4. Copy the token and paste it below
              </Typography>
              <Typography variant="caption" sx={{ mt: 1, display: 'block', fontStyle: 'italic' }}>
                Note: Tokens expire after ~1 hour. You'll need to refresh them periodically.
              </Typography>
            </Alert>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Access Token"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Paste your access token here (starts with eyJ...)"
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  bgcolor: 'background.default',
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                },
              }}
            />
          </DialogContent>
          <DialogActions sx={{ p: 2 }}>
            <Button 
              onClick={() => {
                setTokenDialogOpen(false)
                setTokenInput('')
              }}
              variant="outlined"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSetToken}
              variant="contained"
              disabled={tokenLoading || !tokenInput.trim()}
              startIcon={tokenLoading ? <CircularProgress size={16} /> : null}
            >
              {tokenLoading ? 'Setting Token...' : 'Set Token'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </>
  )
}

function App() {
  return (
    <ThemeContextProvider>
      <Router>
        <AppContent />
      </Router>
    </ThemeContextProvider>
  )
}

export default App


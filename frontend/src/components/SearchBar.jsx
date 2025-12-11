import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  TextField,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Typography,
  CircularProgress,
  Chip,
  Divider,
  InputAdornment,
  IconButton,
  Popper,
  ClickAwayListener
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import CloseIcon from '@mui/icons-material/Close'
import MeetingIcon from '@mui/icons-material/Event'
import TodoIcon from '@mui/icons-material/CheckCircle'
import EmailIcon from '@mui/icons-material/Email'
import TeamsIcon from '@mui/icons-material/Groups'
import { searchAPI } from '../services/api'

const SearchBar = () => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [anchorEl, setAnchorEl] = useState(null)
  const navigate = useNavigate()
  const searchInputRef = useRef(null)
  const debounceTimer = useRef(null)

  useEffect(() => {
    if (searchInputRef.current && !anchorEl) {
      setAnchorEl(searchInputRef.current)
    }
  }, [anchorEl])

  const handleSearch = async (searchQuery) => {
    if (!searchQuery || searchQuery.trim().length < 1) {
      setResults([])
      setOpen(false)
      return
    }

    setLoading(true)
    try {
      const response = await searchAPI.search(searchQuery, 20)
      setResults(response.data.results || [])
      setOpen(true)
    } catch (error) {
      console.error('Search error:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (event) => {
    const value = event.target.value
    setQuery(value)

    // Clear previous timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current)
    }

    // Debounce search
    debounceTimer.current = setTimeout(() => {
      handleSearch(value)
    }, 300)
  }

  const handleClose = () => {
    setOpen(false)
    setQuery('')
    setResults([])
  }

  const handleResultClick = (result) => {
    handleClose()
    
    // Navigate based on result type
    switch (result.type) {
      case 'meeting':
        navigate(`/meetings?session=${result.id}`)
        break
      case 'todo':
        navigate('/')
        // Could scroll to todo or open a dialog
        break
      case 'email':
        navigate('/email')
        break
      case 'teams':
        navigate('/teams')
        break
      default:
        navigate('/')
    }
  }

  const getResultIcon = (type) => {
    switch (type) {
      case 'meeting':
        return <MeetingIcon />
      case 'todo':
        return <TodoIcon />
      case 'email':
        return <EmailIcon />
      case 'teams':
        return <TeamsIcon />
      default:
        return <SearchIcon />
    }
  }

  const getResultTypeLabel = (type) => {
    switch (type) {
      case 'meeting':
        return 'Meeting'
      case 'todo':
        return 'Todo'
      case 'email':
        return 'Email'
      case 'teams':
        return 'Teams'
      default:
        return type
    }
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Escape') {
      handleClose()
    }
  }

  return (
    <ClickAwayListener onClickAway={handleClose}>
      <Box sx={{ position: 'relative', width: { xs: '100%', sm: '300px', md: '400px' }, maxWidth: '100%' }}>
        <TextField
          inputRef={searchInputRef}
          fullWidth
          size="small"
          placeholder="Search meetings, todos, emails, teams..."
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (results.length > 0) {
              setOpen(true)
            }
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" sx={{ color: 'text.secondary' }} />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                {loading && <CircularProgress size={16} />}
                {query && !loading && (
                  <IconButton
                    size="small"
                    onClick={handleClose}
                    sx={{ p: 0.5 }}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                )}
              </InputAdornment>
            ),
            sx: {
              bgcolor: 'background.paper',
              borderRadius: 2,
              '& .MuiOutlinedInput-notchedOutline': {
                borderColor: 'divider'
              },
              '&:hover .MuiOutlinedInput-notchedOutline': {
                borderColor: 'primary.main'
              },
              '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                borderColor: 'primary.main',
                borderWidth: 2
              }
            }
          }}
        />
        
        <Popper
          open={open && (results.length > 0 || loading)}
          anchorEl={searchInputRef.current}
          placement="bottom-start"
          style={{ zIndex: 1300, width: searchInputRef.current?.offsetWidth || 400 }}
          modifiers={[
            {
              name: 'offset',
              options: {
                offset: [0, 8]
              }
            }
          ]}
        >
          <Paper
            elevation={8}
            sx={{
              maxHeight: '500px',
              overflow: 'auto',
              width: '100%',
              borderRadius: 2,
              border: '1px solid',
              borderColor: 'divider'
            }}
          >
            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                <CircularProgress size={24} />
              </Box>
            ) : results.length > 0 ? (
              <>
                <Box sx={{ p: 1.5, borderBottom: '1px solid', borderColor: 'divider' }}>
                  <Typography variant="caption" color="text.secondary">
                    {results.length} result{results.length !== 1 ? 's' : ''} found
                  </Typography>
                </Box>
                <List sx={{ p: 0 }}>
                  {results.map((result, index) => (
                    <React.Fragment key={`${result.type}-${result.id}-${index}`}>
                      <ListItem
                        button
                        onClick={() => handleResultClick(result)}
                        sx={{
                          '&:hover': {
                            bgcolor: 'action.hover'
                          }
                        }}
                      >
                        <ListItemIcon sx={{ minWidth: 40, color: 'primary.main' }}>
                          {getResultIcon(result.type)}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography variant="body2" fontWeight={500}>
                                {result.title}
                              </Typography>
                              <Chip
                                label={getResultTypeLabel(result.type)}
                                size="small"
                                sx={{
                                  height: 20,
                                  fontSize: '0.65rem',
                                  bgcolor: 'primary.light',
                                  color: 'primary.contrastText'
                                }}
                              />
                            </Box>
                          }
                          secondary={
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{
                                display: '-webkit-box',
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: 'vertical',
                                overflow: 'hidden',
                                mt: 0.5
                              }}
                            >
                              {result.snippet}
                            </Typography>
                          }
                        />
                      </ListItem>
                      {index < results.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              </>
            ) : query && !loading ? (
              <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  No results found for "{query}"
                </Typography>
              </Box>
            ) : null}
          </Paper>
        </Popper>
      </Box>
    </ClickAwayListener>
  )
}

export default SearchBar


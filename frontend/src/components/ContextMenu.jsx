import React from 'react'
import { Menu, MenuItem, ListItemIcon, ListItemText } from '@mui/material'
import AddTaskIcon from '@mui/icons-material/AddTask'
import { todoAPI } from '../services/api'

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low Priority' },
  { value: 'medium', label: 'Medium Priority' },
  { value: 'high', label: 'High Priority' },
  { value: 'critical', label: 'Critical Priority' }
]

const ContextMenu = ({ anchorEl, open, onClose, data, sourceType }) => {
  const handleAddToTodo = async (priority) => {
    if (!data) return
    
    try {
      const title = data.title || data.subject || data.task || (typeof data.content === 'string' ? data.content.substring(0, 100) : '') || 'Untitled'
      const description = data.description || data.summary || (typeof data.content === 'string' ? data.content : '') || data.body || ''
      
      const todoData = {
        title: title.length > 200 ? title.substring(0, 200) : title,
        description: description.length > 1000 ? description.substring(0, 1000) : description,
        priority: priority,
        source_type: sourceType || 'manual',
        source_id: data.id || data.message_id || data.email_id || String(data),
        source_data: {
          ...data,
          extracted_at: new Date().toISOString()
        }
      }

      await todoAPI.createTodo(todoData)
      onClose()
      // Show success message via console (can be enhanced with a notification system)
      console.log('Todo added successfully!')
    } catch (err) {
      console.error('Failed to add todo:', err)
      alert('Failed to add todo: ' + (err.response?.data?.detail || err.message))
    }
  }

  if (!open) return null

  return (
    <Menu
      anchorEl={anchorEl}
      open={open}
      onClose={onClose}
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
      <MenuItem disabled sx={{ py: 1, px: 2 }}>
        <ListItemText 
          primary="Add to Todo"
          secondary="Select priority"
          primaryTypographyProps={{ fontWeight: 600 }}
        />
      </MenuItem>
      {PRIORITY_OPTIONS.map((option) => (
        <MenuItem
          key={option.value}
          onClick={() => handleAddToTodo(option.value)}
          sx={{
            '&:hover': {
              bgcolor: 'action.hover',
            },
          }}
        >
          <ListItemIcon>
            <AddTaskIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary={option.label} />
        </MenuItem>
      ))}
    </Menu>
  )
}

export default ContextMenu


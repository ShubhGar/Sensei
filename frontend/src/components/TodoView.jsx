import React, { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  Chip,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  IconButton,
  Checkbox,
  Divider,
  Tabs,
  Tab
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked'
import DragIndicatorIcon from '@mui/icons-material/DragIndicator'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { todoAPI } from '../services/api'
import { useTheme } from '../ThemeContext'

const PRIORITY_COLORS = {
  low: { bg: '#E8F5E9', color: '#2E7D32', border: '#4CAF50' },
  medium: { bg: '#FFF9C4', color: '#F57F17', border: '#FBC02D' },
  high: { bg: '#FFE0B2', color: '#E65100', border: '#FF9800' },
  critical: { bg: '#FFCDD2', color: '#C62828', border: '#F44336' }
}

const PRIORITY_DARK_COLORS = {
  low: { bg: 'rgba(76, 175, 80, 0.15)', color: '#81C784', border: '#4CAF50' },
  medium: { bg: 'rgba(251, 192, 45, 0.15)', color: '#FFD54F', border: '#FBC02D' },
  high: { bg: 'rgba(255, 152, 0, 0.15)', color: '#FFB74D', border: '#FF9800' },
  critical: { bg: 'rgba(244, 67, 54, 0.15)', color: '#E57373', border: '#F44336' }
}

const PRIORITY_ORDER = ['critical', 'high', 'medium', 'low']

// Sortable Todo Item Component
const SortableTodoItem = ({ todo, priorityColor, onToggleComplete, onEdit, onDelete, mode }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: todo.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : (todo.is_completed ? 0.6 : 1),
  }

  return (
    <ListItem
      ref={setNodeRef}
      style={style}
      sx={{
        border: '1px solid',
        borderColor: priorityColor.border,
        borderRadius: 2,
        mb: 1.5,
        bgcolor: priorityColor.bg,
        transition: 'all 0.2s ease',
        '&:hover': {
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          transform: 'translateY(-2px)',
        },
      }}
    >
      <IconButton
        {...attributes}
        {...listeners}
        sx={{ mr: 1, cursor: 'grab', '&:active': { cursor: 'grabbing' } }}
      >
        <DragIndicatorIcon />
      </IconButton>
      <IconButton
        onClick={() => onToggleComplete(todo)}
        sx={{ mr: 1 }}
      >
        {todo.is_completed ? (
          <CheckCircleIcon sx={{ color: 'success.main' }} />
        ) : (
          <RadioButtonUncheckedIcon />
        )}
      </IconButton>
      <ListItemText
        primary={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
            <Typography 
              variant="subtitle1"
              sx={{ 
                fontWeight: 600,
                color: 'text.primary',
                textDecoration: todo.is_completed ? 'line-through' : 'none',
              }}
            >
              {todo.title}
            </Typography>
            <Chip 
              label={todo.priority.toUpperCase()} 
              size="small"
              sx={{ 
                bgcolor: priorityColor.border,
                color: 'white',
                fontWeight: 600,
              }}
            />
            {todo.source_type && (
              <Chip 
                label={todo.source_type} 
                size="small"
                sx={{ 
                  bgcolor: 'background.default',
                  fontWeight: 500,
                }}
              />
            )}
          </Box>
        }
        secondary={
          <Box>
            {todo.description && (
              <Typography 
                variant="body2" 
                sx={{ 
                  mt: 1,
                  color: 'text.primary',
                  lineHeight: 1.6,
                }}
              >
                {todo.description}
              </Typography>
            )}
            <Typography 
              variant="caption" 
              color="text.secondary"
              sx={{ 
                mt: 0.5,
                display: 'block',
              }}
            >
              Created: {new Date(todo.created_at).toLocaleString()}
              {todo.completed_at && ` • Completed: ${new Date(todo.completed_at).toLocaleString()}`}
            </Typography>
          </Box>
        }
      />
      <Box sx={{ display: 'flex', gap: 0.5 }}>
        <IconButton
          size="small"
          onClick={() => onEdit(todo)}
          sx={{ color: 'primary.main' }}
        >
          <EditIcon fontSize="small" />
        </IconButton>
        <IconButton
          size="small"
          onClick={() => onDelete(todo.id)}
          sx={{ color: 'error.main' }}
        >
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Box>
    </ListItem>
  )
}

const TodoView = () => {
  const { mode } = useTheme()
  const [todos, setTodos] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTodo, setEditingTodo] = useState(null)
  const [formData, setFormData] = useState({ title: '', description: '', priority: 'medium' })
  const [filterTab, setFilterTab] = useState(0) // 0: all, 1: active, 2: completed
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [activeId, setActiveId] = useState(null)
  const [groupedTodos, setGroupedTodos] = useState({})

  const cardBackground = mode === 'dark' 
    ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)'

  const priorityColors = mode === 'dark' ? PRIORITY_DARK_COLORS : PRIORITY_COLORS

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  useEffect(() => {
    loadTodos()
  }, [filterTab, priorityFilter])

  const groupTodosByPriority = useCallback(() => {
    const filtered = todos.filter(todo => {
      if (filterTab === 1 && todo.is_completed) return false
      if (filterTab === 2 && !todo.is_completed) return false
      if (priorityFilter !== 'all' && todo.priority !== priorityFilter) return false
      return true
    })

    const grouped = {}
    PRIORITY_ORDER.forEach(priority => {
      grouped[priority] = filtered
        .filter(todo => todo.priority === priority)
        .sort((a, b) => (a.order || 0) - (b.order || 0))
    })
    setGroupedTodos(grouped)
  }, [todos, filterTab, priorityFilter])

  useEffect(() => {
    groupTodosByPriority()
  }, [groupTodosByPriority])

  const loadTodos = async () => {
    setLoading(true)
    setError(null)
    try {
      let completed = null
      if (filterTab === 1) completed = false
      else if (filterTab === 2) completed = true

      const priority = priorityFilter !== 'all' ? priorityFilter : null
      const response = await todoAPI.listTodos(completed, priority)
      setTodos(response.data)
    } catch (err) {
      setError('Failed to load todos: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenDialog = (todo = null) => {
    if (todo) {
      setEditingTodo(todo)
      setFormData({
        title: todo.title,
        description: todo.description || '',
        priority: todo.priority
      })
    } else {
      setEditingTodo(null)
      setFormData({ title: '', description: '', priority: 'medium' })
    }
    setDialogOpen(true)
  }

  const handleCloseDialog = () => {
    setDialogOpen(false)
    setEditingTodo(null)
    setFormData({ title: '', description: '', priority: 'medium' })
  }

  const handleSave = async () => {
    if (!formData.title.trim()) {
      setError('Title is required')
      return
    }

    try {
      if (editingTodo) {
        await todoAPI.updateTodo(editingTodo.id, formData)
      } else {
        await todoAPI.createTodo(formData)
      }
      handleCloseDialog()
      loadTodos()
    } catch (err) {
      setError('Failed to save todo: ' + err.message)
    }
  }

  const handleDelete = async (todoId) => {
    if (!window.confirm('Are you sure you want to delete this todo?')) return
    
    try {
      await todoAPI.deleteTodo(todoId)
      loadTodos()
    } catch (err) {
      setError('Failed to delete todo: ' + err.message)
    }
  }

  const handleToggleComplete = async (todo) => {
    try {
      await todoAPI.updateTodo(todo.id, { is_completed: !todo.is_completed })
      loadTodos()
    } catch (err) {
      setError('Failed to update todo: ' + err.message)
    }
  }

  const handleDragStart = (event) => {
    setActiveId(event.active.id)
  }

  const handleDragEnd = async (event) => {
    const { active, over } = event
    setActiveId(null)

    if (!over || active.id === over.id) {
      return
    }

    // Find which priority group the dragged item belongs to
    const activeTodo = todos.find(t => t.id === active.id)
    if (!activeTodo) return

    const priority = activeTodo.priority
    const priorityTodos = groupedTodos[priority] || []
    
    const oldIndex = priorityTodos.findIndex(t => t.id === active.id)
    const newIndex = priorityTodos.findIndex(t => t.id === over.id)

    if (oldIndex === -1 || newIndex === -1) return

    // Reorder within the same priority group
    const reordered = arrayMove(priorityTodos, oldIndex, newIndex)
    const todoIds = reordered.map(t => t.id)

    try {
      await todoAPI.reorderTodos(todoIds)
      loadTodos()
    } catch (err) {
      setError('Failed to reorder todos: ' + err.message)
    }
  }

  const getPriorityColor = (priority) => {
    return priorityColors[priority] || priorityColors.medium
  }

  const getActiveTodo = () => {
    if (!activeId) return null
    return todos.find(t => t.id === activeId)
  }

  const renderPriorityGroup = (priority) => {
    const priorityTodos = groupedTodos[priority] || []
    if (priorityTodos.length === 0) return null

    const priorityColor = getPriorityColor(priority)
    const todoIds = priorityTodos.map(t => t.id)

    return (
      <Box key={priority} sx={{ mb: 3 }}>
        <Typography 
          variant="h6" 
          sx={{ 
            mb: 2, 
            fontWeight: 600,
            color: priorityColor.border,
            textTransform: 'capitalize'
          }}
        >
          {priority} Priority ({priorityTodos.length})
        </Typography>
        <SortableContext items={todoIds} strategy={verticalListSortingStrategy}>
          <List sx={{ p: 0 }}>
            {priorityTodos.map((todo) => (
              <SortableTodoItem
                key={todo.id}
                todo={todo}
                priorityColor={priorityColor}
                onToggleComplete={handleToggleComplete}
                onEdit={handleOpenDialog}
                onDelete={handleDelete}
                mode={mode}
              />
            ))}
          </List>
        </SortableContext>
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography 
          variant="h4" 
          gutterBottom
          sx={{ 
            mb: 3,
            fontWeight: 700,
            color: 'text.primary',
          }}
        >
          Todo List
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
          sx={{
            bgcolor: 'primary.main',
            '&:hover': { bgcolor: 'primary.dark' }
          }}
        >
          Add Todo
        </Button>
      </Box>

      {error && (
        <Alert 
          severity="error" 
          sx={{ mb: 2, borderRadius: 2 }} 
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}

      <Card sx={{ background: cardBackground, mb: 2 }}>
        <CardContent>
          <Box sx={{ mb: 2 }}>
            <Tabs value={filterTab} onChange={(e, v) => setFilterTab(v)} sx={{ mb: 2 }}>
              <Tab label="All" />
              <Tab label="Active" />
              <Tab label="Completed" />
            </Tabs>
            <FormControl size="small" sx={{ minWidth: 150, ml: 2 }}>
              <InputLabel>Priority</InputLabel>
              <Select
                value={priorityFilter}
                label="Priority"
                onChange={(e) => setPriorityFilter(e.target.value)}
              >
                <MenuItem value="all">All Priorities</MenuItem>
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="critical">Critical</MenuItem>
              </Select>
            </FormControl>
          </Box>

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : Object.values(groupedTodos).flat().length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body2" color="text.secondary">
                No todos found
              </Typography>
            </Box>
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragStart={handleDragStart}
              onDragEnd={handleDragEnd}
            >
              {PRIORITY_ORDER.map(priority => renderPriorityGroup(priority))}
              <DragOverlay>
                {activeId ? (
                  <Box
                    sx={{
                      border: '2px dashed',
                      borderColor: 'primary.main',
                      borderRadius: 2,
                      p: 2,
                      bgcolor: 'background.paper',
                      opacity: 0.8
                    }}
                  >
                    <Typography variant="subtitle1">
                      {getActiveTodo()?.title || 'Dragging...'}
                    </Typography>
                  </Box>
                ) : null}
              </DragOverlay>
            </DndContext>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Dialog */}
      <Dialog 
        open={dialogOpen} 
        onClose={handleCloseDialog} 
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
          {editingTodo ? 'Edit Todo' : 'Add Todo'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField
              label="Title"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              fullWidth
              multiline
              rows={3}
            />
            <FormControl fullWidth>
              <InputLabel>Priority</InputLabel>
              <Select
                value={formData.priority}
                label="Priority"
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
              >
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="critical">Critical</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default TodoView

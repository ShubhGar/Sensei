"""
Todo API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete as sql_delete
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db, TodoItem
from app.models.schemas import TodoItemCreate, TodoItemUpdate, TodoItemResponse

router = APIRouter()

# Priority order mapping for sorting
PRIORITY_ORDER = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1
}


@router.post("/", response_model=TodoItemResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(
    todo: TodoItemCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new todo item"""
    try:
        # Get the maximum order value for todos with the same priority
        result = await db.execute(
            select(TodoItem)
            .where(TodoItem.priority == todo.priority)
        )
        todos_with_priority = result.scalars().all()
        max_order = max([t.order for t in todos_with_priority if t.order is not None], default=-1.0)
        new_order = max_order + 1.0
        
        db_todo = TodoItem(
            title=todo.title,
            description=todo.description,
            priority=todo.priority,
            order=new_order,
            source_type=todo.source_type,
            source_id=todo.source_id,
            source_data=todo.source_data
        )
        db.add(db_todo)
        await db.commit()
        await db.refresh(db_todo)
        return db_todo
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create todo: {str(e)}"
        )


@router.get("/", response_model=List[TodoItemResponse])
async def list_todos(
    completed: Optional[bool] = None,
    priority: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all todo items with optional filters"""
    try:
        query = select(TodoItem)
        
        if completed is not None:
            query = query.where(TodoItem.is_completed == completed)
        
        if priority:
            query = query.where(TodoItem.priority == priority)
        
        # Order by: completed status, priority (critical > high > medium > low), then order within priority
        query = query.order_by(
            TodoItem.is_completed.asc(),
            TodoItem.priority.desc(),
            TodoItem.order.asc(),
            TodoItem.created_at.asc()
        )
        
        result = await db.execute(query)
        todos = result.scalars().all()
        return todos
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list todos: {str(e)}"
        )


@router.get("/{todo_id}", response_model=TodoItemResponse)
async def get_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific todo item"""
    try:
        result = await db.execute(select(TodoItem).where(TodoItem.id == todo_id))
        todo = result.scalar_one_or_none()
        if not todo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todo item not found"
            )
        return todo
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get todo: {str(e)}"
        )


@router.patch("/{todo_id}", response_model=TodoItemResponse)
async def update_todo(
    todo_id: int,
    todo_update: TodoItemUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a todo item"""
    try:
        result = await db.execute(select(TodoItem).where(TodoItem.id == todo_id))
        todo = result.scalar_one_or_none()
        if not todo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todo item not found"
            )
        
        update_data = todo_update.dict(exclude_unset=True)
        
        # Handle completion status
        if "is_completed" in update_data:
            if update_data["is_completed"] and not todo.is_completed:
                todo.completed_at = datetime.utcnow()
            elif not update_data["is_completed"]:
                todo.completed_at = None
        
        for field, value in update_data.items():
            setattr(todo, field, value)
        
        todo.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(todo)
        return todo
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update todo: {str(e)}"
        )


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a todo item"""
    try:
        result = await db.execute(select(TodoItem).where(TodoItem.id == todo_id))
        todo = result.scalar_one_or_none()
        if not todo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todo item not found"
            )
        
        await db.execute(sql_delete(TodoItem).where(TodoItem.id == todo_id))
        await db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete todo: {str(e)}"
        )


class ReorderTodosRequest(BaseModel):
    """Request model for reordering todos"""
    todo_ids: List[int]  # List of todo IDs in the new order (must all have same priority)


@router.post("/reorder", response_model=List[TodoItemResponse], status_code=status.HTTP_200_OK)
async def reorder_todos(
    reorder_request: ReorderTodosRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reorder todos within the same priority level"""
    try:
        if not reorder_request.todo_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="todo_ids list cannot be empty"
            )
        
        # Fetch all todos to be reordered
        result = await db.execute(
            select(TodoItem).where(TodoItem.id.in_(reorder_request.todo_ids))
        )
        todos = result.scalars().all()
        
        if len(todos) != len(reorder_request.todo_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more todo items not found"
            )
        
        # Verify all todos have the same priority
        priorities = set(todo.priority for todo in todos)
        if len(priorities) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All todos must have the same priority to reorder"
            )
        
        # Create a mapping of todo_id to todo object
        todo_map = {todo.id: todo for todo in todos}
        
        # Update order values based on the new order
        for index, todo_id in enumerate(reorder_request.todo_ids):
            todo = todo_map[todo_id]
            todo.order = float(index)
            todo.updated_at = datetime.utcnow()
        
        await db.commit()
        
        # Return updated todos in the new order
        updated_todos = [todo_map[tid] for tid in reorder_request.todo_ids]
        return updated_todos
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reorder todos: {str(e)}"
        )


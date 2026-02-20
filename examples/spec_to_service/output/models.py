"""
Pydantic models for the service
"""

from typing import Optional

from pydantic import BaseModel

class Task(BaseModel):
    """Schema for Task."""
    id: int
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    due_date: Optional[str] = None
    user_id: Optional[int] = None


class TaskCreate(BaseModel):
    """Schema for creating a Task."""
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    due_date: Optional[str] = None
    user_id: Optional[int] = None


class TaskUpdate(BaseModel):
    """Schema for updating a Task."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    user_id: Optional[int] = None


class AssignRequest(BaseModel):
    """Schema for assigning a resource to a user."""
    user_id: int


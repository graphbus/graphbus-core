"""
FastAPI router for TaskManagerAPI
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from models import (
    AssignRequest,
    Task,
    TaskCreate,
    TaskUpdate,
)

router = APIRouter(prefix="", tags=["TaskManagerAPI"])

# In-memory store for demo purposes
tasks_db: dict[int, dict] = {}
_next_id: int = 1

@router.get("/tasks", response_model=List[Task])
def list_tasks():
    """List all tasks."""
    return [{**v, "id": k} for k, v in tasks_db.items()]

@router.post("/tasks", response_model=Task, status_code=201)
def create_task(payload: TaskCreate):
    """Create a new task."""
    global _next_id
    data = payload.model_dump()
    tasks_db[_next_id] = data
    result = {**data, "id": _next_id}
    _next_id += 1
    return result

@router.get("/tasks/filter", response_model=List[Task])
def filter_tasks(status: Optional[str] = Query(None), priority: Optional[str] = Query(None)):
    """Filter tasks by query parameters."""
    results = list(tasks_db.values())
    if status is not None:
        results = [r for r in results if r.get("status") == status]
    if priority is not None:
        results = [r for r in results if r.get("priority") == priority]
    return results

@router.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    """Get a task by ID."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return {**tasks_db[task_id], "id": task_id}

@router.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate):
    """Update an existing task."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    updates = payload.model_dump(exclude_unset=True)
    tasks_db[task_id].update(updates)
    return {**tasks_db[task_id], "id": task_id}

@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """Delete a task."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    del tasks_db[task_id]
    return None

@router.put("/tasks/{task_id}/assign", response_model=Task)
def assign_task(task_id: int, payload: AssignRequest):
    """Assign task to a user."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    tasks_db[task_id]["user_id"] = payload.user_id
    return {**tasks_db[task_id], "id": task_id}

@router.put("/tasks/{task_id}/complete", response_model=Task)
def complete_task(task_id: int):
    """Mark task as complete."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    tasks_db[task_id]["status"] = "completed"
    return {**tasks_db[task_id], "id": task_id}

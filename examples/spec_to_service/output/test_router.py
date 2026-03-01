"""
Tests for TaskManagerAPI
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_task(client):
    """Create a sample task for testing."""
    payload = {"title": "Test task", "description": "A task for testing", "status": "pending", "priority": "medium"}
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    return response.json()


def test_list_tasks(client):
    """Test: List all tasks."""
    response = client.get("/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_task(client):
    """Test: Create a task."""
    payload = {"title": "Test task", "description": "A task for testing", "status": "pending", "priority": "medium"}
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data

def test_get_task(client, sample_task):
    """Test: Get a task by ID."""
    task_id = sample_task["id"]
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["id"] == task_id

def test_get_task_not_found(client):
    """Test: Get a task by ID with invalid ID."""
    response = client.get("/tasks/99999")
    assert response.status_code == 404

def test_update_task(client, sample_task):
    """Test: Update a task."""
    task_id = sample_task["id"]
    response = client.put(
        f"/tasks/{task_id}",
        json={"title": "Updated title"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"

def test_delete_task(client, sample_task):
    """Test: Delete a task."""
    task_id = sample_task["id"]
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204
    # Verify deletion
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 404

def test_assign_task(client, sample_task):
    """Test: Assign task to a user."""
    task_id = sample_task["id"]
    response = client.put(
        f"/tasks/{task_id}/assign",
        json={"user_id": 42}
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == 42

def test_filter_tasks(client, sample_task):
    """Test: Filter tasks by status, priority."""
    response = client.get("/tasks/filter?status=test&priority=test")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_complete_task(client, sample_task):
    """Test: Mark task as complete."""
    task_id = sample_task["id"]
    response = client.put(f"/tasks/{task_id}/complete")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

"""
Workflow project template - Approval workflow system
"""

from pathlib import Path
from .base import Template


class WorkflowTemplate(Template):
    """Approval workflow with multiple stages"""

    @property
    def name(self) -> str:
        return "workflow"

    @property
    def description(self) -> str:
        return "Approval workflow with multiple stages"

    def create_project(self, project_path: Path, project_name: str) -> None:
        """Create workflow project structure"""
        self._create_directory_structure(project_path)

        agents_dir = project_path / "agents"

        # Workflow initiator
        initiator = '''"""
Workflow Initiator - Starts approval workflows
"""

from graphbus_core import GraphBusNode, schema_method


class WorkflowInitiator(GraphBusNode):
    """Agent that initiates approval workflows"""

    SYSTEM_PROMPT = """
    You initiate and manage approval workflows.
    In Build Mode with agent orchestration enabled, you can negotiate with other
    agents about workflow structures, validation rules, and submission policies.
    """

    def __init__(self):
        super().__init__()
        self.request_counter = 0

    @schema_method(
        input_schema={"title": str, "content": str},
        output_schema={"id": int, "title": str, "content": str, "status": str}
    )
    def submit_request(self, title: str, content: str) -> dict:
        """Submit a new approval request"""
        self.request_counter += 1
        request = {
            "id": self.request_counter,
            "title": title,
            "content": content,
            "status": "pending"
        }
        self.publish("/workflow/submitted", request)
        return request

    @schema_method(
        input_schema={},
        output_schema={"total_requests": int}
    )
    def get_stats(self) -> dict:
        """Get workflow statistics"""
        return {"total_requests": self.request_counter}
'''

        # Approval agent
        approver = '''"""
Approval Agent - Reviews and approves requests
"""

from graphbus_core import GraphBusNode, subscribe, schema_method


class ApprovalAgent(GraphBusNode):
    """Agent that reviews and approves workflow requests"""

    SYSTEM_PROMPT = """
    You review and approve or reject workflow requests.
    In Build Mode with agent orchestration enabled, you can negotiate with other
    agents about approval criteria, escalation policies, and decision-making logic.
    """

    def __init__(self):
        super().__init__()
        self.pending_requests = {}
        self.approved_count = 0
        self.rejected_count = 0

    @subscribe("/workflow/submitted")
    def on_workflow_submitted(self, event: dict):
        """Handle new workflow submissions"""
        request_id = event.get("id")
        self.pending_requests[request_id] = event

        # Auto-approve for demo (would have real approval logic in production)
        self.approved_count += 1
        approved = {
            **event,
            "status": "approved",
            "approver": "ApprovalAgent"
        }
        self.publish("/workflow/approved", approved)

    @schema_method(
        input_schema={},
        output_schema={"approved": int, "rejected": int, "pending": int}
    )
    def get_approval_stats(self) -> dict:
        """Get approval statistics"""
        return {
            "approved": self.approved_count,
            "rejected": self.rejected_count,
            "pending": len(self.pending_requests)
        }
'''

        # Notification agent
        notifier = '''"""
Notification Agent - Sends workflow notifications
"""

from graphbus_core import GraphBusNode, subscribe, schema_method


class NotificationAgent(GraphBusNode):
    """Agent that sends notifications about workflow events"""

    SYSTEM_PROMPT = """
    You send notifications about workflow status changes.
    In Build Mode with agent orchestration enabled, you can negotiate with other
    agents about notification channels, formats, and delivery schedules.
    """

    def __init__(self):
        super().__init__()
        self.notification_count = 0

    @subscribe("/workflow/approved")
    def on_workflow_approved(self, event: dict):
        """Notify when workflow is approved"""
        self.notification_count += 1
        title = event.get("title", "Unknown")
        print(f"[NOTIFICATION #{self.notification_count}] Request '{title}' has been approved")
        self.publish("/workflow/completed", event)

    @subscribe("/workflow/rejected")
    def on_workflow_rejected(self, event: dict):
        """Notify when workflow is rejected"""
        self.notification_count += 1
        title = event.get("title", "Unknown")
        print(f"[NOTIFICATION #{self.notification_count}] Request '{title}' has been rejected")

    @schema_method(
        input_schema={},
        output_schema={"total_notifications": int}
    )
    def get_stats(self) -> dict:
        """Get notification statistics"""
        return {"total_notifications": self.notification_count}
'''

        self._write_file(agents_dir / "initiator.py", initiator)
        self._write_file(agents_dir / "approver.py", approver)
        self._write_file(agents_dir / "notifier.py", notifier)

        readme = f'''# {project_name}

Approval workflow system using GraphBus.

## Workflow Stages
1. Initiator - Submits requests
2. Approver - Reviews and approves/rejects
3. Notifier - Sends notifications

## Getting Started
```bash
pip install -r requirements.txt
graphbus build agents/
graphbus run .graphbus
```

## Example Usage
In the REPL:
```
call WorkflowInitiator.submit_request title="Budget Request" content="Need $1000 for equipment"
```
'''

        self._write_file(project_path / "README.md", readme)
        self._write_file(project_path / "requirements.txt", "graphbus-core>=0.1.0\ngraphbus-cli>=0.1.0\n")

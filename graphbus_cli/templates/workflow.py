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
        initiator = '''from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, method

@agent(name="WorkflowInitiator", description="Starts approval workflows")
class WorkflowInitiator(NodeBase):
    @method(description="Submit request", parameters={"title": "str", "content": "str"}, return_type="dict")
    def submit_request(self, title: str, content: str) -> dict:
        request = {"id": 1, "title": title, "content": content, "status": "pending"}
        self.publish("/workflow/submitted", request)
        return request
'''

        # Approval agent
        approver = '''from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, subscribes

@agent(name="ApprovalAgent", description="Reviews and approves requests")
class ApprovalAgent(NodeBase):
    def __init__(self):
        super().__init__()
        self.pending_requests = {}

    @subscribes("/workflow/submitted")
    def on_workflow_submitted(self, payload):
        request_id = payload.get("id")
        self.pending_requests[request_id] = payload
        # Auto-approve for demo
        approved = {**payload, "status": "approved", "approver": "ApprovalAgent"}
        self.publish("/workflow/approved", approved)
'''

        # Notification agent
        notifier = '''from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, subscribes

@agent(name="NotificationAgent", description="Sends workflow notifications")
class NotificationAgent(NodeBase):
    @subscribes("/workflow/approved")
    def on_workflow_approved(self, payload):
        title = payload.get("title", "Unknown")
        print(f"NOTIFICATION: Request '{title}' has been approved")
        self.publish("/workflow/completed", payload)

    @subscribes("/workflow/rejected")
    def on_workflow_rejected(self, payload):
        title = payload.get("title", "Unknown")
        print(f"NOTIFICATION: Request '{title}' has been rejected")
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

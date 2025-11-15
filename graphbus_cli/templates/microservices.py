"""
Microservices project template - Multi-service architecture
"""

from pathlib import Path
from .base import Template


class MicroservicesTemplate(Template):
    """Multi-service architecture with API gateway"""

    @property
    def name(self) -> str:
        return "microservices"

    @property
    def description(self) -> str:
        return "Multi-service architecture with API gateway"

    def create_project(self, project_path: Path, project_name: str) -> None:
        """Create microservices project structure"""
        self._create_directory_structure(project_path)

        # Create agents directory structure
        agents_dir = project_path / "agents"
        (agents_dir / "gateway").mkdir(exist_ok=True)
        (agents_dir / "services").mkdir(exist_ok=True)

        # Gateway agent - simplified
        gateway_agent = '''from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, method, subscribes

@agent(name="APIGateway", description="Routes API requests")
class APIGateway(NodeBase):
    @method(description="Handle request", parameters={"path": "str"}, return_type="dict")
    def handle_request(self, path: str) -> dict:
        if path.startswith("/users"):
            self.publish("/service/user/request", {"path": path})
        return {"status": "routed"}
'''

        # User service - simplified
        user_service = '''from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, method, subscribes

@agent(name="UserService", description="Manages users")
class UserService(NodeBase):
    def __init__(self):
        super().__init__()
        self.users = {}

    @subscribes("/service/user/request")
    def on_user_request(self, payload):
        self.publish("/service/user/response", {"status": "ok"})
'''

        self._write_file(agents_dir / "gateway" / "__init__.py", "")
        self._write_file(agents_dir / "gateway" / "api_gateway.py", gateway_agent)
        self._write_file(agents_dir / "services" / "__init__.py", "")
        self._write_file(agents_dir / "services" / "user_service.py", user_service)

        # README
        readme = f'''# {project_name}

Microservices architecture using GraphBus.

## Services
- API Gateway - Routes requests
- User Service - Manages users

## Getting Started
```bash
pip install -r requirements.txt
graphbus build agents/
graphbus run .graphbus
```
'''

        self._write_file(project_path / "README.md", readme)
        self._write_file(project_path / "requirements.txt", "graphbus-core>=0.1.0\ngraphbus-cli>=0.1.0\n")

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
        gateway_agent = '''"""
API Gateway - Routes API requests to microservices
"""

from graphbus_core import GraphBusNode, schema_method, subscribe


class APIGateway(GraphBusNode):
    """API Gateway that routes requests to appropriate microservices"""

    SYSTEM_PROMPT = """
    You route API requests to appropriate microservices.
    In Build Mode with agent orchestration enabled, you can negotiate with other
    agents about routing strategies, load balancing, authentication, and API versioning.
    """

    def __init__(self):
        super().__init__()
        self.request_count = 0

    @schema_method(
        input_schema={"path": str, "method": str},
        output_schema={"status": str, "service": str, "request_id": int}
    )
    def handle_request(self, path: str, method: str = "GET") -> dict:
        """Route API request to appropriate service"""
        self.request_count += 1

        if path.startswith("/users"):
            service = "UserService"
            self.publish("/service/user/request", {
                "path": path,
                "method": method,
                "request_id": self.request_count
            })
        elif path.startswith("/orders"):
            service = "OrderService"
            self.publish("/service/order/request", {
                "path": path,
                "method": method,
                "request_id": self.request_count
            })
        else:
            service = "Unknown"

        return {
            "status": "routed",
            "service": service,
            "request_id": self.request_count
        }

    @schema_method(
        input_schema={},
        output_schema={"total_requests": int}
    )
    def get_stats(self) -> dict:
        """Get gateway statistics"""
        return {"total_requests": self.request_count}
'''

        # User service - simplified
        user_service = '''"""
User Service - Manages user data
"""

from graphbus_core import GraphBusNode, subscribe, schema_method


class UserService(GraphBusNode):
    """Microservice that manages user data"""

    SYSTEM_PROMPT = """
    You manage user data and handle user-related operations.
    In Build Mode with agent orchestration enabled, you can negotiate with other
    agents about data schemas, validation rules, caching strategies, and security policies.
    """

    def __init__(self):
        super().__init__()
        self.users = {}
        self.request_count = 0

    @subscribe("/service/user/request")
    def on_user_request(self, event: dict):
        """Handle user service requests"""
        self.request_count += 1
        path = event.get("path", "")
        method = event.get("method", "GET")
        request_id = event.get("request_id")

        # Simple demo response
        response = {
            "status": "ok",
            "service": "UserService",
            "request_id": request_id,
            "data": {"user_count": len(self.users)}
        }
        self.publish("/service/user/response", response)

    @schema_method(
        input_schema={"user_id": str, "name": str},
        output_schema={"id": str, "name": str, "created": bool}
    )
    def create_user(self, user_id: str, name: str) -> dict:
        """Create a new user"""
        self.users[user_id] = {"name": name}
        return {"id": user_id, "name": name, "created": True}

    @schema_method(
        input_schema={},
        output_schema={"user_count": int, "request_count": int}
    )
    def get_stats(self) -> dict:
        """Get service statistics"""
        return {
            "user_count": len(self.users),
            "request_count": self.request_count
        }
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

"""
Chatbot project template
"""

from pathlib import Path
from .base import Template


class ChatbotTemplate(Template):
    """LLM-powered chatbot with specialized agents"""

    @property
    def name(self) -> str:
        return "chatbot"

    @property
    def description(self) -> str:
        return "LLM-powered chatbot with specialized agents"

    def create_project(self, project_path: Path, project_name: str) -> None:
        """Create chatbot project structure"""
        self._create_directory_structure(project_path)

        agents_dir = project_path / "agents"

        # Orchestrator
        orchestrator = '''"""
Chat Orchestrator - Routes messages to specialist agents
"""

from graphbus_core import GraphBusNode, schema_method


class ChatOrchestrator(GraphBusNode):
    """Routes chat messages to specialized agents"""

    SYSTEM_PROMPT = """
    You route incoming chat messages to appropriate specialist agents.
    In Build Mode with agent orchestration enabled, you can negotiate with other
    agents about routing logic, message classification, and load balancing strategies.
    """

    def __init__(self):
        super().__init__()
        self.message_count = 0

    @schema_method(
        input_schema={"text": str},
        output_schema={"status": str, "route": str, "count": int}
    )
    def handle_message(self, text: str) -> dict:
        """Route message to appropriate specialist"""
        self.message_count += 1

        if "weather" in text.lower():
            route = "/chat/weather/query"
            specialist = "weather"
        elif "code" in text.lower():
            route = "/chat/code/query"
            specialist = "code"
        else:
            route = "/chat/general/query"
            specialist = "general"

        self.publish(route, {"text": text})
        return {
            "status": "routed",
            "route": specialist,
            "count": self.message_count
        }
'''

        # Weather specialist
        weather = '''"""
Weather Agent - Handles weather-related queries
"""

from graphbus_core import GraphBusNode, subscribe, schema_method


class WeatherAgent(GraphBusNode):
    """Specialized agent for weather queries"""

    SYSTEM_PROMPT = """
    You handle weather-related queries and provide weather information.
    In Build Mode with agent orchestration enabled, you can negotiate with other
    agents about data sources, caching strategies, and response formats.
    """

    def __init__(self):
        super().__init__()
        self.query_count = 0

    @subscribe("/chat/weather/query")
    def on_weather_query(self, event: dict):
        """Handle incoming weather queries"""
        text = event.get("text", "")
        self.query_count += 1

        # Simple weather response (would connect to real API in production)
        response = f"Weather query received: '{text}'. It's sunny today!"

        self.publish("/chat/response", {
            "text": response,
            "agent": "WeatherAgent",
            "query_count": self.query_count
        })

    @schema_method(
        input_schema={},
        output_schema={"total_queries": int}
    )
    def get_stats(self) -> dict:
        """Get weather query statistics"""
        return {"total_queries": self.query_count}
'''

        self._write_file(agents_dir / "orchestrator.py", orchestrator)
        self._write_file(agents_dir / "weather_agent.py", weather)

        readme = f'''# {project_name}

LLM-powered chatbot using GraphBus.

## Getting Started
```bash
pip install -r requirements.txt
graphbus build agents/
graphbus run .graphbus
```
'''

        self._write_file(project_path / "README.md", readme)
        self._write_file(project_path / "requirements.txt", "graphbus-core>=0.1.0\ngraphbus-cli>=0.1.0\n")

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
        orchestrator = '''from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, method, subscribes

@agent(name="ChatOrchestrator", description="Routes messages to specialists")
class ChatOrchestrator(NodeBase):
    @method(description="Handle message", parameters={"text": "str"}, return_type="dict")
    def handle_message(self, text: str) -> dict:
        if "weather" in text.lower():
            self.publish("/chat/weather/query", {"text": text})
        elif "code" in text.lower():
            self.publish("/chat/code/query", {"text": text})
        else:
            self.publish("/chat/general/query", {"text": text})
        return {"status": "routed"}
'''

        # Weather specialist
        weather = '''from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, subscribes

@agent(name="WeatherAgent", description="Handles weather queries")
class WeatherAgent(NodeBase):
    @subscribes("/chat/weather/query")
    def on_weather_query(self, payload):
        response = "It's sunny today!"
        self.publish("/chat/response", {"text": response})
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

"""
Basic project template - Simple 3-agent example
"""

from pathlib import Path
from .base import Template


class BasicTemplate(Template):
    """Simple 3-agent example (recommended for beginners)"""

    @property
    def name(self) -> str:
        return "basic"

    @property
    def description(self) -> str:
        return "Simple 3-agent example (recommended for beginners)"

    def create_project(self, project_path: Path, project_name: str) -> None:
        """Create basic project structure"""
        self._create_directory_structure(project_path)

        # Create agents
        self._create_hello_agent(project_path)
        self._create_processor_agent(project_path)
        self._create_logger_agent(project_path)

        # Create supporting files
        self._create_init_file(project_path)
        self._create_readme(project_path, project_name)
        self._create_requirements(project_path)
        self._create_tests(project_path)
        self._create_gitignore(project_path)

    def _create_hello_agent(self, project_path: Path) -> None:
        """Create HelloAgent"""
        content = '''"""
Hello Agent - Generates greetings
"""

from graphbus_core import GraphBusNode, schema_method


class HelloAgent(GraphBusNode):
    """Agent that generates greetings"""

    SYSTEM_PROMPT = """
    You generate personalized greeting messages.
    In Build Mode with agent orchestration enabled, you can negotiate with other
    agents to improve greeting formats, add personalization, or enhance the user experience.
    """

    def __init__(self):
        super().__init__()
        self.greeting_count = 0

    @schema_method(
        input_schema={"name": str},
        output_schema={"message": str, "count": int}
    )
    def generate_greeting(self, name: str) -> dict:
        """Generate a personalized greeting"""
        self.greeting_count += 1
        message = f"Hello, {name}! This is greeting #{self.greeting_count}"
        return {"message": message, "count": self.greeting_count}

    @schema_method(
        input_schema={},
        output_schema={"total_greetings": int}
    )
    def get_stats(self) -> dict:
        """Get greeting statistics"""
        return {"total_greetings": self.greeting_count}
'''
        self._write_file(project_path / "agents" / "hello_agent.py", content)

    def _create_processor_agent(self, project_path: Path) -> None:
        """Create ProcessorAgent"""
        content = '''"""
Processor Agent - Processes greetings
"""

from graphbus_core import GraphBusNode, schema_method, subscribe


class ProcessorAgent(GraphBusNode):
    """Agent that processes greetings"""

    SYSTEM_PROMPT = """
    You process and transform greeting messages.
    In Build Mode with agent orchestration, you can propose improvements to message
    processing algorithms, suggest new transformations, or optimize performance.
    """

    def __init__(self):
        super().__init__()
        self.processed_count = 0

    @subscribe("/greetings/generated")
    def on_greeting_generated(self, event: dict):
        """Handle greeting generation events"""
        message = event.get("message", "")
        print(f"[ProcessorAgent] Received greeting: {message}")

        # Process and publish transformed message
        processed = self.process(message)
        self.publish("/greetings/processed", {
            "original": message,
            "processed": processed
        })

    @schema_method(
        input_schema={"message": str},
        output_schema={"result": str, "count": int}
    )
    def process(self, message: str) -> dict:
        """Process and transform a greeting"""
        self.processed_count += 1
        return {
            "result": message.upper(),
            "count": self.processed_count
        }
'''
        self._write_file(project_path / "agents" / "processor_agent.py", content)

    def _create_logger_agent(self, project_path: Path) -> None:
        """Create LoggerAgent"""
        content = '''"""
Logger Agent - Logs messages
"""

from graphbus_core import GraphBusNode, subscribe, schema_method


class LoggerAgent(GraphBusNode):
    """Agent that logs events"""

    SYSTEM_PROMPT = """
    You log all system events for monitoring and debugging.
    In Build Mode with agent orchestration, you can negotiate about what events
    should be logged, log formats, retention policies, and integration with
    monitoring systems.
    """

    def __init__(self):
        super().__init__()
        self.log_count = 0

    @subscribe("/greetings/generated")
    def on_greeting_generated(self, event: dict):
        """Log when a greeting is generated"""
        self.log_count += 1
        message = event.get("message", "Unknown")
        print(f"[LOG #{self.log_count}] Greeting generated: {message}")

    @subscribe("/greetings/processed")
    def on_greeting_processed(self, event: dict):
        """Log when a greeting is processed"""
        self.log_count += 1
        original = event.get("original", "Unknown")
        processed = event.get("processed", "Unknown")
        print(f"[LOG #{self.log_count}] Processed: {original} -> {processed}")

    @schema_method(
        input_schema={},
        output_schema={"total_logs": int}
    )
    def get_log_count(self) -> dict:
        """Get total number of logs"""
        return {"total_logs": self.log_count}
'''
        self._write_file(project_path / "agents" / "logger_agent.py", content)

    def _create_init_file(self, project_path: Path) -> None:
        """Create __init__.py"""
        content = '''"""
Agents package
"""
'''
        self._write_file(project_path / "agents" / "__init__.py", content)

    def _create_readme(self, project_path: Path, project_name: str) -> None:
        """Create README.md"""
        content = f'''# {project_name}

A GraphBus application with a simple 3-agent architecture.

## Architecture

This project demonstrates basic GraphBus concepts with three agents:

- **HelloAgent**: Generates personalized greetings
- **ProcessorAgent**: Processes and transforms greetings
- **LoggerAgent**: Logs all system events

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Build the agents:
   ```bash
   graphbus build agents/
   ```

3. Run the runtime:
   ```bash
   graphbus run .graphbus
   ```

4. In the interactive REPL, try:
   ```
   call HelloAgent.generate_greeting {{"name": "Alice"}}
   call ProcessorAgent.process {{"message": "hello world"}}
   stats
   nodes
   topics
   ```

## Project Structure

```
{project_name}/
├── agents/              # Agent implementations
│   ├── hello_agent.py
│   ├── processor_agent.py
│   └── logger_agent.py
├── tests/               # Test suite
│   └── test_agents.py
├── .graphbus/           # Build artifacts (generated)
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Next Steps

- Add more agents by creating new Python files in `agents/`
- Define event subscriptions using the `@subscribes` decorator
- Implement methods using the `@method` decorator
- Run tests with `pytest tests/`
- See GraphBus documentation for advanced features

## Learn More

- [GraphBus Documentation](https://github.com/your-org/graphbus)
- [Agent Development Guide](https://github.com/your-org/graphbus/docs/agents.md)
- [Examples](https://github.com/your-org/graphbus/examples)
'''
        self._write_file(project_path / "README.md", content)

    def _create_requirements(self, project_path: Path) -> None:
        """Create requirements.txt"""
        content = '''# GraphBus dependencies
graphbus-core>=0.1.0
graphbus-cli>=0.1.0

# Development dependencies
pytest>=7.0.0
pytest-cov>=4.0.0
'''
        self._write_file(project_path / "requirements.txt", content)

    def _create_tests(self, project_path: Path) -> None:
        """Create test file"""
        content = '''"""
Tests for agents
"""

import pytest
from pathlib import Path


def test_agents_can_be_imported():
    """Test that all agents can be imported"""
    from agents.hello_agent import HelloAgent
    from agents.processor_agent import ProcessorAgent
    from agents.logger_agent import LoggerAgent

    assert HelloAgent is not None
    assert ProcessorAgent is not None
    assert LoggerAgent is not None


def test_hello_agent_generates_greeting():
    """Test HelloAgent greeting generation"""
    from agents.hello_agent import HelloAgent

    agent = HelloAgent()
    greeting = agent.generate_greeting("Alice")

    assert "Alice" in greeting
    assert "Hello" in greeting


def test_processor_agent_transforms_message():
    """Test ProcessorAgent message transformation"""
    from agents.processor_agent import ProcessorAgent

    agent = ProcessorAgent()
    result = agent.process("hello world")

    assert result == "HELLO WORLD"
'''
        self._write_file(project_path / "tests" / "test_agents.py", content)

    def _create_gitignore(self, project_path: Path) -> None:
        """Create .gitignore"""
        content = '''# GraphBus
.graphbus/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env
.venv
env/
venv/
ENV/
'''
        self._write_file(project_path / ".gitignore", content)

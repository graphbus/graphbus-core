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

from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, method, subscribes


@agent(
    name="HelloAgent",
    description="Generates personalized greetings"
)
class HelloAgent(NodeBase):
    """Agent that generates greetings"""

    def __init__(self):
        super().__init__()
        self.greeting_count = 0

    @method(
        description="Generate a greeting message",
        parameters={"name": "str"},
        return_type="str"
    )
    def generate_greeting(self, name: str) -> str:
        """Generate a personalized greeting"""
        self.greeting_count += 1
        return f"Hello, {name}! This is greeting #{self.greeting_count}"

    @subscribes("/system/start")
    def on_system_start(self, payload):
        """Handle system start event"""
        self.publish("/hello/ready", {"agent": "HelloAgent", "status": "ready"})
'''
        self._write_file(project_path / "agents" / "hello_agent.py", content)

    def _create_processor_agent(self, project_path: Path) -> None:
        """Create ProcessorAgent"""
        content = '''"""
Processor Agent - Processes greetings
"""

from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, method, subscribes


@agent(
    name="ProcessorAgent",
    description="Processes and transforms greetings"
)
class ProcessorAgent(NodeBase):
    """Agent that processes greetings"""

    @subscribes("/hello/ready")
    def on_hello_ready(self, payload):
        """Handle hello ready event"""
        print(f"Received: {payload}")
        self.publish("/processor/ready", {"agent": "ProcessorAgent", "status": "ready"})

    @method(
        description="Process a greeting message",
        parameters={"message": "str"},
        return_type="str"
    )
    def process(self, message: str) -> str:
        """Process and transform a greeting"""
        return message.upper()
'''
        self._write_file(project_path / "agents" / "processor_agent.py", content)

    def _create_logger_agent(self, project_path: Path) -> None:
        """Create LoggerAgent"""
        content = '''"""
Logger Agent - Logs messages
"""

from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, subscribes


@agent(
    name="LoggerAgent",
    description="Logs all system events"
)
class LoggerAgent(NodeBase):
    """Agent that logs events"""

    def __init__(self):
        super().__init__()
        self.log_count = 0

    @subscribes("/hello/ready")
    @subscribes("/processor/ready")
    def on_agent_ready(self, payload):
        """Log when agents become ready"""
        self.log_count += 1
        agent_name = payload.get("agent", "Unknown")
        print(f"[LOG #{self.log_count}] Agent ready: {agent_name}")
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

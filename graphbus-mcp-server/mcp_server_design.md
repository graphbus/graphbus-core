# GraphBus MCP Server - Complete Design

## Overview

The GraphBus MCP server exposes the entire GraphBus CLI as MCP tools, allowing Claude Code to interact with GraphBus naturally through conversation.

---

## MCP Tools - Complete CLI Mapping

### Core Commands

#### 1. graphbus_build
```json
{
  "name": "graphbus_build",
  "description": "Build GraphBus agents from source directory. Discovers agents, validates them, and generates runtime artifacts in .graphbus/",
  "inputSchema": {
    "type": "object",
    "properties": {
      "agents_dir": {
        "type": "string",
        "description": "Directory containing agent source files"
      },
      "output_dir": {
        "type": "string",
        "description": "Output directory for artifacts (default: .graphbus)",
        "default": ".graphbus"
      },
      "validate": {
        "type": "boolean",
        "description": "Validate agents after build",
        "default": false
      },
      "verbose": {
        "type": "boolean",
        "description": "Verbose output",
        "default": false
      }
    },
    "required": ["agents_dir"]
  }
}
```

#### 2. graphbus_run
```json
{
  "name": "graphbus_run",
  "description": "Run GraphBus runtime from built artifacts. Starts the message bus and all agents.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "artifacts_dir": {
        "type": "string",
        "description": "Directory containing .graphbus artifacts"
      },
      "interactive": {
        "type": "boolean",
        "description": "Start interactive REPL",
        "default": false
      },
      "no_message_bus": {
        "type": "boolean",
        "description": "Disable message bus",
        "default": false
      },
      "enable_state_persistence": {
        "type": "boolean",
        "description": "Enable state persistence",
        "default": false
      },
      "enable_hot_reload": {
        "type": "boolean",
        "description": "Enable hot reload",
        "default": false
      },
      "enable_health_monitoring": {
        "type": "boolean",
        "description": "Enable health monitoring",
        "default": false
      },
      "debug": {
        "type": "boolean",
        "description": "Enable debugger",
        "default": false
      },
      "verbose": {
        "type": "boolean",
        "description": "Verbose output",
        "default": false
      }
    },
    "required": ["artifacts_dir"]
  }
}
```

#### 3. graphbus_inspect
```json
{
  "name": "graphbus_inspect",
  "description": "Inspect GraphBus artifacts without running. Shows agents, topics, subscriptions, and graph structure.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "artifacts_dir": {
        "type": "string",
        "description": "Directory containing .graphbus artifacts"
      },
      "show_graph": {
        "type": "boolean",
        "description": "Display graph structure",
        "default": false
      },
      "show_agents": {
        "type": "boolean",
        "description": "List all agents",
        "default": false
      },
      "show_topics": {
        "type": "boolean",
        "description": "List all topics",
        "default": false
      },
      "show_subscriptions": {
        "type": "boolean",
        "description": "Show subscription mappings",
        "default": false
      },
      "agent": {
        "type": "string",
        "description": "Show detailed info for specific agent"
      },
      "format": {
        "type": "string",
        "enum": ["json", "yaml", "table"],
        "description": "Output format",
        "default": "table"
      }
    },
    "required": ["artifacts_dir"]
  }
}
```

#### 4. graphbus_validate
```json
{
  "name": "graphbus_validate",
  "description": "Validate agent definitions before building. Checks for common issues, cycles, and type errors.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "agents_dir": {
        "type": "string",
        "description": "Directory containing agent source files"
      },
      "strict": {
        "type": "boolean",
        "description": "Enable strict validation",
        "default": false
      },
      "check_types": {
        "type": "boolean",
        "description": "Validate type annotations",
        "default": false
      },
      "check_cycles": {
        "type": "boolean",
        "description": "Check for dependency cycles",
        "default": false
      }
    },
    "required": ["agents_dir"]
  }
}
```

### Project Management

#### 5. graphbus_init
```json
{
  "name": "graphbus_init",
  "description": "Initialize a new GraphBus project from template. Creates project structure with example agents.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "project_name": {
        "type": "string",
        "description": "Name of the project to create"
      },
      "template": {
        "type": "string",
        "enum": ["basic", "microservices", "etl", "chatbot", "workflow"],
        "description": "Project template to use",
        "default": "basic"
      },
      "output_dir": {
        "type": "string",
        "description": "Parent directory for project",
        "default": "."
      },
      "force": {
        "type": "boolean",
        "description": "Overwrite if exists",
        "default": false
      }
    },
    "required": ["project_name"]
  }
}
```

#### 6. graphbus_generate
```json
{
  "name": "graphbus_generate",
  "description": "Generate agent boilerplate code from specification. Creates agent class with methods, subscriptions, and tests.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "entity_type": {
        "type": "string",
        "enum": ["agent"],
        "description": "Type of entity to generate",
        "default": "agent"
      },
      "name": {
        "type": "string",
        "description": "Name of the agent (PascalCase)"
      },
      "output_dir": {
        "type": "string",
        "description": "Output directory",
        "default": "agents"
      },
      "methods": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Method names to generate"
      },
      "subscribes": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Topics to subscribe to"
      },
      "publishes": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Topics this agent publishes"
      },
      "with_llm": {
        "type": "boolean",
        "description": "Include LLM client integration",
        "default": false
      },
      "with_state": {
        "type": "boolean",
        "description": "Include state management",
        "default": false
      }
    },
    "required": ["name"]
  }
}
```

#### 7. graphbus_quickstart
```json
{
  "name": "graphbus_quickstart",
  "description": "Interactive quickstart wizard. Guides user through creating a new GraphBus project.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "non_interactive": {
        "type": "boolean",
        "description": "Skip interactive prompts, use defaults",
        "default": false
      },
      "project_name": {
        "type": "string",
        "description": "Project name (for non-interactive mode)"
      },
      "template": {
        "type": "string",
        "description": "Template name (for non-interactive mode)"
      }
    }
  }
}
```

### Development & Debugging

#### 8. graphbus_profile
```json
{
  "name": "graphbus_profile",
  "description": "Profile GraphBus runtime performance. Identifies bottlenecks and slow methods.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "artifacts_dir": {
        "type": "string",
        "description": "Directory containing .graphbus artifacts"
      },
      "duration": {
        "type": "integer",
        "description": "Profiling duration in seconds",
        "default": 60
      },
      "output": {
        "type": "string",
        "description": "Output file for report"
      },
      "format": {
        "type": "string",
        "enum": ["text", "json", "html"],
        "description": "Report format",
        "default": "text"
      },
      "threshold_ms": {
        "type": "number",
        "description": "Bottleneck threshold in milliseconds",
        "default": 100
      }
    },
    "required": ["artifacts_dir"]
  }
}
```

#### 9. graphbus_dashboard
```json
{
  "name": "graphbus_dashboard",
  "description": "Start web-based visualization dashboard. Shows real-time agent graph and metrics.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "artifacts_dir": {
        "type": "string",
        "description": "Directory containing .graphbus artifacts"
      },
      "port": {
        "type": "integer",
        "description": "Dashboard port",
        "default": 8080
      },
      "no_browser": {
        "type": "boolean",
        "description": "Don't open browser automatically",
        "default": false
      }
    },
    "required": ["artifacts_dir"]
  }
}
```

### Deployment

#### 10. graphbus_docker
```json
{
  "name": "graphbus_docker",
  "description": "Docker containerization commands. Generate Dockerfiles, build images, run containers.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "subcommand": {
        "type": "string",
        "enum": ["generate", "build", "run", "compose"],
        "description": "Docker subcommand"
      },
      "artifacts_dir": {
        "type": "string",
        "description": "Directory containing .graphbus artifacts"
      },
      "image_name": {
        "type": "string",
        "description": "Docker image name"
      },
      "tag": {
        "type": "string",
        "description": "Image tag",
        "default": "latest"
      },
      "python_version": {
        "type": "string",
        "description": "Python version for image",
        "default": "3.11"
      },
      "port": {
        "type": "integer",
        "description": "Container port",
        "default": 8080
      }
    },
    "required": ["subcommand", "artifacts_dir"]
  }
}
```

#### 11. graphbus_k8s
```json
{
  "name": "graphbus_k8s",
  "description": "Kubernetes deployment commands. Generate manifests, deploy to cluster, check status.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "subcommand": {
        "type": "string",
        "enum": ["generate", "apply", "status", "logs"],
        "description": "Kubernetes subcommand"
      },
      "artifacts_dir": {
        "type": "string",
        "description": "Directory containing .graphbus artifacts"
      },
      "namespace": {
        "type": "string",
        "description": "Kubernetes namespace",
        "default": "default"
      },
      "replicas": {
        "type": "integer",
        "description": "Number of replicas",
        "default": 3
      },
      "output_dir": {
        "type": "string",
        "description": "Output directory for manifests",
        "default": "k8s"
      }
    },
    "required": ["subcommand", "artifacts_dir"]
  }
}
```

#### 12. graphbus_ci
```json
{
  "name": "graphbus_ci",
  "description": "Generate CI/CD pipeline configurations. Supports GitHub Actions, GitLab CI, Jenkins.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "provider": {
        "type": "string",
        "enum": ["github", "gitlab", "jenkins"],
        "description": "CI/CD provider"
      },
      "output_dir": {
        "type": "string",
        "description": "Output directory for CI config",
        "default": "."
      },
      "enable_docker": {
        "type": "boolean",
        "description": "Include Docker build steps",
        "default": false
      },
      "enable_k8s": {
        "type": "boolean",
        "description": "Include Kubernetes deployment",
        "default": false
      }
    },
    "required": ["provider"]
  }
}
```

### State & Runtime Management

#### 13. graphbus_state
```json
{
  "name": "graphbus_state",
  "description": "Manage agent state. View, save, load, or clear agent state.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "subcommand": {
        "type": "string",
        "enum": ["list", "get", "set", "clear", "save", "load"],
        "description": "State management subcommand"
      },
      "artifacts_dir": {
        "type": "string",
        "description": "Directory containing .graphbus artifacts"
      },
      "agent": {
        "type": "string",
        "description": "Agent name"
      },
      "key": {
        "type": "string",
        "description": "State key"
      },
      "value": {
        "type": "string",
        "description": "State value (JSON)"
      }
    },
    "required": ["subcommand"]
  }
}
```

### Contract & Schema Management

#### 14. graphbus_contract
```json
{
  "name": "graphbus_contract",
  "description": "Manage API contracts and schema versions. Register, validate, diff, and analyze impact.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "subcommand": {
        "type": "string",
        "enum": ["register", "list", "validate", "diff", "impact"],
        "description": "Contract management subcommand"
      },
      "agent": {
        "type": "string",
        "description": "Agent name"
      },
      "version": {
        "type": "string",
        "description": "Contract version (semver)"
      },
      "other_agent": {
        "type": "string",
        "description": "Other agent for validation"
      },
      "from_version": {
        "type": "string",
        "description": "Start version for diff"
      },
      "to_version": {
        "type": "string",
        "description": "End version for diff"
      },
      "schema_file": {
        "type": "string",
        "description": "Schema definition file"
      }
    },
    "required": ["subcommand"]
  }
}
```

#### 15. graphbus_migrate
```json
{
  "name": "graphbus_migrate",
  "description": "Manage schema migrations. Create, plan, apply, rollback, and check status.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "subcommand": {
        "type": "string",
        "enum": ["create", "plan", "apply", "rollback", "status", "validate"],
        "description": "Migration subcommand"
      },
      "agent": {
        "type": "string",
        "description": "Agent name"
      },
      "from_version": {
        "type": "string",
        "description": "Source version"
      },
      "to_version": {
        "type": "string",
        "description": "Target version"
      },
      "migration_id": {
        "type": "string",
        "description": "Migration ID for rollback"
      }
    },
    "required": ["subcommand"]
  }
}
```

#### 16. graphbus_coherence
```json
{
  "name": "graphbus_coherence",
  "description": "Track long-form coherence. Check schema consistency, detect drift, generate reports.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "subcommand": {
        "type": "string",
        "enum": ["check", "report", "drift", "visualize"],
        "description": "Coherence subcommand"
      },
      "artifacts_dir": {
        "type": "string",
        "description": "Directory containing .graphbus artifacts"
      },
      "time_window": {
        "type": "integer",
        "description": "Time window in hours for drift detection",
        "default": 24
      },
      "format": {
        "type": "string",
        "enum": ["text", "json", "html"],
        "description": "Report format",
        "default": "text"
      },
      "output": {
        "type": "string",
        "description": "Output file"
      }
    },
    "required": ["subcommand"]
  }
}
```

### Utility Commands

#### 17. graphbus_list_templates
```json
{
  "name": "graphbus_list_templates",
  "description": "List available project templates with descriptions and features.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "format": {
        "type": "string",
        "enum": ["table", "json"],
        "description": "Output format",
        "default": "table"
      }
    }
  }
}
```

#### 18. graphbus_doctor
```json
{
  "name": "graphbus_doctor",
  "description": "Run diagnostic checks on GraphBus installation and project. Checks dependencies, configuration, and common issues.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "project_dir": {
        "type": "string",
        "description": "Project directory to check",
        "default": "."
      },
      "fix": {
        "type": "boolean",
        "description": "Attempt to fix issues automatically",
        "default": false
      }
    }
  }
}
```

#### 19. graphbus_version
```json
{
  "name": "graphbus_version",
  "description": "Show GraphBus version information.",
  "inputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

### Runtime Interaction (for running instances)

#### 20. graphbus_call
```json
{
  "name": "graphbus_call",
  "description": "Call an agent method on a running GraphBus instance (REPL mode).",
  "inputSchema": {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string",
        "description": "Runtime session ID"
      },
      "agent": {
        "type": "string",
        "description": "Agent name"
      },
      "method": {
        "type": "string",
        "description": "Method name"
      },
      "args": {
        "type": "object",
        "description": "Method arguments"
      }
    },
    "required": ["session_id", "agent", "method"]
  }
}
```

#### 21. graphbus_publish
```json
{
  "name": "graphbus_publish",
  "description": "Publish an event to a running GraphBus instance (REPL mode).",
  "inputSchema": {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string",
        "description": "Runtime session ID"
      },
      "topic": {
        "type": "string",
        "description": "Topic to publish to"
      },
      "payload": {
        "type": "object",
        "description": "Event payload"
      }
    },
    "required": ["session_id", "topic", "payload"]
  }
}
```

#### 22. graphbus_stats
```json
{
  "name": "graphbus_stats",
  "description": "Get runtime statistics from a running GraphBus instance.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string",
        "description": "Runtime session ID"
      }
    },
    "required": ["session_id"]
  }
}
```

#### 23. graphbus_load_example
```json
{
  "name": "graphbus_load_example",
  "description": "Load a pre-built example project. Creates a working directory with example agents.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "example": {
        "type": "string",
        "enum": [
          "hello-world",
          "order-processing",
          "chatbot",
          "data-pipeline",
          "api-gateway",
          "event-sourcing",
          "saga-pattern",
          "circuit-breaker"
        ],
        "description": "Example to load"
      },
      "output_dir": {
        "type": "string",
        "description": "Output directory",
        "default": "."
      }
    },
    "required": ["example"]
  }
}
```

---

## MCP Server Implementation

### Directory Structure
```
graphbus-mcp/
├── src/
│   ├── graphbus_mcp/
│   │   ├── __init__.py
│   │   ├── server.py          # Main MCP server
│   │   ├── tools/             # Tool implementations
│   │   │   ├── __init__.py
│   │   │   ├── core.py        # build, run, inspect, validate
│   │   │   ├── project.py     # init, generate, quickstart
│   │   │   ├── debug.py       # profile, dashboard
│   │   │   ├── deploy.py      # docker, k8s, ci
│   │   │   ├── state.py       # state management
│   │   │   ├── contract.py    # contract, migrate, coherence
│   │   │   ├── runtime.py     # call, publish, stats
│   │   │   └── utility.py     # doctor, version, templates
│   │   ├── session.py         # Session management
│   │   ├── formatters.py      # Output formatting
│   │   └── examples.py        # Example loader
│   └── tests/
├── examples/                   # Pre-built examples
│   ├── hello-world/
│   ├── order-processing/
│   └── ...
├── pyproject.toml
├── README.md
└── LICENSE
```

### Key Implementation Files

#### `server.py` - Main MCP Server
```python
"""
GraphBus MCP Server
Exposes GraphBus CLI as MCP tools for Claude Code
"""
import asyncio
from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from .tools import (
    core_tools,
    project_tools,
    debug_tools,
    deploy_tools,
    state_tools,
    contract_tools,
    runtime_tools,
    utility_tools
)
from .session import SessionManager

app = Server("graphbus-mcp")
sessions = SessionManager()

# Register all tools
ALL_TOOLS = [
    *core_tools.TOOLS,
    *project_tools.TOOLS,
    *debug_tools.TOOLS,
    *deploy_tools.TOOLS,
    *state_tools.TOOLS,
    *contract_tools.TOOLS,
    *runtime_tools.TOOLS,
    *utility_tools.TOOLS
]

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available GraphBus tools"""
    return ALL_TOOLS

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a GraphBus tool"""
    # Route to appropriate handler
    if name.startswith("graphbus_"):
        handler = get_tool_handler(name)
        result = await handler(arguments, sessions)
        return [TextContent(type="text", text=result)]

    raise ValueError(f"Unknown tool: {name}")

def get_tool_handler(tool_name: str):
    """Get handler function for tool"""
    # Map tool names to handlers
    handlers = {
        "graphbus_build": core_tools.handle_build,
        "graphbus_run": core_tools.handle_run,
        # ... map all 23 tools
    }
    return handlers[tool_name]

async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
```

#### `session.py` - Session Management
```python
"""
Manage GraphBus runtime sessions
Allows multiple concurrent runtimes per user
"""
import uuid
from typing import Dict, Optional
from graphbus_core.runtime.executor import RuntimeExecutor
from graphbus_core.config import RuntimeConfig

class Session:
    def __init__(self, session_id: str, artifacts_dir: str):
        self.session_id = session_id
        self.artifacts_dir = artifacts_dir
        self.executor: Optional[RuntimeExecutor] = None
        self.config: Optional[RuntimeConfig] = None

    def start(self, config: RuntimeConfig):
        """Start GraphBus runtime"""
        self.config = config
        self.executor = RuntimeExecutor(config)
        self.executor.start()

    def stop(self):
        """Stop GraphBus runtime"""
        if self.executor:
            self.executor.stop()
            self.executor = None

    def is_running(self) -> bool:
        """Check if runtime is running"""
        return self.executor is not None and self.executor.is_running

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}

    def create_session(self, artifacts_dir: str) -> str:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = Session(session_id, artifacts_dir)
        return session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get existing session"""
        return self.sessions.get(session_id)

    def close_session(self, session_id: str):
        """Close and cleanup session"""
        session = self.sessions.get(session_id)
        if session:
            session.stop()
            del self.sessions[session_id]
```

#### `tools/core.py` - Core Command Handlers
```python
"""
Core GraphBus commands: build, run, inspect, validate
"""
from typing import Any, Dict
from graphbus_cli.commands.build import build as cli_build
from graphbus_cli.commands.run import run as cli_run
from graphbus_cli.commands.inspect import inspect as cli_inspect
from graphbus_cli.commands.validate import validate as cli_validate
from ..formatters import format_build_output, format_runtime_output

async def handle_build(args: Dict[str, Any], sessions) -> str:
    """Handle graphbus build command"""
    try:
        # Run build command
        result = cli_build(
            agents_dir=args["agents_dir"],
            output_dir=args.get("output_dir", ".graphbus"),
            validate=args.get("validate", False),
            verbose=args.get("verbose", False),
            _return_result=True  # Return result instead of printing
        )

        return format_build_output(result)

    except Exception as e:
        return f"Error building: {str(e)}\n\nTroubleshooting tips:\n- Check agent syntax\n- Ensure all decorators are present\n- Run 'graphbus validate' first"

async def handle_run(args: Dict[str, Any], sessions) -> str:
    """Handle graphbus run command"""
    try:
        # Create session
        session_id = sessions.create_session(args["artifacts_dir"])
        session = sessions.get_session(session_id)

        # Configure runtime
        from graphbus_core.config import RuntimeConfig
        config = RuntimeConfig(
            artifacts_dir=args["artifacts_dir"],
            enable_message_bus=not args.get("no_message_bus", False),
            enable_state_persistence=args.get("enable_state_persistence", False),
            enable_hot_reload=args.get("enable_hot_reload", False),
            enable_health_monitoring=args.get("enable_health_monitoring", False),
            verbose=args.get("verbose", False)
        )

        # Start runtime
        session.start(config)

        output = f"✓ GraphBus runtime started\n"
        output += f"Session ID: {session_id}\n\n"
        output += f"Loaded agents:\n"
        for agent_name in session.executor.get_all_nodes().keys():
            output += f"  - {agent_name}\n"

        output += f"\nUse this session_id to interact with the runtime:\n"
        output += f"  - graphbus_call(session_id=\"{session_id}\", agent=\"...\", method=\"...\")\n"
        output += f"  - graphbus_publish(session_id=\"{session_id}\", topic=\"...\", payload={{...}})\n"
        output += f"  - graphbus_stats(session_id=\"{session_id}\")\n"

        return output

    except Exception as e:
        return f"Error starting runtime: {str(e)}"

# ... handle_inspect, handle_validate
```

---

## Installation Process

### 1. Development Installation

#### Setup Script - `install_dev.sh`
```bash
#!/bin/bash
# Development installation for GraphBus MCP Server

set -e

echo "Installing GraphBus MCP Server (Development Mode)..."

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.9+ required (found $python_version)"
    exit 1
fi

# Install GraphBus core and CLI first
echo "Installing GraphBus core..."
pip install -e ../graphbus-core
pip install -e ../graphbus-cli

# Install MCP server in development mode
echo "Installing GraphBus MCP server..."
pip install -e .

# Install MCP dependencies
echo "Installing MCP dependencies..."
pip install mcp

# Verify installation
echo "Verifying installation..."
python3 -c "import graphbus_mcp; print(f'✓ GraphBus MCP {graphbus_mcp.__version__} installed')"

echo ""
echo "✓ Installation complete!"
echo ""
echo "To register with Claude Code, add to your MCP settings:"
echo ""
echo '{
  "mcpServers": {
    "graphbus": {
      "command": "python3",
      "args": ["-m", "graphbus_mcp"],
      "description": "GraphBus multi-agent system toolkit"
    }
  }
}'
echo ""
echo "MCP settings location:"
echo "  macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "  Linux: ~/.config/Claude/claude_desktop_config.json"
echo "  Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
```

### 2. System Installation

#### System Install Script - `install.sh`
```bash
#!/bin/bash
# System installation for GraphBus MCP Server

set -e

echo "Installing GraphBus MCP Server (System-wide)..."

# Install from PyPI
pip install graphbus-mcp

# Auto-configure Claude Code (if installed)
if command -v claude &> /dev/null; then
    echo "Configuring Claude Code integration..."
    python3 -m graphbus_mcp.configure
else
    echo ""
    echo "✓ Installation complete!"
    echo ""
    echo "To use with Claude Code, add to your MCP settings:"
    echo ""
    echo '{
  "mcpServers": {
    "graphbus": {
      "command": "python3",
      "args": ["-m", "graphbus_mcp"],
      "description": "GraphBus multi-agent system toolkit"
    }
  }
}'
fi
```

### 3. Auto-configuration Script

#### `graphbus_mcp/configure.py` - Auto-configure Claude
```python
"""
Auto-configure GraphBus MCP server with Claude Code
"""
import json
import os
import sys
from pathlib import Path

def get_claude_config_path():
    """Get Claude Code config path for current platform"""
    if sys.platform == "darwin":  # macOS
        return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    elif sys.platform == "linux":
        return Path.home() / ".config/Claude/claude_desktop_config.json"
    elif sys.platform == "win32":
        return Path(os.getenv("APPDATA")) / "Claude/claude_desktop_config.json"
    else:
        raise OSError(f"Unsupported platform: {sys.platform}")

def configure():
    """Add GraphBus MCP server to Claude Code configuration"""
    config_path = get_claude_config_path()

    # Create config directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {}

    # Add GraphBus MCP server
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["graphbus"] = {
        "command": "python3",
        "args": ["-m", "graphbus_mcp"],
        "description": "GraphBus multi-agent system toolkit"
    }

    # Save config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✓ Configured GraphBus MCP server at {config_path}")
    print("\nRestart Claude Code to activate.")

if __name__ == "__main__":
    configure()
```

---

## PyPI Publishing Process

### 1. Package Configuration

#### `pyproject.toml`
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "graphbus-mcp"
version = "1.0.0"
description = "MCP server for GraphBus - Multi-agent orchestration toolkit"
readme = "README.md"
license = {text = "Apache-2.0"}
authors = [
    {name = "GraphBus Team", email = "team@graphbus.dev"}
]
keywords = ["graphbus", "mcp", "claude", "agents", "multi-agent", "orchestration"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
    "Topic :: System :: Distributed Computing",
]
requires-python = ">=3.9"
dependencies = [
    "graphbus-core>=1.0.0",
    "graphbus-cli>=1.0.0",
    "mcp>=0.5.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "black>=23.0",
    "ruff>=0.1.0",
    "mypy>=1.0",
]

[project.urls]
Homepage = "https://graphbus.dev"
Documentation = "https://docs.graphbus.dev"
Repository = "https://github.com/graphbus/graphbus-mcp"
"Bug Tracker" = "https://github.com/graphbus/graphbus-mcp/issues"

[project.scripts]
graphbus-mcp = "graphbus_mcp.server:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
graphbus_mcp = ["examples/**/*"]
```

### 2. Publishing Script

#### `scripts/publish.sh`
```bash
#!/bin/bash
# Publish GraphBus MCP to PyPI

set -e

echo "Publishing GraphBus MCP to PyPI..."

# Check we're on main branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    echo "Error: Must be on main branch to publish"
    exit 1
fi

# Check working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Working directory has uncommitted changes"
    exit 1
fi

# Run tests
echo "Running tests..."
pytest

# Build package
echo "Building package..."
rm -rf dist/
python3 -m build

# Check package
echo "Checking package..."
twine check dist/*

# Confirm publish
echo ""
read -p "Publish to PyPI? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted"
    exit 0
fi

# Publish to PyPI
echo "Publishing to PyPI..."
twine upload dist/*

# Get version
version=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")

# Tag release
echo "Creating git tag v${version}..."
git tag -a "v${version}" -m "Release v${version}"
git push origin "v${version}"

echo ""
echo "✓ Published graphbus-mcp ${version} to PyPI!"
echo ""
echo "Install with: pip install graphbus-mcp"
```

### 3. TestPyPI Testing

#### `scripts/publish_test.sh`
```bash
#!/bin/bash
# Publish to TestPyPI for testing

set -e

echo "Publishing GraphBus MCP to TestPyPI..."

# Build package
echo "Building package..."
rm -rf dist/
python3 -m build

# Publish to TestPyPI
echo "Publishing to TestPyPI..."
twine upload --repository testpypi dist/*

version=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")

echo ""
echo "✓ Published to TestPyPI!"
echo ""
echo "Test installation:"
echo "  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ graphbus-mcp==${version}"
```

### 4. Release Checklist

#### `RELEASE_CHECKLIST.md`
```markdown
# Release Checklist

Before releasing a new version of GraphBus MCP:

## Pre-release
- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in pyproject.toml
- [ ] No uncommitted changes
- [ ] On main branch

## Testing
- [ ] Test with TestPyPI
- [ ] Verify installation from TestPyPI
- [ ] Test MCP server with Claude Code
- [ ] Run all 23 tools manually
- [ ] Check examples load correctly

## Release
- [ ] Run `scripts/publish.sh`
- [ ] Verify on PyPI
- [ ] Test `pip install graphbus-mcp`
- [ ] Create GitHub release
- [ ] Update documentation site
- [ ] Announce on social media

## Post-release
- [ ] Monitor issue tracker
- [ ] Check download stats
- [ ] Gather user feedback
- [ ] Plan next version
```

---

## Usage Examples

### Example 1: First-time User
```
User: I want to build an order processing system with GraphBus

Claude: Great! Let me help you get started. I'll use the GraphBus MCP tools
to create a complete order processing system.

[Uses graphbus_quickstart]

I've created a new project called "order-system" with the microservices template.
It includes three agents:

1. OrderService - Receives and validates orders
2. PaymentService - Processes payments
3. ShipmentService - Handles shipping

Let me show you the structure...

[Uses graphbus_inspect]

Now let's build it:

[Uses graphbus_build]

✓ Build successful! Would you like to run it and see it in action?
```

### Example 2: Debugging Help
```
User: My agent isn't receiving events, can you help debug?

Claude: I'll help you diagnose this. Let me inspect your GraphBus setup.

[Uses graphbus_validate to check for issues]
[Uses graphbus_inspect with show_subscriptions=true]

I found the issue! Your PaymentService is subscribed to "/order/validated"
but OrderService is publishing to "/orders/validated" (with an 's').

Let me check the contract to confirm...

[Uses graphbus_contract with subcommand="list"]

I can fix this for you. Should I update the subscription to match?
```

### Example 3: Deployment
```
User: How do I deploy this to Kubernetes?

Claude: I'll help you deploy to Kubernetes. Let me generate the manifests:

[Uses graphbus_k8s with subcommand="generate"]

I've generated Kubernetes manifests with:
- Deployment with 3 replicas
- Service (ClusterIP)
- ConfigMap for configuration
- Horizontal Pod Autoscaler

Now let me create a Docker image first:

[Uses graphbus_docker with subcommand="generate"]
[Uses graphbus_docker with subcommand="build"]

✓ Docker image built: order-system:latest

Ready to deploy! Run this to apply to your cluster:
  kubectl apply -f k8s/

Or I can do it for you with:
[Shows graphbus_k8s with subcommand="apply"]
```

---

## Testing the MCP Server

### Test Script - `test_mcp_server.py`
```python
"""
Test GraphBus MCP server
"""
import pytest
from graphbus_mcp.server import app
from mcp.types import CallToolRequest

@pytest.mark.asyncio
async def test_list_tools():
    """Test listing all tools"""
    tools = await app.list_tools()
    assert len(tools) == 23  # All CLI commands

    # Check key tools exist
    tool_names = [t.name for t in tools]
    assert "graphbus_build" in tool_names
    assert "graphbus_run" in tool_names
    assert "graphbus_init" in tool_names

@pytest.mark.asyncio
async def test_build_command():
    """Test graphbus build via MCP"""
    result = await app.call_tool(
        "graphbus_build",
        {"agents_dir": "examples/hello-world/agents"}
    )

    assert "✓" in result[0].text
    assert "agents" in result[0].text.lower()

@pytest.mark.asyncio
async def test_load_example():
    """Test loading example"""
    result = await app.call_tool(
        "graphbus_load_example",
        {"example": "hello-world", "output_dir": "/tmp/test"}
    )

    assert "✓" in result[0].text

# ... more tests for all 23 tools
```

---

## Documentation

### README.md for MCP Server
```markdown
# GraphBus MCP Server

Model Context Protocol server for GraphBus - enables Claude Code to interact with GraphBus naturally.

## Installation

```bash
pip install graphbus-mcp
```

## Configuration

Add to Claude Code MCP settings:

```json
{
  "mcpServers": {
    "graphbus": {
      "command": "python3",
      "args": ["-m", "graphbus_mcp"],
      "description": "GraphBus multi-agent system toolkit"
    }
  }
}
```

## Usage

Once configured, just talk to Claude Code about GraphBus:

- "Create a new GraphBus project for order processing"
- "Build my GraphBus agents"
- "Show me the agent graph"
- "Deploy my agents to Kubernetes"
- "Debug why my agent isn't receiving events"

Claude will use the MCP tools automatically.

## Available Tools

All GraphBus CLI commands are available as MCP tools:

### Core Commands
- `graphbus_build` - Build agents
- `graphbus_run` - Run runtime
- `graphbus_inspect` - Inspect artifacts
- `graphbus_validate` - Validate agents

### Project Management
- `graphbus_init` - Initialize project
- `graphbus_generate` - Generate agent code
- `graphbus_quickstart` - Quick start wizard

### Development
- `graphbus_profile` - Performance profiling
- `graphbus_dashboard` - Web dashboard
- `graphbus_doctor` - Diagnostic checks

### Deployment
- `graphbus_docker` - Docker commands
- `graphbus_k8s` - Kubernetes commands
- `graphbus_ci` - CI/CD generation

### Advanced
- `graphbus_contract` - Contract management
- `graphbus_migrate` - Schema migrations
- `graphbus_coherence` - Coherence tracking
- `graphbus_state` - State management

And 5 more utility commands!

## Development

```bash
git clone https://github.com/graphbus/graphbus-mcp
cd graphbus-mcp
pip install -e ".[dev]"
pytest
```

## License

Apache 2.0
```

This comprehensive design gives Claude Code full access to all GraphBus functionality through natural conversation!
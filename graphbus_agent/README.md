# graphbus-agent

Headless agent SDK for GraphBus. Activates LLM agents to negotiate, propose, and commit code improvements — no API key required.

## Authentication

Uses your **Claude OAuth session** automatically. Resolution order:

1. `--token` / explicit argument
2. `GRAPHBUS_TOKEN` environment variable
3. `ANTHROPIC_API_KEY` environment variable
4. **OpenClaw credential store** (`~/.openclaw/agents/main/agent/auth-profiles.json`)
5. Claude CLI config (`~/.claude.json`)

If you're running OpenClaw or have Claude Code CLI installed and logged in, it just works.

---

## CLI

```bash
# Dry run — build the agent graph without LLM calls
graphbus-agent --package my_project.agents --dry-run

# Live run — agents negotiate and commit code changes
graphbus-agent \
  --package my_project.agents \
  --intent "Add input validation and structured error responses" \
  --output .graphbus/

# JSON output (for scripting)
graphbus-agent --package my_project.agents --intent "..." --json
```

### Options

| Flag | Description |
|------|-------------|
| `--package`, `-p` | Dotted Python package path containing `GraphBusNode` subclasses (required) |
| `--intent`, `-i` | Natural-language goal for the agents |
| `--output`, `-o` | Output dir for `.graphbus/` artifacts (default: `./.graphbus`) |
| `--token`, `-t` | Explicit Anthropic/Claude OAuth token |
| `--model` | Claude model alias (default: `sonnet`) |
| `--dry-run` | Skip LLM calls, just build the graph |
| `--json` | Print result as JSON |

---

## Python SDK

```python
from graphbus_agent import run_agents

result = run_agents(
    root_package="my_project.agents",
    intent="Add input validation and structured error responses",
)

if result.success:
    print(f"Artifacts: {result.artifacts_dir}")
    print(f"Modified:  {result.modified_files}")
else:
    print(f"Failed: {result.error}")
```

### `run_agents()`

```python
def run_agents(
    root_package: str,       # e.g. "my_project.agents"
    intent: str = None,      # natural-language goal
    output_dir: str = None,  # defaults to ./.graphbus
    token: str = None,       # auto-resolved if not set
    model: str = "sonnet",   # claude model alias
    dry_run: bool = False,   # skip LLM calls
) -> AgentRunResult
```

### `AgentRunResult`

```python
@dataclass
class AgentRunResult:
    success: bool
    package: str
    intent: str | None
    artifacts_dir: str
    agents_found: int
    agents_active: int
    modified_files: list[str]
    log: list[str]
    duration_s: float
    error: str | None
```

---

## How it works

```
graphbus-agent
  │
  ├── auth.py        Resolves Claude OAuth token from OpenClaw / env / CLI
  │
  ├── claude_client.py   ClaudeCLIClient — wraps `claude -p` subprocess
  │                      Emulates tool-use via JSON prompting
  │
  └── runner.py      Wires ClaudeCLIClient into the GraphBus build pipeline
                     Detects OAuth tokens (sk-ant-oat01-) and routes to CLI
```

**Build pipeline (from `graphbus_core`):**

1. Scan agent modules → find all `GraphBusNode` subclasses
2. Extract method schemas, pub/sub subscriptions, system prompts
3. Build dependency graph (networkx DAG)
4. Activate one LLM agent per class
5. Negotiation rounds: each agent proposes → others evaluate → arbiter resolves conflicts → commits applied
6. Emit `.graphbus/` artifacts (graph.json, agents.json, topics.json)

---

## Defining agents

Any Python class that subclasses `GraphBusNode` is an agent:

```python
from graphbus_core import GraphBusNode, schema_method, subscribe

class GreetingService(GraphBusNode):
    SYSTEM_PROMPT = "You generate personalised greeting messages."

    @schema_method(
        input_schema={"name": str},
        output_schema={"message": str},
    )
    def greet(self, name: str) -> dict:
        return {"message": f"Hello, {name}!"}

    @subscribe("/Greet/Sent")
    def on_greet_sent(self, event):
        print(f"Greeting sent: {event}")
```

---

## Requirements

- Python 3.10+
- `claude` CLI installed and authenticated (`npm install -g @anthropic-ai/claude-code`)
- OR: `ANTHROPIC_API_KEY` set
- OR: OpenClaw running with an Anthropic profile configured

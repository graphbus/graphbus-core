# GraphBus MCP Server

Model Context Protocol (MCP) server exposing all GraphBus CLI commands as tools for Claude Code integration.

## Architecture

### Core Concept: Thin Wrapper

The MCP server is a **thin wrapper around existing graphbus_cli commands**. It does NOT reimplement GraphBus functionality - it simply provides an MCP interface to the CLI that already exists.

```
┌─────────────────┐
│   Claude Code   │
└────────┬────────┘
         │ MCP Protocol
         ▼
┌─────────────────┐
│  MCP Server     │  ← Thin wrapper, translates MCP → CLI
│  (This module)  │
└────────┬────────┘
         │ Direct Python imports from graphbus_cli
         ▼
┌─────────────────┐
│  graphbus_cli   │  ← Existing CLI commands
│  (Already done) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ graphbus_core   │  ← Core runtime
└─────────────────┘
```

### MCP Server Responsibilities

1. **Expose CLI commands as MCP tools** - Each CLI command becomes an MCP tool
2. **Format output for Claude** - Make CLI output readable/parseable for Claude
3. **Manage sessions** - Track running runtime instances for graphbus_call/publish/stats
4. **Provide context** - Give Claude complete GraphBus architectural context

### What MCP Server Does NOT Do

- ❌ Reimplement `graphbus build` logic
- ❌ Reimplement `graphbus run` logic
- ❌ Duplicate any graphbus_core or graphbus_cli code
- ❌ Create separate package with its own logic

### Tool Naming Convention

MCP tools are named for Claude's convenience but directly call CLI:

- **MCP tool name**: `graphbus_build` (what Claude sees)
- **Implementation**: Calls `graphbus_cli.commands.build.build()` directly
- **CLI equivalent**: `graphbus build agents/`

This makes it clear that MCP tools map 1:1 to CLI commands.

## GraphBus Architecture Context

### Two-Phase Architecture: Build Mode vs Runtime Mode

#### **Build Mode** (Compile Time)
- **Purpose**: Analyze agent source code and generate executable artifacts
- **Input**: Python files with `@agent` decorated classes
- **Output**: `.graphbus/` directory with NetworkX serialized graphs
- **Commands**: `graphbus_build`, `graphbus_validate`, `graphbus_inspect`
- **Key Operation**: Static analysis, dependency resolution, graph construction

#### **Runtime Mode** (Execution Time)
- **Purpose**: Load artifacts and execute the agent system
- **Input**: `.graphbus/` artifacts from build phase
- **Output**: Running agent system with message bus
- **Commands**: `graphbus_run`, `graphbus_call`, `graphbus_publish`, `graphbus_stats`
- **Key Operation**: Dynamic execution, event routing, state management

**Critical Rule**: You must BUILD before you can RUN. Build creates the artifacts that Runtime loads.

### NetworkX DAG (Directed Acyclic Graph) System

GraphBus uses two different NetworkX graphs for different purposes:

#### **1. Agent Dependency Graph** (Build & Runtime)
- **Structure**: DAG where nodes = agents, edges = dependencies
- **Purpose**: Determine agent initialization order, validate no circular dependencies
- **Built During**: Build phase by analyzing `depends` parameter in `@agent` decorators
- **Used During**: Runtime initialization to start agents in correct order
- **NetworkX Operations**:
  ```python
  import networkx as nx

  # Check for cycles (invalid)
  if not nx.is_directed_acyclic_graph(dep_graph):
      raise Exception("Circular dependencies detected")

  # Get initialization order
  activation_order = list(nx.topological_sort(dep_graph))
  # If A depends on B, then B appears before A in activation_order
  ```

**Example Dependency Graph**:
```
OrderService (depends on PaymentService, ShipmentService)
    ↓
PaymentService (depends on nothing)
ShipmentService (depends on nothing)

Initialization order: [PaymentService, ShipmentService, OrderService]
```

#### **2. Event Flow Graph** (Runtime Only)
- **Structure**: Graph where nodes = agents, edges = topic subscriptions
- **Purpose**: Route events from publishers to subscribers
- **Built During**: Build phase by analyzing `@subscribes` and `@publishes` decorators
- **Used During**: Runtime message routing
- **NetworkX Operations**:
  ```python
  # Find all agents subscribed to a topic
  subscribers = event_graph.neighbors(topic)

  # Trace event flow paths
  paths = nx.all_simple_paths(event_graph, source_agent, target_agent)
  ```

**Example Event Flow**:
```
OrderService publishes '/order/created'
    ↓ (event flows through message bus)
    ├→ PaymentService subscribes to '/order/created'
    ├→ NotificationService subscribes to '/order/created'
    └→ AuditLogger subscribes to '/order/created'

All three subscribers receive the event concurrently
```

### Key Differences Between Graphs

| Aspect | Dependency Graph | Event Flow Graph |
|--------|------------------|------------------|
| **Purpose** | Initialization order | Event routing |
| **Edges Mean** | "A depends on B" | "A publishes, B subscribes" |
| **Constraint** | Must be acyclic (DAG) | Can have cycles (event loops) |
| **Direction** | Dependency direction | Message flow direction |
| **Used When** | Agent startup | Event delivery |

### Event-Driven Messaging

GraphBus uses publish-subscribe messaging:

1. **Topics**: Hierarchical topic names like `/order/created`, `/payment/completed`
2. **Publishers**: Agents that publish events to topics (via `@publishes` hint or `self.publish()`)
3. **Subscribers**: Agents with methods decorated with `@subscribes('/topic/name')`
4. **Message Bus**: Routes events from publishers to all subscribers concurrently
5. **Loose Coupling**: Publishers don't know subscribers, subscribers don't know publishers

**Event Flow Example**:
```python
# Publisher (OrderService)
@agent(name="OrderService")
class OrderService:
    def create_order(self, order_data):
        # Process order
        self.publish('/order/created', {'order_id': '123', ...})

# Subscriber (PaymentService)
@agent(name="PaymentService")
class PaymentService:
    @subscribes('/order/created')
    def handle_order_created(self, event_data):
        # Process payment for this order
        order_id = event_data['order_id']
```

### Command Sequencing Patterns

#### **New Project from Template**
```
graphbus_init
  → graphbus_build
  → graphbus_inspect (optional, to understand structure)
  → graphbus_run (get session_id)
  → graphbus_publish or graphbus_call
  → graphbus_stats
```

#### **Load and Explore Example**
```
graphbus_load_example
  → graphbus_build
  → graphbus_inspect (to understand example)
  → graphbus_run
  → graphbus_publish (trigger workflows)
  → graphbus_stats (see what happened)
```

#### **Add Agent to Existing Project**
```
graphbus_generate (create new agent)
  → [user implements business logic]
  → graphbus_validate (check for errors)
  → graphbus_build (regenerate artifacts)
  → graphbus_inspect (verify integration)
  → graphbus_run
```

#### **Troubleshooting**
```
graphbus_doctor (diagnose issues)
  → graphbus_validate (check code)
  → [user fixes issues]
  → graphbus_build
  → graphbus_run
```

#### **Modify and Rebuild**
```
[user modifies agent code]
  → graphbus_build (regenerate artifacts)
  → graphbus_inspect (verify changes)
  → graphbus_run
```

#### **Agent Orchestration During Build**
```
graphbus_build (with enable_agents=true)
  → graphbus_inspect_negotiation (review AI proposals)
  → graphbus_inspect (verify changes)
  → graphbus_run
```

#### **Agent Orchestration After Build**
```
graphbus_build (fast validation)
  → graphbus_negotiate (run AI enhancement)
  → graphbus_inspect_negotiation (review results)
  → [decide: accept or rollback]
  → graphbus_build (if changes accepted)
  → graphbus_run
```

### When to Use Which Command

#### **Build Mode Commands** (work with source code / artifacts)
- `graphbus_init` - Start new project from template
- `graphbus_generate` - Add new agent to existing project
- `graphbus_load_example` - Load pre-built example
- `graphbus_build` - Compile agents into artifacts (optional: enable agent orchestration)
- `graphbus_negotiate` - Run LLM agent negotiation after build
- `graphbus_inspect_negotiation` - View negotiation history and AI proposals
- `graphbus_validate` - Check code for errors before building
- `graphbus_inspect` - Examine artifacts (after build)
- `graphbus_doctor` - Diagnose installation/project issues

#### **Runtime Mode Commands** (work with running system)
- `graphbus_run` - Start runtime (returns session_id)
- `graphbus_call` - Invoke agent method directly (requires session_id)
- `graphbus_publish` - Publish event to message bus (requires session_id)
- `graphbus_stats` - Get runtime statistics (requires session_id)

#### **Deployment Commands** (package and deploy)
- `graphbus_docker` - Generate/build/run Docker containers
- `graphbus_k8s` - Deploy to Kubernetes
- `graphbus_ci` - Generate CI/CD pipelines

#### **Advanced Commands** (for production systems)
- `graphbus_contract` - API contract management
- `graphbus_migrate` - Schema migrations
- `graphbus_coherence` - Check system consistency
- `graphbus_state` - Manage persistent state
- `graphbus_profile` - Performance profiling
- `graphbus_dashboard` - Monitoring dashboard

## Directory Structure

```
graphbus-core/                      # Main GraphBus repository
├── graphbus_core/                  # Core runtime package
├── graphbus_cli/                   # CLI commands package
├── tests/                          # All tests
│   └── mcp/                        # MCP server tests
└── graphbus-mcp-server/            # MCP server module (this directory)
    ├── __init__.py
    ├── server.py                   # Main MCP server entry point
    ├── tools/                      # Tool implementations (thin wrappers)
    │   ├── __init__.py
    │   ├── core.py                 # build, run, inspect, validate
    │   ├── project.py              # init, generate, load_example
    │   ├── runtime.py              # call, publish, stats
    │   ├── deploy.py               # docker, k8s, ci
    │   ├── advanced.py             # contract, migrate, coherence, state
    │   └── monitoring.py           # profile, dashboard, doctor
    ├── session.py                  # Runtime session management
    ├── formatters.py               # Output formatting for Claude
    ├── examples/                   # Pre-built examples (optional)
    ├── mcp_tools.json              # Complete tool definitions
    └── README.md                   # This file
```

## Implementation Pattern

```python
# graphbus-mcp-server/tools/core.py

from graphbus_cli.commands.build import build as cli_build
from graphbus_cli.commands.run import run as cli_run

async def handle_build(args: Dict[str, Any], sessions) -> str:
    """
    MCP handler for graphbus build command.
    Simply calls the existing CLI function.
    """
    try:
        # Direct Python import (preferred - faster than subprocess)
        result = cli_build(
            agents_dir=args["agents_dir"],
            output_dir=args.get("output_dir", ".graphbus"),
            validate=args.get("validate", False),
            verbose=args.get("verbose", False)
        )
        return format_build_output(result)
    except Exception as e:
        return f"Error: {str(e)}"

async def handle_run(args: Dict[str, Any], sessions) -> str:
    """
    MCP handler for graphbus run command.

    Special case: Keep runtime alive for session,
    so we can't just call cli_run() directly. We:
    1. Start RuntimeExecutor
    2. Store it in sessions manager
    3. Return session_id
    """
    session_id = sessions.create_session(args["artifacts_dir"])
    session = sessions.get_session(session_id)

    # Start runtime (similar to cli_run but we keep reference)
    config = RuntimeConfig(artifacts_dir=args["artifacts_dir"], ...)
    session.executor = RuntimeExecutor(config)
    session.executor.start()

    return format_run_output(session_id, session.executor)
```

## Session Management

The ONLY exception to the thin wrapper pattern is `graphbus_run` session management:

**CLI behavior**:
```bash
$ graphbus run .graphbus --interactive
# Starts REPL, blocks, exits when user types 'exit'
```

**MCP behavior**:
```python
# Start runtime but DON'T block
# Keep runtime alive in background
# Return session_id to Claude
# Claude can call/publish using session_id
```

For `graphbus_run`, the MCP server:
1. Imports RuntimeExecutor directly from graphbus_core
2. Starts it without blocking
3. Stores it in SessionManager
4. Returns session_id to Claude

For all other commands: call CLI function, format output, return.

## LLM Agent Orchestration (Tranche 4.5)

GraphBus includes a **fully implemented LLM agent orchestration system** where each `@agent` class can become an active LLM participant that analyzes code, proposes improvements, and negotiates with other agents through multi-round collaboration. This enables AI-powered code review and iterative improvement during the build process.

### How It Works

1. **Agent Activation**: Each `@agent` class becomes an LLM-powered agent with its own context
2. **Analysis Phase**: Agents analyze their own code for potential improvements
3. **Proposal Phase**: Agents propose changes with detailed rationale
4. **Evaluation Phase**: Agents evaluate other agents' proposals (approve/reject with reasoning)
5. **Consensus**: Multi-round negotiation continues until convergence (no new proposals for N rounds)
6. **Commitment**: Accepted proposals are applied to source files
7. **History**: Complete negotiation history saved to `.graphbus/negotiations.json`

### Workflow Options

#### Option 1: Agent Orchestration During Build
```
graphbus_build
  agents_dir: "agents/"
  enable_agents: true
  llm_api_key: "sk-..."  # or use ANTHROPIC_API_KEY env var
  llm_model: "claude-sonnet-4-20250514"
  max_negotiation_rounds: 10
  max_proposals_per_agent: 5
  convergence_threshold: 2
  protected_files: ["*.json", "tests/*"]  # Safety: files agents can't modify

→ Builds artifacts AND runs agent negotiation in one command
→ Saves negotiation history to .graphbus/negotiations.json
```

#### Option 2: Separate Negotiation After Build
```
# First: Build without agent orchestration (fast)
graphbus_build
  agents_dir: "agents/"

# Then: Run agent negotiation as separate step
graphbus_negotiate
  artifacts_dir: ".graphbus"
  llm_api_key: "sk-..."
  rounds: 5
  llm_model: "claude-sonnet-4-20250514"

→ Separates build validation from AI enhancement
→ Useful for CI/CD: fast builds, optional negotiate for improvement
```

### Inspecting Negotiation History

After agent orchestration, view the complete history:

```
graphbus_inspect_negotiation
  artifacts_dir: ".graphbus"
  format: "table"  # or "timeline" or "json"

→ Shows proposals, evaluations, conflicts, commits
→ Filter by round number or agent name
→ Understand why proposals were accepted/rejected
```

**Output formats:**
- `table`: Summary statistics and key decisions in tables
- `timeline`: Chronological event flow (proposals → evaluations → commits)
- `json`: Complete raw data for programmatic analysis

### Safety Guardrails

The agent orchestration system includes multiple safety mechanisms:

1. **Protected Files**: Specify patterns agents cannot modify (e.g., `["*.json", "tests/*", "config.py"]`)
2. **Proposal Limits**: `max_proposals_per_agent` prevents individual agents from overwhelming the system
3. **Round Limits**: `max_negotiation_rounds` forces termination if negotiation doesn't converge
4. **Convergence Detection**: Automatically stops when no proposals accepted for N consecutive rounds
5. **Arbiter Agent**: Optional agent acts as tiebreaker for conflict resolution
6. **Complete Audit Trail**: All proposals, evaluations, and changes logged with timestamps and rationale

### When to Use Agent Orchestration

**Good Use Cases:**
- Large agent systems where human review is time-consuming
- Iterative refactoring where agents can suggest improvements
- Code quality enhancement through multi-agent peer review
- Teaching agents to self-improve through collaborative feedback
- CI/CD pipelines with optional AI enhancement step

**Not Recommended:**
- Prototype/early development phase (code changes too frequently)
- Small systems with 1-3 simple agents (overhead not justified)
- Critical production code without human review (always review AI changes)
- When API keys or LLM access unavailable

### Example: Complete Orchestration Workflow

```
# 1. Build with agent orchestration enabled
graphbus_build
  agents_dir: "agents/"
  enable_agents: true
  llm_api_key: "sk-ant-..."
  max_negotiation_rounds: 10
  protected_files: ["tests/*", "*.json"]

# 2. Inspect what agents negotiated
graphbus_inspect_negotiation
  artifacts_dir: ".graphbus"
  format: "timeline"

# 3. Review and decide: accept changes or rollback
# If satisfied, proceed to run
graphbus_run
  artifacts_dir: ".graphbus"

# If not satisfied, rollback and iterate
```

### MCP Tools for Agent Orchestration

Three MCP tools expose the full agent orchestration capabilities:

1. **`graphbus_build`** - Now includes agent orchestration parameters:
   - `enable_agents`: Activate LLM agent orchestration during build
   - `llm_model`: Model to use (claude-sonnet-4, gpt-4, etc.)
   - `llm_api_key`: API key for LLM provider
   - `max_negotiation_rounds`: Maximum rounds before termination
   - `max_proposals_per_agent`: Proposal limit per agent per round
   - `convergence_threshold`: Rounds with no changes before stopping
   - `protected_files`: File patterns agents cannot modify
   - `arbiter_agent`: Agent name for conflict resolution

2. **`graphbus_negotiate`** - Standalone post-build negotiation:
   - Run negotiation after building artifacts
   - Useful for separating build validation from AI enhancement
   - CI/CD friendly: fast builds, optional negotiate step
   - Can re-run with different parameters without rebuilding

3. **`graphbus_inspect_negotiation`** - View negotiation history:
   - Examine proposals, evaluations, and commits
   - Multiple formats: table, timeline, JSON
   - Filter by round or agent
   - Audit AI-generated changes before accepting

---

## Tool Definitions

All 21 CLI commands are exposed as MCP tools with comprehensive metadata. See `mcp_tools.json` for complete definitions including:
- Detailed descriptions with architectural context
- When to use / when not to use guidance
- NetworkX usage explanations
- Build vs Runtime phase indicators
- Command sequencing patterns
- Example workflows

## Why This Architecture

1. **No Code Duplication** - Don't reimplement `graphbus build` logic
2. **Single Source of Truth** - CLI is the only implementation
3. **Maintenance** - Fixes to CLI automatically work in MCP
4. **Consistency** - CLI and MCP behave identically
5. **Testing** - Test CLI, MCP wrapper is trivial (~1000 lines of new code total)

## Installation

```bash
# Install GraphBus with MCP support
pip install graphbus-core[mcp]

# Or install in development mode
cd graphbus-core
pip install -e .[mcp]
```

## Usage with Claude Code

Configure Claude Code to use this MCP server:

```json
{
  "mcpServers": {
    "graphbus": {
      "command": "python",
      "args": ["-m", "graphbus_mcp_server"],
      "cwd": "/path/to/graphbus-core"
    }
  }
}
```

Now Claude Code can use all GraphBus commands naturally:
- "Create a new order processing system" → uses `graphbus_init`
- "Build the agents" → uses `graphbus_build`
- "Show me the agent graph" → uses `graphbus_inspect`
- "Run the system" → uses `graphbus_run`
- "Publish an order created event" → uses `graphbus_publish`

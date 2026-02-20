# GraphBus

<div align="center">

**A multi-agent orchestration protocol where LLM-powered agents negotiate, refactor, and evolve your codebase — then run it statically at zero AI cost.**

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Build Status](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#testing)
[![Version](https://img.shields.io/badge/version-0.1.0--alpha-orange.svg)](https://github.com/graphbus/graphbus-core/releases)
[![graphbus.com](https://img.shields.io/badge/site-graphbus.com-7c3aed.svg)](https://graphbus.com)

[**Website**](https://graphbus.com) · [**Quickstart**](#quickstart) · [**Examples**](#examples) · [**CLI Reference**](#cli-reference) · [**Architecture**](#architecture)

</div>

---

## What is GraphBus?

GraphBus is a Python framework with a radical idea: **let your agents improve the code itself, not just run it.**

Every class in a GraphBus project is a potential LLM agent. During a **build cycle**, agents wake up, read their own source, propose improvements, and negotiate consensus with other agents via a typed message bus. An arbiter resolves conflicts. The result is committed back to source.

At **runtime**, none of that happens. The built artifacts execute as plain, deterministic Python — no LLM calls, no network latency, zero AI cost.

```
Build once (agents active) → Deploy forever (agents dormant, code immutable)
```

### Why this matters

Most LLM orchestration frameworks call LLMs at runtime — forever. Every user request burns tokens. GraphBus inverts this: the intelligence is spent once at build time to improve the code, and the improved code runs cheaply at scale.

---

## Quickstart

```bash
# Install
pip install graphbus

# Create a new project
graphbus init my-project --template microservices
cd my-project

# Build (static, no LLM)
graphbus build agents/

# Run the built artifacts
graphbus run .graphbus/

# Enable LLM agents for a negotiation round
export ANTHROPIC_API_KEY=sk-ant-...
graphbus build agents/ --enable-agents
```

That's it. Your agents will propose improvements, evaluate each other's proposals, and commit consensus changes. The `run` step uses zero AI budget.

---

## Hello World

```python
# agents/hello_service.py
from graphbus_core import GraphBusNode, schema_method, subscribe

class HelloService(GraphBusNode):
    SYSTEM_PROMPT = "I generate friendly greeting messages."

    @schema_method(
        input_schema={},
        output_schema={"message": str}
    )
    def generate_message(self):
        return {"message": "Hello from GraphBus!"}

    @subscribe("/Hello/MessageGenerated")
    def on_message(self, event):
        self.log(event.payload)
```

```bash
graphbus build agents/
# [BUILD] Scanning agents/hello_service.py
# [BUILD] Graph: 1 node, 0 edges
# [BUILD] Artifacts written to .graphbus/

graphbus run .graphbus/
# [RUNTIME] Loaded 1 agent
# [RUNTIME] HelloService → "Hello from GraphBus!"
```

Enable agents and watch them negotiate:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
graphbus build agents/ --enable-agents
# [AGENT] HelloService: "I propose adding input validation..."
# [AGENT] LoggerService: "I accept — improves contract safety"
# [ARBITER] Consensus reached. Committing changes.
# [BUILD] Artifacts written to .graphbus/ (2 files modified)
```

---

## Architecture

GraphBus has two strictly separated modes:

```
┌─────────────────────────────────────────────────────────────────┐
│                        BUILD MODE                               │
│  ┌──────────┐  proposals  ┌─────────┐  evaluations  ┌────────┐ │
│  │ AgentA   │────────────▶│  BUS    │◀──────────────│ AgentB │ │
│  │  (LLM)   │◀────────────│         │───────────────▶│  (LLM) │ │
│  └──────────┘  commits    └────┬────┘               └────────┘ │
│                                │                                │
│                          ┌─────▼─────┐                         │
│                          │  Arbiter  │  resolves conflicts      │
│                          └─────┬─────┘                         │
│                                │                                │
│                    ┌───────────▼──────────┐                     │
│                    │   Build Artifacts     │  (.graphbus/)       │
│                    │  graph.json           │                     │
│                    │  agents.json          │                     │
│                    │  topics.json          │                     │
│                    └───────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (deploy once)
┌─────────────────────────────────────────────────────────────────┐
│                       RUNTIME MODE                              │
│                                                                 │
│  ┌──────────┐   events    ┌─────────┐   events    ┌──────────┐ │
│  │ AgentA   │────────────▶│  BUS    │────────────▶│ AgentB   │ │
│  │ (static) │             │ (pub/   │             │ (static) │ │
│  └──────────┘             │  sub)   │             └──────────┘ │
│                            └─────────┘                          │
│                                                                 │
│          ✅ No LLM calls   ✅ Deterministic   ✅ $0 AI cost     │
└─────────────────────────────────────────────────────────────────┘
```

### Core Concepts

| Concept | Description |
|---|---|
| **GraphBusNode** | Base class for all agents. Subclass it, add a `SYSTEM_PROMPT`, decorate methods. |
| **@schema_method** | Declares typed input/output schema for a method — forms the contract between agents. |
| **@subscribe** | Registers a handler for a topic on the message bus. |
| **@depends_on** | Declares a dependency edge between agents in the DAG. |
| **Build Artifacts** | JSON files emitted after a build: `graph.json`, `agents.json`, `topics.json`. |
| **Arbiter** | A special agent (mark with `IS_ARBITER = True`) that resolves conflicting proposals. |
| **Message Bus** | Typed pub/sub backbone. Topics are typed paths (e.g. `/Order/Created`). |

---

## CLI Reference

GraphBus ships a full-featured CLI with 18 commands:

```
graphbus [OPTIONS] COMMAND [ARGS]...
```

### Core Commands

| Command | Description |
|---|---|
| `graphbus build <path>` | Scan agents, build dependency graph, emit artifacts |
| `graphbus run <artifacts>` | Load artifacts and execute the runtime |
| `graphbus inspect <artifacts>` | Inspect build artifacts (graph, agents, topics) |
| `graphbus validate <path>` | Validate agent definitions without building |
| `graphbus tui` | Launch interactive TUI (keyboard-driven UI) |

### Development Tools

| Command | Description |
|---|---|
| `graphbus init <name>` | Initialize a new project from template |
| `graphbus generate agent <Name>` | Generate agent boilerplate |
| `graphbus profile <artifacts>` | Profile runtime performance |
| `graphbus dashboard` | Launch web-based visualization dashboard |
| `graphbus negotiate <path>` | Run a standalone LLM negotiation round |
| `graphbus inspect-negotiation` | Browse negotiation history |

### Deployment Tools

| Command | Description |
|---|---|
| `graphbus docker build` | Generate Dockerfile for your project |
| `graphbus docker run` | Build and run in Docker |
| `graphbus k8s generate` | Generate Kubernetes manifests |
| `graphbus k8s deploy` | Deploy to Kubernetes cluster |
| `graphbus ci github` | Generate GitHub Actions workflow |
| `graphbus ci gitlab` | Generate GitLab CI pipeline |

### Advanced

| Command | Description |
|---|---|
| `graphbus state` | Manage agent state persistence |
| `graphbus coherence` | Run inter-agent coherence checks |
| `graphbus contract` | Validate schema contracts between agents |
| `graphbus migrate` | Migrate artifacts across schema versions |

---

## Examples

Three working examples are included in `examples/`:

### 1. `hello_graphbus` — The basics

```bash
cd examples/hello_graphbus
python build.py              # Build without agents
ANTHROPIC_API_KEY=sk-... python build.py   # Build with LLM agents
python run.py                # Run the built artifacts
```

### 2. `hello_world_mcp` — MCP integration

GraphBus ships an MCP (Model Context Protocol) server so any MCP-compatible client can interact with a running GraphBus runtime as a tool.

```bash
cd examples/hello_world_mcp
graphbus build agents/
graphbus run .graphbus/ --mcp   # Exposes MCP endpoint
```

### 3. `news_summarizer` — Real-world pipeline

A multi-agent news summarization pipeline. One agent fetches, one summarizes, one formats. Agents negotiate a shared schema for the summary output during build; runtime executes deterministically.

```bash
cd examples/news_summarizer
graphbus build agents/
OPENAI_API_KEY=sk-... graphbus run .graphbus/
```

---

## The Negotiation Protocol

When `--enable-agents` is set, each agent gets an LLM instance. Build Mode runs this cycle:

```
1. SCAN     → Discover all GraphBusNode subclasses in the target path
2. EXTRACT  → Parse methods, schemas, subscriptions, system prompts
3. BUILD    → Construct networkx DAG (topological sort for eval order)
4. ACTIVATE → Instantiate one LLM agent per node
5. PROPOSE  → Each agent reads its source and proposes improvements
6. EVALUATE → Agents evaluate each other's proposals (accept/reject + reasoning)
7. ARBITRATE → Arbiter resolves split decisions
8. COMMIT   → Accepted proposals are applied to source files
9. ARTIFACT → Build graph + agent metadata serialized to .graphbus/
```

Proposals are structured messages:

```python
class Proposal:
    agent_id: str
    target_file: str
    diff: str          # unified diff
    rationale: str     # LLM reasoning
    affects: list[str] # other agents impacted
```

---

## Project Structure

```
graphbus-core/
├── graphbus_core/           # Core library
│   ├── node_base.py         # GraphBusNode base class
│   ├── decorators.py        # @schema_method, @subscribe, @depends_on
│   ├── config.py            # BuildConfig, RuntimeConfig
│   ├── build/               # Build pipeline (scanner, extractor, builder, writer)
│   ├── runtime/             # Runtime engine (loader, bus, router, executor)
│   ├── agents/              # LLM agent wrappers
│   └── model/               # Pydantic models (Message, Event, Proposal, ...)
├── graphbus_cli/            # CLI (click + rich)
│   ├── main.py              # Entry point
│   ├── commands/            # One file per command group
│   └── repl/                # Interactive REPL
├── graphbus_api/            # REST API server
├── graphbus-mcp-server/     # MCP protocol server
├── examples/
│   ├── hello_graphbus/      # Basic example
│   ├── hello_world_mcp/     # MCP integration
│   └── news_summarizer/     # Real-world pipeline
├── tests/                   # Full test suite
└── docs/
    └── core/                # Architecture docs
```

---

## vs. LangGraph / CrewAI / AutoGen

| | **GraphBus** | LangGraph | CrewAI | AutoGen |
|---|---|---|---|---|
| Agents rewrite source code | ✅ Core feature | ❌ | ❌ | ⚠️ Limited |
| Zero LLM cost at runtime | ✅ Always | ❌ Every call | ❌ Every call | ❌ Every call |
| Agent negotiation / consensus | ✅ Built-in | ❌ | ⚠️ Partial | ⚠️ Partial |
| Graph-native DAG orchestration | ✅ networkx | ✅ | ❌ | ❌ |
| Typed schema contracts per edge | ✅ | ⚠️ Partial | ❌ | ❌ |
| Build / Runtime mode separation | ✅ Core design | ❌ | ❌ | ❌ |
| Full deployment tooling (K8s/Docker) | ✅ CLI native | ❌ | ❌ | ❌ |
| Interactive TUI | ✅ | ❌ | ❌ | ❌ |

The key difference: **other frameworks run agents to perform tasks. GraphBus runs agents to improve the code that performs tasks.** After a build cycle, the intelligence is baked into static artifacts — not perpetually consumed at runtime.

---

## Installation

### From source (current)

```bash
git clone https://github.com/graphbus/graphbus-core
cd graphbus-core
pip install -e .
```

### From PyPI (coming soon)

```bash
pip install graphbus
```

### Requirements

- Python 3.9+
- networkx >= 3.0
- click >= 8.1.0
- rich >= 13.0.0

Optional (for LLM agents):
- `anthropic` — Claude models
- `openai` — GPT models

Optional (for TUI):
- `textual >= 0.47.0`

---

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=graphbus_core --cov-report=term-missing

# Run a specific test suite
pytest tests/test_runtime/
pytest tests/test_build/
```

**Test coverage:**
- Build pipeline: 100% passing (scanner, extractor, graph builder, artifact writer)
- Runtime engine: 100% passing (loader, message bus, event router, executor)
- End-to-end: Hello World example builds and runs clean
- CLI: All commands smoke-tested

---

## Contributing

GraphBus is in alpha and we welcome contributors. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Quick start for contributors:

```bash
git clone https://github.com/graphbus/graphbus-core
cd graphbus-core
pip install -e ".[dev]"
pytest                    # Make sure everything passes
```

Areas where we especially want help:
- **More LLM backends** — currently Claude-native, OpenAI adapter needed
- **More examples** — real-world pipelines showing agent negotiation
- **Documentation** — architecture docs, tutorials, protocol spec
- **Benchmarks** — latency/cost comparisons vs. runtime LLM frameworks

---

## Roadmap

See **[ROADMAP.md](ROADMAP.md)** for the full roadmap with targets and status.

**What's shipped (v0.1 alpha):**
- [x] Build Mode (scanner → extractor → graph builder → artifact writer)
- [x] Runtime Mode (loader → message bus → event router → executor)
- [x] CLI with 18 commands
- [x] LLM negotiation engine (propose / evaluate / arbitrate / commit)
- [x] MCP server integration
- [x] Docker + Kubernetes deployment tooling
- [x] 800+ tests, CI with GitHub Actions

**Coming next (v0.2):**
- [ ] `graphbus dev` — hot-reload mode during development
- [ ] Message trace UI — replay message flows in a web UI
- [ ] `graphbus test` — agent unit tests with full runtime wired in

**Later:**
- [ ] PyPI release (`pip install graphbus`)
- [ ] OpenAI / Ollama LLM backends
- [ ] Multi-process distributed runtime
- [ ] TypeScript SDK
- [ ] Protocol specification (for non-Python implementations)

Want to influence what ships next? [Open a GitHub Discussion](https://github.com/graphbus/graphbus-core/discussions) or 👍 the relevant issue.

---

## License

MIT. See [LICENSE](LICENSE).

---

## Links

- 🌐 [graphbus.com](https://graphbus.com) — Landing page + waitlist
- 📧 [hello@graphbus.com](mailto:hello@graphbus.com) — Questions, feedback, partnership

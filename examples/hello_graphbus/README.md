# GraphBus Hello World - Basic Example

This example demonstrates the core GraphBus workflow: **Build Mode** (where LLM agents negotiate improvements) and **Runtime Mode** (where the negotiated code runs deterministically with zero LLM cost).

## What You'll Learn

- Creating simple agents with `@schema_method` and `@subscribe` decorators
- How **Build Mode** works: agents read source, propose changes, negotiate consensus
- How **Runtime Mode** works: agents execute static code with pub/sub messaging
- Multi-agent message passing and event handling

## Prerequisites

1. **Install GraphBus** (from repo):
   ```bash
   cd /path/to/graphbus-core
   pip install -e .
   ```

2. **Verify installation**:
   ```bash
   graphbus --version
   ```

3. **Optional: For agent negotiation**, set an LLM API key:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."        # Claude models (recommended)
   export OPENAI_API_KEY="sk-..."               # GPT models
   export DEEPSEEK_API_KEY="sk-..."             # DeepSeek models
   ```

## Quick Start

### 1. Build the agents (without LLM)

```bash
cd examples/hello_graphbus
python build.py
```

This scans the `agents/` directory, discovers 4 agents, builds a dependency graph, and emits JSON artifacts to `.graphbus/`.

**Output:**
```
Agent mode disabled - set GRAPHBUS_API_KEY to enable (get yours at graphbus.com)
Build successful!
Artifacts saved to: examples/hello_graphbus/.graphbus
```

### 2. Run the agents in Runtime Mode

```bash
python run.py
```

This loads the artifacts and executes a series of tests:
- Direct method calls (HelloService.generate_message)
- Event publishing and pub/sub routing (LoggerService subscribes to /Hello/MessageGenerated)
- Runtime statistics

**Output:**
```
============================================================
HELLO GRAPHBUS - RUNTIME MODE DEMO
============================================================

[Test 1] Calling HelloService.generate_message()...
  Result: {'message': 'Hello, World!'}

[Test 2] Publishing to /Hello/MessageGenerated...
[LOG] [2024-11-14 14:32:55] Greeting generated for 'World': Hello, World!

[Test 3] Runtime Statistics:
  Nodes active: 4
  Messages published: 1
  Messages delivered: 1
  Errors: 0

[Test 4] Accessing node directly...
  Node: HelloService
  Mode: runtime

============================================================
✅ ALL TESTS PASSED - RUNTIME MODE WORKING!
============================================================
```

### 3. Enable LLM agents and watch them negotiate (optional)

If you have an LLM API key, let agents propose improvements:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python build.py
```

With the API key set, agents will:
1. **Propose** improvements to their own code based on their system prompts
2. **Evaluate** other agents' proposals (accept or reject)
3. **Arbitrate** conflicts via an `IS_ARBITER = True` agent
4. **Commit** accepted changes back to source files

**Example negotiation output:**
```
Agent mode enabled - agents will propose code improvements

[AGENT] HelloService: "I propose adding input validation for empty names"
[AGENT] LoggerService: "I accept — improves contract safety"
[ARBITER] ArbitraryService: "Both proposals are compatible. Committing."
[BUILD] Proposal applied: agents/hello.py (+3 lines)

Build successful!
Agents modified 2 files:
  - examples/hello_graphbus/agents/hello.py
  - examples/hello_graphbus/agents/logger.py
```

## Project Structure

```
hello_graphbus/
├── README.md              # This file
├── agents/               # Agent source code
│   ├── __init__.py
│   ├── hello.py         # HelloService: generates greetings
│   ├── logger.py        # LoggerService: logs events via pub/sub
│   ├── printer.py       # PrinterService: prints to console
│   └── arbiter.py       # ArbitraryService: resolves conflicts (IS_ARBITER=True)
├── build.py             # Build script (scanner → graph → artifacts)
├── run.py               # Runtime demo (load artifacts, run tests)
└── .graphbus/           # Build artifacts (created by build.py)
    ├── agents.json      # Agent metadata
    ├── graph.json       # Dependency DAG
    ├── topics.json      # Topic registry
    └── build_summary.json
```

## The Agents

### HelloService
**Role:** Generate personalized greeting messages

```python
@schema_method(
    input_schema={"name": str},
    output_schema={"message": str}
)
def generate_message(self, name="World"):
    return {"message": f"Hello, {name}!"}
```

**In Build Mode:** Can propose adding format variations ("Bonjour", "こんにちは", etc.)

### LoggerService
**Role:** Listen for greeting events and log them

```python
@subscribe("/Hello/MessageGenerated")
def on_message_generated(self, event):
    print(f"[LOG] Greeting generated for '{name}': {message}")
```

**In Build Mode:** Can propose logging more context (timestamp, sender, etc.)

### PrinterService
**Role:** Print formatted messages to console

```python
@schema_method(
    input_schema={"message": str},
    output_schema={}
)
def print_message(self, message: str):
    print(f"[{timestamp}] {message}")
```

**In Build Mode:** Can propose adding ANSI colors or structured output formats

### ArbitraryService
**Role:** Resolve conflicting proposals from other agents

```python
class ArbitraryService(GraphBusNode):
    IS_ARBITER = True  # Special flag
    
    def evaluate_proposal(self, proposal):
        # Accept/reject logic
```

**In Build Mode:** Acts as a tie-breaker when agents disagree on improvements

## Build Mode vs Runtime Mode

| Aspect | Build Mode | Runtime Mode |
|--------|-----------|--------------|
| **LLM calls** | ✅ Every iteration | ❌ Zero |
| **Code modification** | ✅ Agents rewrite source | ❌ Static code only |
| **Agent logic** | Full reasoning + negotiation | Pre-negotiated contracts |
| **Cost** | Depends on LLM API usage | $0 AI budget |
| **Speed** | Slower (negotiation rounds) | Fast (deterministic execution) |
| **Use case** | Improving code quality before deployment | Running production workloads |

## Commands Reference

```bash
# Build only (no LLM)
python build.py

# Build with agent negotiation
export ANTHROPIC_API_KEY="..."
python build.py

# Run the built agents
python run.py

# Inspect build artifacts (requires graphbus CLI)
graphbus inspect .graphbus --graph --agents --topics

# Clear artifacts and rebuild from scratch
rm -rf .graphbus/
python build.py
```

## Extending the Example

### Add a new agent

1. Create `agents/my_service.py`:
```python
from graphbus_core import GraphBusNode, schema_method

class MyService(GraphBusNode):
    SYSTEM_PROMPT = "I do something specific. I can negotiate improvements with other agents."
    
    @schema_method(
        input_schema={"x": int},
        output_schema={"result": int}
    )
    def my_method(self, x):
        return {"result": x * 2}
```

2. Rebuild:
```bash
python build.py
```

The scanner will discover your new agent automatically.

### Subscribe to events

To have an agent respond to published events:

```python
from graphbus_core import GraphBusNode, subscribe

class MyListener(GraphBusNode):
    @subscribe("/Hello/MessageGenerated")
    def on_greeting(self, event):
        print(f"Heard greeting: {event.get('message')}")
```

Then rebuild and run — the subscription will be wired automatically.

## Troubleshooting

### Build fails with "module not found"

**Error:** `ModuleNotFoundError: No module named 'graphbus_core'`

**Solution:** Make sure you installed graphbus-core from source:
```bash
cd /path/to/graphbus-core
pip install -e .
```

### Run fails with "artifacts not found"

**Error:** `FileNotFoundError: .graphbus/agents.json not found`

**Solution:** Build first:
```bash
python build.py
python run.py
```

### Agent negotiation doesn't happen

**Error:** Agents run but don't propose changes

**Cause:** LLM API key not set

**Solution:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python build.py
```

## Next Steps

1. **Explore other examples:**
   - `examples/news_summarizer/` — Real-world pipeline (fetch → clean → format)
   - `examples/hello_world_mcp/` — MCP protocol integration
   - `examples/spec_to_service/` — Advanced multi-agent orchestration

2. **Read the docs:**
   - [README.md](../../README.md) — Overview & architecture
   - [ROADMAP.md](../../ROADMAP.md) — What's coming next

3. **Create your own project:**
   ```bash
   graphbus init my-microservices
   cd my-microservices
   graphbus build agents/
   ```

## Support

- **Documentation:** See [README.md](../../README.md)
- **Issues:** Report on [GitHub](https://github.com/graphbus/graphbus-core/issues)
- **Questions:** Open a [Discussion](https://github.com/graphbus/graphbus-core/discussions)

---

**Happy building!** 🚀

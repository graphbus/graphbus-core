# GraphBus Spec-to-Service - Advanced Code Generation

This example demonstrates GraphBus at scale: **turn a natural language spec into a working FastAPI microservice** — with agents negotiating API contracts, data models, routes, and unit tests.

This is a real-world use case showing how distributed agent reasoning can generate production-ready code.

## What You'll Learn

- **Multi-agent orchestration** — coordinating 5+ agents toward a single goal
- **Spec parsing and code generation** — converting requirements to code
- **Schema negotiation** — agents agree on data models and API contracts
- **Dependency management** — `@depends_on` declares pipeline order
- **File I/O and persistence** — writing generated code to disk
- How agents can cooperate to produce **deterministic artifacts**

## Prerequisites

1. **Install GraphBus** (from repo):
   ```bash
   cd /path/to/graphbus-core
   pip install -e .
   ```

2. **Optional: For agent negotiation**, set an LLM API key:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

## Quick Start

### 1. Build the agents

```bash
cd examples/spec_to_service
python build.py
```

Builds a 5-agent orchestration system:
- **SpecParserAgent** — Extracts requirements from natural language
- **ModelAgent** — Generates Pydantic data models
- **RouterAgent** — Generates FastAPI route handlers
- **TestAgent** — Generates pytest test cases
- **OrchestratorAgent** — Coordinates the full pipeline

**Output:**
```
✅ Build complete: 5 agents, 0 topics
Artifacts saved to: examples/spec_to_service/.graphbus
```

### 2. Run the pipeline

```bash
python run.py
```

This takes a task management API spec (hardcoded in run.py) and generates:
1. Pydantic models (Task, User, etc.)
2. FastAPI routes (GET, POST, PUT, DELETE)
3. Pytest test cases
4. A working `output/` directory with the service

**Example output:**
```
============================================================
SPEC-TO-SERVICE — GRAPHBUS RUNTIME DEMO
============================================================

[Pipeline] Input spec:
A task management API with:
- CRUD operations for tasks (id, title, description, status, priority, due_date)
- User assignment (assign tasks to users by user_id)
- Filter tasks by status and priority
- Mark tasks complete
No auth required for MVP.

[Pipeline] Service name: TaskManagerAPI

[OrchestratorAgent] Parsed spec: 8 endpoints, 3 models, auth=False
[RouterAgent] Generated 8 API routes
[ModelAgent] Generated 3 data models
[TestAgent] Generated 24 test cases

============================================================
GENERATED OUTPUT
============================================================

────────────────────────────────────────────────────
  models.py
────────────────────────────────────────────────────
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class Task(BaseModel):
    id: int
    title: str
    description: str
    status: TaskStatus
    priority: int
    due_date: datetime
    assigned_user_id: int | None = None

class User(BaseModel):
    id: int
    name: str

...

────────────────────────────────────────────────────
  main.py
────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException
from datetime import datetime
from models import Task, User, TaskStatus

app = FastAPI(title="TaskManagerAPI")

@app.get("/tasks", response_model=list[Task])
def list_tasks():
    """List all tasks."""
    return []

@app.post("/tasks", response_model=Task)
def create_task(task: Task):
    """Create a new task."""
    return task

...

────────────────────────────────────────────────────
  test_main.py
────────────────────────────────────────────────────
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_list_tasks():
    response = client.get("/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

...

============================================================
PIPELINE COMPLETE
============================================================

  Output directory : examples/spec_to_service/output
  Files written    : 3
    - models.py
    - main.py
    - test_main.py

  Nodes active     : 5
  Messages sent    : 15
```

### 3. Enable agent negotiation (optional)

With an LLM API key, agents propose improvements:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python build.py
```

Agents might propose:
- **SpecParserAgent** → "Add OpenAPI schema parsing"
- **ModelAgent** → "Use FastAPI Annotated for better validation"
- **RouterAgent** → "Add authentication middleware"
- **TestAgent** → "Add fixtures for common setup"

After negotiation:
```bash
python run.py   # Generates improved code
```

## Project Structure

```
spec_to_service/
├── README.md                # This file
├── agents/                 # Agent source code
│   ├── __init__.py
│   ├── spec_parser.py     # Parses natural language specs
│   ├── model.py           # Generates Pydantic models
│   ├── router.py          # Generates FastAPI routes
│   ├── test_writer.py     # Generates pytest tests
│   └── orchestrator.py    # Coordinates all agents
├── build.py               # Build script
├── run.py                 # Runtime demo
├── output/                # Generated service files (created by run.py)
│   ├── models.py
│   ├── main.py
│   └── test_main.py
└── .graphbus/             # Build artifacts
    ├── agents.json
    ├── graph.json
    └── build_summary.json
```

## The Agents

### SpecParserAgent
**Role:** Parse natural language specs into structured requirements

```python
@schema_method(
    input_schema={"spec": str},
    output_schema={
        "endpoints": list,
        "models": list,
        "auth_required": bool
    }
)
def parse_spec(self, spec: str) -> dict:
    # Extract endpoints, data models, auth requirements
    return {
        "endpoints": [
            {"method": "GET", "path": "/tasks", "response_type": "list[Task]"},
            {"method": "POST", "path": "/tasks", "request_type": "Task"},
            # ... more endpoints
        ],
        "models": ["Task", "User", "TaskStatus"],
        "auth_required": False
    }
```

**Responsibilities:**
- Extract HTTP methods, paths, and request/response types
- Identify data models
- Determine auth requirements

**In Build Mode:** Propose:
- Swagger/OpenAPI spec parsing
- Validation rule extraction
- Rate limiting requirements

### ModelAgent
**Role:** Generate Pydantic data models from requirements

```python
@schema_method(
    input_schema={"model_specs": list},
    output_schema={"models_code": str}
)
def generate_models(self, model_specs: list) -> dict:
    # Generate Pydantic BaseModel subclasses
    code = """
from pydantic import BaseModel

class Task(BaseModel):
    id: int
    title: str
    status: str
    ...
"""
    return {"models_code": code}
```

**Responsibilities:**
- Create Pydantic BaseModel subclasses
- Add field validation (required/optional, types)
- Generate enums for status fields

**In Build Mode:** Propose:
- Field validators and constraints
- SQLAlchemy ORM mappings
- Serialization customizations

### RouterAgent
**Role:** Generate FastAPI route handlers

```python
@schema_method(
    input_schema={"endpoints": list, "models": list},
    output_schema={"routes_code": str}
)
def generate_routes(self, endpoints: list, models: list) -> dict:
    # Generate FastAPI @app.get/@app.post decorators
    code = """
from fastapi import FastAPI
from models import Task

app = FastAPI()

@app.get("/tasks", response_model=list[Task])
def list_tasks():
    return []

@app.post("/tasks", response_model=Task)
def create_task(task: Task):
    return task
"""
    return {"routes_code": code}
```

**Responsibilities:**
- Generate route decorators
- Handle path parameters, query parameters, request bodies
- Type responses using response_model

**In Build Mode:** Propose:
- Error handling middleware
- Request/response validation
- Authentication decorators
- CORS configuration

### TestAgent
**Role:** Generate pytest test cases

```python
@schema_method(
    input_schema={"endpoints": list},
    output_schema={"test_code": str}
)
def generate_tests(self, endpoints: list) -> dict:
    # Generate pytest functions for each endpoint
    code = """
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_list_tasks():
    response = client.get("/tasks")
    assert response.status_code == 200
"""
    return {"test_code": code}
```

**Responsibilities:**
- Create test functions for each endpoint
- Add assertions for status codes, response shapes
- Generate fixtures for common setup

**In Build Mode:** Propose:
- Property-based testing (Hypothesis)
- Concurrent test scenarios
- Load testing harnesses
- Integration test patterns

### OrchestratorAgent
**Role:** Coordinate the full pipeline

```python
@depends_on("RouterAgent", "ModelAgent", "TestAgent")
class OrchestratorAgent(GraphBusNode):
    @schema_method(
        input_schema={"spec": str, "service_name": str},
        output_schema={"output_dir": str, "files_written": list}
    )
    def build_service(self, spec: str, service_name: str) -> dict:
        # 1. Parse spec (SpecParserAgent)
        # 2. Generate models (ModelAgent)
        # 3. Generate routes (RouterAgent)
        # 4. Generate tests (TestAgent)
        # 5. Write files to output/
        return {
            "output_dir": "output/",
            "files_written": ["models.py", "main.py", "test_main.py"]
        }
```

**Responsibilities:**
- Call agents in order (respecting dependencies)
- Collect results
- Write generated code to files
- Return success/failure

**Dependencies:**
- Depends on RouterAgent, ModelAgent, TestAgent
- They execute in topological order

## Agent Orchestration Pattern

This example demonstrates the **orchestration pattern**:

```
spec (natural language)
    ↓
[SpecParserAgent]  → extract requirements
    ↓
[ModelAgent]  ←→  [RouterAgent]  ←→  [TestAgent]
(models)          (routes)           (tests)
    ↓                    ↓                  ↓
      └──────────────────┬──────────────────┘
                         ↓
            [OrchestratorAgent]
            (coordinates & writes files)
                         ↓
                    output/
                (working FastAPI service)
```

**Key insights:**
- `@depends_on` declares execution order
- Agents run in topological order (safe parallelization)
- Agents negotiate contracts at boundaries
- Output is deterministic static files (no LLM at runtime)

## Extending the Example

### Change the input spec

Edit `run.py`:

```python
TASK_SPEC = """A chat API with:
- Websocket connections for real-time messaging
- User rooms and presence
- Message history (SQLite)
"""
```

Then rebuild and run:
```bash
python build.py
python run.py
```

Agents will generate models, routes, and tests for the chat API automatically.

### Add a new agent (e.g., DocAgent)

1. Create `agents/docs.py`:
```python
from graphbus_core import GraphBusNode, schema_method, depends_on

@depends_on("ModelAgent", "RouterAgent")
class DocAgent(GraphBusNode):
    SYSTEM_PROMPT = "I generate Markdown documentation."
    
    @schema_method(
        input_schema={"spec": str, "routes_code": str, "models_code": str},
        output_schema={"docs_code": str}
    )
    def generate_docs(self, spec: str, routes_code: str, models_code: str):
        # Generate README.md, API docs, etc.
        return {"docs_code": "# API Documentation\n..."}
```

2. Update `orchestrator.py` to call DocAgent and write the docs.

3. Rebuild:
```bash
python build.py
python run.py
```

### Use the generated service

The generated code in `output/` is ready to run:

```bash
cd examples/spec_to_service/output

# Install dependencies
pip install fastapi pydantic

# Run the service
python -m uvicorn main:app --reload

# Run tests
pytest test_main.py -v
```

The service will be live on `http://localhost:8000`.

## Build vs Runtime Cost

| Phase | Cost | Time |
|-------|------|------|
| **Build (agent negotiation)** | LLM API cost | Minutes (agent proposals + evaluation) |
| **Runtime (generated code)** | $0 LLM budget | Milliseconds (deterministic Python) |

**Example:** Build takes 2 minutes with Claude, but generates code that runs millions of times without AI cost.

## Commands Reference

```bash
# Build without negotiation
python build.py

# Build with agent negotiation
export ANTHROPIC_API_KEY="..."
python build.py

# Run the pipeline (generates code)
python run.py

# Inspect agents and dependencies
graphbus inspect .graphbus --graph --agents

# View negotiation history
graphbus inspect-negotiation .graphbus --format timeline
```

## Real-World Extensions

This pattern scales to:

1. **Microservices mesh** — Generate multiple coordinated services
2. **Database schema** — Agents negotiate Alembic migrations
3. **Kubernetes manifests** — Generate deployment configs
4. **CI/CD pipelines** — Generate GitHub Actions workflows
5. **Client SDKs** — Generate TypeScript/Python client libraries
6. **Documentation sites** — Generate MkDocs or Sphinx

All with the same orchestration pattern: **spec → agents → files → deployed artifacts**

## Real-World Patterns

### Pattern 1: Build once, deploy many
Build the service with agent negotiation once, then deploy the generated code to 100 servers. The cost amortizes.

### Pattern 2: Spec versioning
Store specs in version control. Rebuild whenever specs change. Agents re-negotiate and generate updated code.

### Pattern 3: Interactive refinement
User proposes spec → agents generate → user reviews → user refines spec → agents re-generate (with better context).

## Troubleshooting

### Build fails with "module not found"

**Error:** `ModuleNotFoundError: No module named 'graphbus_core'`

**Solution:** Install from source:
```bash
cd /path/to/graphbus-core
pip install -e .
```

### Generated code has syntax errors

**Error:** Invalid Python in output/

**Cause:** Agents negotiated incompatible contracts

**Solution:** Review orchestrator logs and review negotiation:
```bash
graphbus inspect-negotiation .graphbus
```

### Run.py fails with "missing files"

**Error:** `FileNotFoundError: output/ not found`

**Solution:** Run the pipeline first:
```bash
python run.py  # Creates output/
```

### Agent negotiation takes too long

**Error:** Build hangs for >30 seconds

**Cause:** Many negotiation rounds with expensive LLM

**Solution:** Limit rounds:
```python
config.max_negotiation_rounds = 1  # In build.py
```

## Performance Characteristics

**Build time (with negotiation):**
- Parsing spec: ~100ms
- Agent proposals: ~5 seconds (depends on LLM latency)
- Evaluation: ~3 seconds
- Total: ~8-10 seconds per round

**Runtime (generated code):**
- Spec input: ~1ms
- Generate models: ~0.5ms
- Generate routes: ~0.5ms
- Generate tests: ~2ms
- Write files: ~5ms
- **Total: ~9ms (zero LLM cost)**

After generation, the FastAPI service runs with zero AI overhead.

## Next Steps

1. **Explore other examples:**
   - `hello_graphbus/` — Basic 4-agent pipeline
   - `news_summarizer/` — Real-world ETL pipeline
   - `hello_world_mcp/` — MCP protocol integration

2. **Read architecture docs:**
   - [README.md](../../README.md) — Core concepts
   - [ROADMAP.md](../../ROADMAP.md) — Future features

3. **Build your own codegen:**
   ```bash
   graphbus init my-codegen
   cd my-codegen
   # Create agents for your domain-specific language
   graphbus build agents/
   ```

## Support

- **Documentation:** [README.md](../../README.md)
- **Issues:** [GitHub Issues](https://github.com/graphbus/graphbus-core/issues)
- **Questions:** [GitHub Discussions](https://github.com/graphbus/graphbus-core/discussions)

---

**Generate code with confidence!** 🚀

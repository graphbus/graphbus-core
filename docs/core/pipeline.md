# GraphBus Core Execution Pipeline

This document defines the **deterministic pipelines** for both **Build Mode** and **Runtime Mode**.

**Critical Distinction:**
* **Build Mode Pipeline**: Agent orchestration and code refactoring (agents active, code mutable)
* **Runtime Mode Pipeline**: Static code execution (agents dormant, code immutable)

---

## 0. Two Separate Pipelines

GraphBus Core has **two distinct execution modes**, each with its own pipeline:

1. **Build Mode Pipeline** - Where agents refactor code
2. **Runtime Mode Pipeline** - Where code executes statically

These are **NOT sequential phases of a single pipeline**. They are separate operational modes.

---

## 1. Build Mode Pipeline (Agent-Driven Refactoring)

### 1.1 Build Pipeline Stages

The Build Mode pipeline activates agents and orchestrates code refactoring through negotiations.

**Stage List:**

1. `LOAD_BUILD_CONFIG`
2. `DISCOVER_MODULES`
3. `DISCOVER_CLASSES`
4. `READ_SOURCE_CODE`
5. `EXTRACT_AGENT_METADATA`
6. `BUILD_AGENT_GRAPH`
7. `COMPUTE_TOPOLOGICAL_ORDER`  ← **NetworkX topological sort**
8. `INIT_NEGOTIATION_ENGINE`  ← **Initialize with SafetyConfig**
9. `ACTIVATE_AGENTS`  ← **Agents come alive here in topological order**
10. `AGENT_ANALYSIS_PHASE`
11. `DETECT_SCHEMA_CONFLICTS`
12. `MULTI_ROUND_NEGOTIATION_LOOP`  ← **Multi-round negotiation with safety checks**
13. `APPLY_CODE_CHANGES`
14. `EMIT_BUILD_ARTIFACTS`
15. `BUILD_COMPLETE`

### 1.2 Build Pipeline DAG

```text
LOAD_BUILD_CONFIG
  ↓
DISCOVER_MODULES
  ↓
DISCOVER_CLASSES
  ↓
READ_SOURCE_CODE
  ↓
EXTRACT_AGENT_METADATA
  ↓
BUILD_AGENT_GRAPH
  ↓
COMPUTE_TOPOLOGICAL_ORDER
  ↓
INIT_AGENT_BUS
  ↓
INIT_NEGOTIATION_ENGINE
  ↓
ACTIVATE_AGENTS
  ↓
AGENT_ANALYSIS_PHASE
  ↓
DETECT_SCHEMA_CONFLICTS
  ↓
NEGOTIATION_LOOP (iterative)
  ↓
APPLY_CODE_CHANGES
  ↓
EMIT_BUILD_ARTIFACTS
  ↓
BUILD_COMPLETE
```

### 1.3 Build Pipeline networkx Implementation

```python
import networkx as nx

BUILD_PIPELINE = nx.DiGraph()

build_stages = [
    "LOAD_BUILD_CONFIG",
    "DISCOVER_MODULES",
    "DISCOVER_CLASSES",
    "READ_SOURCE_CODE",
    "EXTRACT_AGENT_METADATA",
    "BUILD_AGENT_GRAPH",
    "COMPUTE_TOPOLOGICAL_ORDER",
    "INIT_NEGOTIATION_ENGINE",
    "ACTIVATE_AGENTS",
    "AGENT_ANALYSIS_PHASE",
    "DETECT_SCHEMA_CONFLICTS",
    "MULTI_ROUND_NEGOTIATION_LOOP",
    "APPLY_CODE_CHANGES",
    "EMIT_BUILD_ARTIFACTS",
    "BUILD_COMPLETE",
]

BUILD_PIPELINE.add_nodes_from(build_stages)

BUILD_PIPELINE.add_edges_from([
    ("LOAD_BUILD_CONFIG", "DISCOVER_MODULES"),
    ("DISCOVER_MODULES", "DISCOVER_CLASSES"),
    ("DISCOVER_CLASSES", "READ_SOURCE_CODE"),
    ("READ_SOURCE_CODE", "EXTRACT_AGENT_METADATA"),
    ("EXTRACT_AGENT_METADATA", "BUILD_AGENT_GRAPH"),
    ("BUILD_AGENT_GRAPH", "COMPUTE_TOPOLOGICAL_ORDER"),
    ("COMPUTE_TOPOLOGICAL_ORDER", "INIT_NEGOTIATION_ENGINE"),
    ("INIT_NEGOTIATION_ENGINE", "ACTIVATE_AGENTS"),
    ("ACTIVATE_AGENTS", "AGENT_ANALYSIS_PHASE"),
    ("AGENT_ANALYSIS_PHASE", "DETECT_SCHEMA_CONFLICTS"),
    ("DETECT_SCHEMA_CONFLICTS", "MULTI_ROUND_NEGOTIATION_LOOP"),
    ("MULTI_ROUND_NEGOTIATION_LOOP", "APPLY_CODE_CHANGES"),
    ("APPLY_CODE_CHANGES", "EMIT_BUILD_ARTIFACTS"),
    ("EMIT_BUILD_ARTIFACTS", "BUILD_COMPLETE"),
])

# Execution
def run_build_pipeline(config: BuildConfig):
    context = {"config": config}
    for stage in nx.topological_sort(BUILD_PIPELINE):
        run_build_stage(stage, context)
    return context["artifacts"]
```

### 1.4 Build Stage Semantics

#### `LOAD_BUILD_CONFIG`

**Input:** CLI args or config file

**Output:**
```python
context["config"] = BuildConfig(
    root_package="my_project.agents",
    llm_config=LLMConfig(model="claude-sonnet-4", api_key="..."),
    refactoring_goals=["align_schemas", "add_validation"],
    safety_config=SafetyConfig(
        max_negotiation_rounds=10,
        max_proposals_per_agent=3,
        convergence_threshold=2,
        require_arbiter_on_conflict=True,
        max_total_file_changes=10,
        protected_files=[]
    )
)
```

---

#### `DISCOVER_MODULES`

**Input:** `config.root_package`

**Behavior:** Use `pkgutil.walk_packages` to find all modules

**Output:** `context["modules"] = [module1, module2, ...]`

---

#### `DISCOVER_CLASSES`

**Input:** `modules`

**Behavior:** Import modules and find `GraphBusNode` subclasses

**Output:** `context["classes"] = [(class_obj, module), ...]`

---

#### `READ_SOURCE_CODE`

**Input:** `classes`

**Behavior:** Read the actual `.py` file for each class

**Output:**
```python
context["source_files"] = {
    "HelloService": {
        "path": "/path/to/hello.py",
        "content": "class HelloService(GraphBusNode):\n    ..."
    },
    ...
}
```

---

#### `EXTRACT_AGENT_METADATA`

**Input:** `classes`, `source_files`

**Behavior:** Extract prompts, schemas, subscriptions from each class

**Output:**
```python
context["agent_definitions"] = [
    AgentDefinition(
        name="HelloService",
        source_file="/path/to/hello.py",
        source_code="...",
        system_prompt="...",
        methods=[...],
        subscriptions=[...]
    ),
    ...
]
```

---

#### `BUILD_AGENT_GRAPH`

**Input:** `agent_definitions`

**Behavior:** Create `networkx.DiGraph` with agents as nodes, dependencies as edges

**Output:** `context["agent_graph"] = AgentGraph(...)`

---

#### `COMPUTE_TOPOLOGICAL_ORDER`

**Input:** `agent_graph`

**Behavior:**
* Use `networkx.topological_sort(agent_graph.graph)` to determine agent activation order
* Agents with no dependencies come first
* Agents with dependencies come after their providers
* Ensures proper negotiation flow based on code structure

**Output:** `context["agent_order"] = ["HelloService", "PrinterService", "LoggerService"]`

**Implementation:**
```python
def compute_topological_order(context):
    agent_graph = context["agent_graph"]
    activation_order = agent_graph.get_agent_activation_order()
    # Uses networkx.topological_sort() internally
    context["agent_order"] = activation_order
```

---

#### `INIT_NEGOTIATION_ENGINE`

**Input:** `config.safety_config`

**Behavior:**
* Create negotiation engine for proposals/evaluations/commits
* Initialize with safety guardrails from SafetyConfig
* Set up tracking for:
  * Proposal counts per agent
  * Round counter
  * File modification counter
  * Convergence detection

**Output:**
```python
context["negotiation_engine"] = NegotiationEngine(
    safety_config=config.safety_config
)
```

**Safety Features Initialized:**
* `max_negotiation_rounds`: Hard limit on negotiation rounds
* `max_proposals_per_agent`: Per-agent proposal budget
* `convergence_threshold`: Rounds without proposals before stopping
* `require_arbiter_on_conflict`: Auto-invoke arbiter on ties
* `max_total_file_changes`: Cap on files modified
* `protected_files`: Files that cannot be changed

---

#### `ACTIVATE_AGENTS`

**Critical Stage: Agents Come Alive**

**Input:** `agent_definitions`, `agent_order`, `negotiation_engine`

**Behavior:**
* **For each agent in topological order** (from `agent_order`):
  * Instantiate LLM-powered agent with system prompt
  * Give agent access to its source code
  * Detect if agent is an arbiter (`IS_ARBITER = True`)
  * Give agent negotiation capabilities
* Arbiter agents are identified and tracked separately

**Output:**
```python
context["active_agents"] = {
    "HelloService": LLMAgent(
        name="HelloService",
        system_prompt="...",
        source_code="...",
        is_arbiter=False
    ),
    "ArbiterService": LLMAgent(
        name="ArbiterService",
        system_prompt="...",
        source_code="...",
        is_arbiter=True  # Detected from IS_ARBITER class attribute
    ),
    ...
}
```

**Invariant:** From this point forward, agents can send proposals and evaluate.

**Topological Order Impact:**
* Agents activate in dependency order
* Downstream agents see upstream agents' initial state
* Ensures coherent negotiation flow

---

#### `AGENT_ANALYSIS_PHASE`

**Input:** `active_agents`

**Behavior:**
* Each agent (in order) analyzes its own code
* Agent uses LLM to understand what its code does
* Agent identifies dependencies on other agents
* Agent checks schemas of methods it calls/receives

**Output:**
```python
context["agent_analyses"] = {
    "HelloService": {
        "dependencies": ["PrinterService"],
        "schema_expectations": {...},
        "potential_issues": []
    },
    ...
}
```

---

#### `DETECT_SCHEMA_CONFLICTS`

**Input:** `agent_analyses`, `agent_graph`

**Behavior:**
* Compare producer/consumer schemas across agent edges
* Detect mismatches (type conflicts, missing fields, etc.)
* Create initial proposals for schema alignment

**Output:**
```python
context["schema_conflicts"] = [
    SchemaConflict(
        producer="HelloService",
        consumer="PrinterService",
        issue="output type mismatch",
        suggested_fix="..."
    ),
    ...
]
```

---

#### `MULTI_ROUND_NEGOTIATION_LOOP`

**Critical Stage: Multi-Round Agent Negotiation with Safety Checks**

**Input:** `active_agents`, `negotiation_engine`, `schema_conflicts`, `safety_config`

**Behavior (multi-round iterative):**

**For each Round N (from 0 to `max_negotiation_rounds - 1`):**

1. **Proposal Phase**:
   * Each agent proposes improvements from analysis
   * **Safety Check**: `negotiation_engine.can_agent_propose(agent)` checks:
     - Agent hasn't exceeded `max_proposals_per_agent`
     - Not past `max_negotiation_rounds`
     - Not already converged
   * **Protected Files Check**: Proposals targeting protected files are rejected
   * Valid proposals added to `negotiation_engine.proposals`

2. **Evaluation Phase**:
   * All agents evaluate all proposals (except their own)
   * Each agent uses LLM to assess impact and decide accept/reject
   * Evaluations stored: `negotiation_engine.evaluations[proposal_id]`

3. **Conflict Detection**:
   * Count accept vs reject votes for each proposal
   * Detect conflicts:
     - Tie: `accepts == rejects`
     - Close vote: `abs(accepts - rejects) <= 1`
   * If conflict detected and `require_arbiter_on_conflict = True` → trigger arbitration

4. **Arbiter Invocation** (if conflict):
   * Select arbiter agent (first agent with `is_arbiter = True`)
   * Call `arbiter.arbitrate_conflict(proposal, evaluations, round_num)`
   * Arbiter reviews:
     - Proposed code change
     - All agent evaluations and reasoning
     - Technical correctness and system impact
   * Arbiter returns binding evaluation (accept or reject)
   * Arbiter's decision recorded in evaluations

5. **Commit Creation**:
   * For each accepted proposal:
     - **Safety Check**: Total files modified < `max_total_file_changes`
     - Create `CommitRecord` with consensus type:
       - "unanimous" if all accepted
       - "majority" if some rejected
       - "arbiter" if arbiter decided
     - Increment `total_files_modified`

6. **Convergence Check**:
   * If no new proposals this round:
     - Increment `rounds_without_proposals`
     - If `>= convergence_threshold` → STOP
   * If new proposals: reset `rounds_without_proposals = 0`

7. **Safety Termination Checks**:
   * If `current_round >= max_negotiation_rounds` → STOP
   * If `total_files_modified >= max_total_file_changes` → STOP

**Output:**
```python
context["negotiations"] = {
    "completed": [CommitRecord(...), ...],
    "rounds_executed": N,
    "converged": True/False,
    "termination_reason": "convergence" | "max_rounds" | "file_limit"
}
```

**Multi-Round Flow Example:**

```
Round 0:
  - 3 agents propose improvements
  - All proposals evaluated
  - 1 conflict detected → arbiter invoked → accepted
  - 2 commits created

Round 1:
  - 1 agent proposes follow-up improvement
  - Evaluated and accepted
  - 1 commit created

Round 2:
  - No new proposals
  - rounds_without_proposals = 1

Round 3:
  - No new proposals
  - rounds_without_proposals = 2 (>= convergence_threshold)
  - CONVERGENCE DETECTED → Stop
```

**Safety Guarantees:**
* No agent can spam proposals (rate limited)
* Negotiation always terminates (round limit)
* Conflicts resolved fairly (arbiter)
* File changes bounded (modification limits)
* Critical files protected (protected_files list)

---

#### `APPLY_CODE_CHANGES`

**Critical Stage: Source Files Modified**

**Input:** `negotiations["completed"]`

**Behavior:**
* For each CommitRecord:
  * Extract agreed-upon code changes
  * Apply changes to source files on disk
  * Track which files were modified

**Output:**
```python
context["modified_files"] = [
    "/path/to/hello.py",
    "/path/to/printer.py"
]
```

**Invariant:** Source code files have been physically modified by agents.

---

#### `EMIT_BUILD_ARTIFACTS`

**Input:** `agent_graph`, `agent_definitions`, `negotiations`, `modified_files`

**Behavior:**
* Write JSON artifacts to `.graphbus/`:
  * `graph.json` (agent graph structure)
  * `agents.json` (agent metadata)
  * `negotiations.json` (build history)
  * `modified_files.json` (list of changes)

**Output:** `context["artifacts"] = BuildArtifacts(...)`

---

#### `BUILD_COMPLETE`

**Input:** `artifacts`

**Behavior:** Mark build as successful, log summary

**Output:** `context["build_status"] = "success"`

---

## 2. Runtime Mode Pipeline (Static Execution)

### 2.1 Runtime Pipeline Stages

The Runtime Mode pipeline executes refactored code without agent intelligence.

**Stage List:**

1. `LOAD_RUNTIME_CONFIG`
2. `LOAD_BUILD_ARTIFACTS`
3. `IMPORT_MODULES`
4. `INIT_SIMPLE_BUS` (optional)
5. `EXECUTE_ENTRYPOINT`
6. `SHUTDOWN`

**Key Difference:** No agent activation, no negotiation, no code modification.

### 2.2 Runtime Pipeline DAG

```text
LOAD_RUNTIME_CONFIG
  ↓
LOAD_BUILD_ARTIFACTS
  ↓
IMPORT_MODULES
  ↓
INIT_SIMPLE_BUS (optional)
  ↓
EXECUTE_ENTRYPOINT
  ↓
SHUTDOWN
```

### 2.3 Runtime Pipeline networkx Implementation

```python
import networkx as nx

RUNTIME_PIPELINE = nx.DiGraph()

runtime_stages = [
    "LOAD_RUNTIME_CONFIG",
    "LOAD_BUILD_ARTIFACTS",
    "IMPORT_MODULES",
    "INIT_SIMPLE_BUS",
    "EXECUTE_ENTRYPOINT",
    "SHUTDOWN",
]

RUNTIME_PIPELINE.add_nodes_from(runtime_stages)

RUNTIME_PIPELINE.add_edges_from([
    ("LOAD_RUNTIME_CONFIG", "LOAD_BUILD_ARTIFACTS"),
    ("LOAD_BUILD_ARTIFACTS", "IMPORT_MODULES"),
    ("IMPORT_MODULES", "INIT_SIMPLE_BUS"),
    ("INIT_SIMPLE_BUS", "EXECUTE_ENTRYPOINT"),
    ("EXECUTE_ENTRYPOINT", "SHUTDOWN"),
])

# Execution
def run_runtime_pipeline(config: RuntimeConfig):
    context = {"config": config}
    for stage in nx.topological_sort(RUNTIME_PIPELINE):
        run_runtime_stage(stage, context)
```

### 2.4 Runtime Stage Semantics

#### `LOAD_RUNTIME_CONFIG`

**Input:** CLI args

**Output:** `context["config"] = RuntimeConfig(entrypoint="my_project.main:run")`

---

#### `LOAD_BUILD_ARTIFACTS`

**Input:** Artifacts from Build Mode

**Behavior:** Load JSON from `.graphbus/`

**Output:** `context["artifacts"] = BuildArtifacts.load(".graphbus/")`

**Invariant:** Artifacts contain info about refactored code, but agents are dormant.

---

#### `IMPORT_MODULES`

**Input:** `artifacts.agents`

**Behavior:** Import the (refactored) Python modules

**Output:** `context["modules"] = {name: imported_module, ...}`

**Note:** This is standard Python import - no LLM, no agents.

---

#### `INIT_SIMPLE_BUS` (Optional)

**Input:** `artifacts` (for subscription info)

**Behavior:** If Build Mode defined pub/sub topics, create static router

**Output:** `context["bus"] = SimpleMessageBus()`

**Note:** This is pure function-call routing, no agent reasoning.

---

#### `EXECUTE_ENTRYPOINT`

**Input:** `config.entrypoint`, `modules`

**Behavior:**
* Import entrypoint function
* Execute it
* Code runs normally (agents dormant)

**Output:** Execution results (stdout, return values, etc.)

**Invariant:** No agent negotiations, no code modifications.

---

#### `SHUTDOWN`

**Input:** Entire context

**Behavior:** Clean up resources, exit

---

## 3. Comparison: Build vs Runtime Pipelines

| Aspect | Build Mode Pipeline | Runtime Mode Pipeline |
|--------|---------------------|----------------------|
| **Purpose** | Refactor code via agents | Execute code statically |
| **Agents** | Active (LLM-powered) | Dormant (metadata only) |
| **Code** | Mutable (can be changed) | Immutable (execution only) |
| **Negotiation** | Yes (multi-round with safety limits) | No |
| **Arbiter** | Yes (automatic conflict resolution) | No |
| **Graph Usage** | Orchestration (networkx topological sort) | Documentation only |
| **Safety Limits** | Enforced (proposals, rounds, files) | N/A |
| **Stages** | 15 stages | 6 stages |
| **Complexity** | High (agent coordination, arbitration) | Low (standard execution) |
| **Output** | Modified source code + artifacts | Program execution results |
| **Convergence** | Detected and enforced | N/A |

---

## 4. Hello World Through Both Pipelines

### 4.1 Build Mode (Hello World)

```bash
python -m graphbus_core.build --root hello_graphbus.agents
```

**Pipeline execution:**
* `COMPUTE_TOPOLOGICAL_ORDER`: NetworkX determines order: [Hello, Printer, Logger, Arbiter]
* `INIT_NEGOTIATION_ENGINE`: Safety config loaded (max_rounds=10, max_proposals=3, etc.)
* `ACTIVATE_AGENTS`: 4 agents instantiated (Hello, Printer, Logger, Arbiter)
* `AGENT_ANALYSIS_PHASE`: Each agent reads its code
* `MULTI_ROUND_NEGOTIATION_LOOP`:
  * **Round 0**:
    - PrinterService proposes adding color output
    - LoggerService proposes adding timestamps
    - Agents evaluate → all accept
    - 2 commits created
  * **Round 1**:
    - No new proposals (agents satisfied)
    - rounds_without_proposals = 1
  * **Round 2**:
    - No new proposals
    - rounds_without_proposals = 2 (>= convergence_threshold)
    - **CONVERGENCE DETECTED**
* `APPLY_CODE_CHANGES`: 2 files modified
* `EMIT_BUILD_ARTIFACTS`: JSON written to `.graphbus/`

**Result:** Source code modified, artifacts created.
**Safety Stats:** 2 rounds, 2 proposals, 2 commits, 2 files modified

### 4.2 Runtime Mode (Hello World)

```bash
python -m graphbus_core.runtime --entrypoint hello_graphbus.main:run
```

**Pipeline execution:**
* `LOAD_BUILD_ARTIFACTS`: Load from `.graphbus/`
* `IMPORT_MODULES`: Import refactored code
* `EXECUTE_ENTRYPOINT`: Run `main()` function
  * Calls HelloService.generate_message()
  * Calls PrinterService.print_message() → green output
  * LoggerService subscription fires → timestamped log

**Result:** Console output (no code changes, agents dormant).

---

## 5. Pipeline Determinism

Both pipelines are deterministic:

**Build Mode:**
* Given the same initial code and LLM config, agents should converge to the same refactorings (modulo LLM non-determinism)
* Pipeline stages execute in fixed topological order
* Negotiation loop has clear termination conditions

**Runtime Mode:**
* Completely deterministic (standard Python execution)
* No LLM calls, no randomness
* Same input → same output

---

## 6. Implementation Notes

### 6.1 Shared Infrastructure

Both pipelines share some primitives:
* `GraphBusNode` base class
* Schema definitions
* Graph data structures (networkx)

But they use them differently:
* Build Mode: Agents actively interpret prompts and refactor
* Runtime Mode: Metadata only, no interpretation

### 6.2 Pipeline Context

Both pipelines use a `context` dict to pass data between stages:

```python
# Build Mode context
build_context = {
    "config": BuildConfig(...),
    "agent_graph": AgentGraph(...),
    "active_agents": {...},
    "negotiations": {...},
    "modified_files": [...]
}

# Runtime Mode context
runtime_context = {
    "config": RuntimeConfig(...),
    "artifacts": BuildArtifacts(...),
    "modules": {...}
}
```

### 6.3 Pipeline Extensibility

New stages can be added by:
1. Adding stage to the DAG
2. Implementing `run_<mode>_stage(stage_name, context)`
3. Ensuring dependencies are correct (edges in DAG)

Example: Adding a validation stage after `APPLY_CODE_CHANGES` in Build Mode.

---

## 7. Future Enhancements

**Build Mode Pipeline:**
* Incremental builds (only re-run changed agents)
* Parallel agent activation (when no dependencies)
* Rollback on failed negotiations
* Human-in-the-loop approval gates

**Runtime Mode Pipeline:**
* Hot reload on code changes
* Distributed execution (multi-process/multi-host)
* Performance profiling integration
* Debugging/breakpoint support

---

The core architecture remains: **Build Mode refactors code with active agents, Runtime Mode executes code with dormant agents**.

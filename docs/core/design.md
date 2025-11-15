# GraphBus Core – Design Document (Python + Swift/macOS)

## 0. Purpose & Scope

**Goal:**
Define the primitives and architecture for a **graphbus-core** Python library that:

* Treats **each Python class as a node/agent** with:
  * a **system prompt**
  * a **schema contract**
  * **negotiation primitives**
* Represents the codebase as a **graph** (using `networkx`)
* Provides a **graph-based messaging bus** with:
  * direct messages (node → node)
  * pub/sub notifications (topics)
* Separates **Build Mode** (active agents that refactor code) from **Runtime Mode** (static code execution)
* Exposes a **clean API surface** that a **Swift macOS app** can use to:
  * visualize the graph
  * inspect nodes
  * start/stop runtimes
  * inspect messages and negotiations

This document focuses on **graphbus-core primitives in Python**, plus the integration contract to the Swift frontend.

Non-goals for this first iteration:

* No distributed multi-machine runtime (single-host only).
* No persistence beyond simple file-based artifacts (JSON) and optional local memory storage.
* No deep security/permissions model yet (assume trusted local environment).

---

## 1. High-Level Architecture

### 1.1 Main Components

1. **Build Mode** (Agents Active - Code Mutable)
   * Scans Python modules and discovers classes that opt into GraphBus.
   * **Activates LLM-powered agents** - one per class/file.
   * Each agent:
     * Has a system prompt defining its role and responsibilities
     * Can read and understand its associated code file
     * Can negotiate with other agents via the GraphBus
     * Can propose, evaluate, and commit code changes
   * Uses the **DAG to orchestrate agent execution**:
     * Topological sort determines agent activation order
     * Schema dependencies drive negotiation flows
     * Agents refactor code collaboratively
   * Extracts and builds:
     * nodes (classes with their agent metadata)
     * dependencies (edges representing code/schema relationships)
     * schemas (input/output contracts)
     * prompts (per-agent instructions)
     * topics / subscriptions (pub/sub relationships)
   * **Agents can modify source code files** based on negotiations
   * Emits build artifacts (updated code + metadata JSON) for runtime

2. **Runtime Mode** (Agents Dormant - Code Immutable)
   * Loads the **static artifacts** produced by Build Mode.
   * Code is **frozen and immutable** - no agent intelligence active.
   * Simply **executes the Python code** as-is:
     * Direct function calls (no agent negotiation)
     * Pure pub/sub message routing (no LLM decisions)
     * Deterministic execution based on the code structure
   * No schema negotiation, no code modification, no proposals.
   * This is traditional "run the program" mode.

3. **Swift macOS Frontend**
   * Talks to a local **Python host** process (graphbus-core).
   * Uses REST/WebSocket to:
     * **In Build Mode:**
       * Visualize agent graph and dependencies
       * Observe agent negotiations in real-time
       * Watch code being refactored
       * Trigger build/rebuild
       * Inspect agent prompts and decisions
     * **In Runtime Mode:**
       * Display static code graph
       * Monitor program execution
       * Show message flows (no agent reasoning)
       * Standard debugging/logging
   * Renders:
     * graph views (nodes/edges)
     * agent conversation timelines (Build Mode)
     * execution logs (Runtime Mode)
     * node details and code diffs

---

## 2. Core Concepts & Primitives

These are the building blocks the library must expose and internally rely on.

### 2.1 Node / ClassAgent

Each **Python class** that participates is a GraphBus node, and in **Build Mode**, each node has an **active LLM agent** associated with it.

**Primitive:** `GraphBusNode` (base class)

**Build Mode Responsibilities (Agent Active):**

* **LLM-Powered Agent** with system prompt defining its role
* Can **read and analyze** its associated source code file
* Can **propose code changes** via negotiation primitives
* Can **evaluate proposals** from other agents
* Can **commit agreed-upon changes** to source files
* Participates in **schema negotiation** with other agents
* Uses the GraphBus to send/receive messages during refactoring

**Runtime Mode Responsibilities (Agent Dormant):**

* Define **system prompt** (metadata only, not used for LLM)
* Register **methods as tools** (for static execution)
* Declare **schemas** for methods (documentation/validation)
* Declare **subscriptions** to topics (static pub/sub routing)
* Provide a `handle_event(topic, payload)` hook (pure code execution)

Example usage by a dev:

```python
from graphbus_core import GraphBusNode, schema_method, subscribe

class InventoryService(GraphBusNode):
    SYSTEM_PROMPT = "You manage product quantity and stock allocation."

    @schema_method(
        input_schema={"sku": str, "qty": int},
        output_schema={"available": bool}
    )
    def check_stock(self, sku: str, qty: int):
        # business logic
        ...

    @subscribe("/Order/Created")
    def on_order_created(self, event):
        # react to new orders
        ...
```

### 2.2 System Prompt

**Primitive:** `SystemPrompt`

The system prompt is the **LLM instruction** that powers each agent in Build Mode.

* Defines the agent's **role, responsibilities, and domain knowledge**
* Instructs the agent on **how to negotiate with other agents**
* Guides **code refactoring decisions** the agent can make
* In Runtime Mode, this becomes **documentation metadata only**

```python
@dataclass
class SystemPrompt:
    text: str
    role: str | None = None  # e.g. "payment_processor", "inventory_manager"
    capabilities: list[str] = None  # e.g. ["refactor_methods", "add_validation"]
```

Example:

```python
SYSTEM_PROMPT = """
You are the InventoryService agent. Your role is to manage product stock levels.

In Build Mode, you can:
- Negotiate with OrderService about stock allocation schemas
- Propose adding validation for SKU formats
- Refactor your check_stock method to match agreed schemas
- Evaluate proposals from other agents about inventory APIs

Always ensure stock levels are tracked accurately in your code.
"""
```

Included in each `GraphBusNode` via `SYSTEM_PROMPT`.

### 2.3 Schema

**Primitive:** `Schema`, `SchemaMethod`

Used to describe input/output contracts for methods.

```python
@dataclass
class Schema:
    fields: dict[str, type]   # or richer type system later
    description: str | None = None

@dataclass
class SchemaMethod:
    name: str
    input_schema: Schema
    output_schema: Schema
```

Exposed via decorator `@schema_method(...)` and introspected in Build Mode.

### 2.4 Topics & Subscriptions (Pub/Sub)

**Primitive:** `Topic`, `Subscription`

```python
@dataclass(frozen=True)
class Topic:
    name: str  # e.g. "/Order/Created"

@dataclass
class Subscription:
    node_name: str
    topic: Topic
    handler_name: str  # method to call when event arrives
```

### 2.5 Message (Direct Routing)

**Primitive:** `Message`

```python
from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class Message:
    msg_id: str
    src: str
    dst: str
    method: str
    payload: Dict[str, Any]
    context: Dict[str, Any] | None = None
    timestamp: float | None = None
```

### 2.6 Event (Pub/Sub)

**Primitive:** `Event`

```python
@dataclass
class Event:
    event_id: str
    topic: str
    src: str
    payload: dict
    timestamp: float | None = None
```

### 2.7 Negotiation (Build Mode Only)

**Critical:** Negotiation primitives are **only active in Build Mode** when agents are refactoring code.

In Build Mode, agents use these to collaboratively modify source code:

```python
@dataclass
class Proposal:
    proposal_id: str
    round: int  # negotiation round number
    src: str  # agent proposing
    dst: str | None  # target agent (or None for broadcast)
    intent: str  # e.g. "refactor_schema", "add_validation", "rename_method"
    code_change: CodeChange  # structured code change details
    schema_change: SchemaChange | None  # input/output schema modifications
    reason: str  # LLM-generated explanation
    dependencies: list[str]  # other proposals this depends on
    priority: int  # urgency (higher = more important)

@dataclass
class CodeChange:
    file_path: str
    target: str  # method name or class name
    change_type: str  # "modify", "add", "delete"
    old_code: str
    new_code: str
    diff: str | None  # unified diff format

@dataclass
class ProposalEvaluation:
    proposal_id: str
    evaluator: str  # agent evaluating
    round: int
    decision: str  # "accept" | "reject" | "counter" | "defer"
    reasoning: str  # LLM-generated reasoning
    confidence: float  # 0.0-1.0, LLM confidence
    concerns: list[str] | None  # specific issues identified
    suggestions: list[str] | None  # improvements even if accepting
    counter_proposal: Proposal | None = None
    impact_assessment: dict | None  # risk analysis

@dataclass
class CommitRecord:
    commit_id: str
    proposal_id: str
    round: int
    proposer: str
    evaluators: list[str]  # all agents who evaluated
    consensus_type: str  # "unanimous", "majority", "arbiter"
    resolution: dict  # final agreed-upon changes
    files_modified: list[str]  # which source files were changed
    schema_changes: list[SchemaChange]
    timestamp: float
    negotiation_log: list[dict]  # full conversation history
```

`GraphBusNode` provides methods (Build Mode only):

```python
class GraphBusNode:
    ...

    def propose(self, proposal: Proposal) -> None:
        """Agent proposes a code change to other agents"""
        ...

    def evaluate(self, proposal: Proposal) -> ProposalEvaluation:
        """Agent evaluates another agent's proposal using LLM"""
        ...

    def commit(self, commit: CommitRecord) -> None:
        """Agent applies agreed-upon changes to source files"""
        ...
```

In Runtime Mode, these methods are **never called** - code is immutable.

### 2.8 Memory

**Primitive:** `NodeMemory`

Agent-local memory for maintaining context.

**Build Mode:** Used by LLM agents to track negotiation history and decisions.

```python
@dataclass
class NodeMemory:
    state: dict[str, Any]  # current agent state
    history: list[dict]  # logs, observations, negotiation outcomes
    code_understanding: dict  # agent's analysis of its source code
    pending_proposals: list[str]  # proposal IDs awaiting resolution
```

**Runtime Mode:** Minimal or unused - execution is stateless code execution.

### 2.9 Graph Model (networkx)

**Primitive:** `GraphBusGraph` (wrapper around `networkx.DiGraph`)

Nodes store metadata about each class; edges represent dependencies or key relationships.

Graph node attributes:

* `node_name`
* `module`
* `class_name`
* `system_prompt`
* `schemas`
* `subscriptions`
* `metadata`

Graph edge attributes:

* `edge_type` (e.g. `"depends_on"`, `"calls"`, `"schema_depends"`)
* `metadata` (reason/source of edge, e.g. constructor argument, decorator)

**Build Mode Usage:**

In Build Mode, the graph is used for **agent orchestration**:

* `AgentGraph.get_agent_activation_order()` uses `networkx.topological_sort()` to determine which agents activate first
* Agents with no dependencies activate first
* Agents with dependencies activate after their dependencies are ready
* This ensures proper negotiation order based on code structure

### 2.10 Safety Guardrails (Build Mode Only)

**Primitive:** `SafetyConfig`

Safety guardrails prevent runaway negotiation and protect code integrity during Build Mode:

```python
@dataclass
class SafetyConfig:
    # Negotiation limits
    max_negotiation_rounds: int = 10  # Max rounds before forcing termination
    max_proposals_per_agent: int = 3  # Max proposals each agent can make total
    max_proposals_per_round: int = 1  # Max proposals per agent per round
    max_back_and_forth: int = 3  # Max times a proposal can be re-evaluated
    convergence_threshold: int = 2  # Rounds with no new proposals = converged

    # Arbiter configuration
    require_arbiter_on_conflict: bool = True  # Require arbiter when agents disagree
    arbiter_agents: list[str] = []  # Names of arbiter agents

    # File protection
    max_file_changes_per_commit: int = 1  # Max files a single commit can modify
    max_total_file_changes: int = 10  # Max total files modified in entire build
    allow_external_dependencies: bool = False  # Allow adding new imports
    protected_files: list[str] = []  # Files that can't be modified
```

**Key Safety Features:**

1. **Proposal Rate Limiting**: Each agent has a budget of proposals to prevent spam
2. **Round Limits**: Negotiation automatically terminates after max rounds
3. **Convergence Detection**: Stops when no new proposals for N consecutive rounds
4. **File Modification Limits**: Caps total files that can be changed
5. **Protected Files**: Certain files can be marked as immutable
6. **Arbiter Requirement**: Conflicts trigger automatic arbiter invocation

### 2.11 Arbiter Agents (Build Mode Only)

**Primitive:** Arbiter Agent (special `GraphBusNode` with `IS_ARBITER = True`)

Arbiter agents are impartial agents that resolve conflicts when regular agents disagree:

```python
class ArbiterService(GraphBusNode):
    SYSTEM_PROMPT = """
    You are an impartial arbiter agent responsible for resolving conflicts
    during code negotiations. Review proposals that have conflicting evaluations
    and make fair, unbiased decisions based on engineering principles.
    """

    IS_ARBITER = True  # Mark this as an arbiter agent
```

**Arbiter Behavior:**

* **Invoked Automatically**: When evaluations are tied or close (e.g., 2 accept vs 2 reject)
* **Reviews All Evidence**: Sees the proposal and all agent evaluations
* **Makes Final Decision**: Arbiter decision is binding
* **LLM-Powered**: Uses LLM to analyze technical merits and make judgment

**Arbitration Flow:**

1. Regular agents evaluate a proposal → results in tie or close vote
2. `NegotiationEngine` detects conflict (if `require_arbiter_on_conflict = True`)
3. Engine invokes `arbiter.arbitrate_conflict(proposal, evaluations, round)`
4. Arbiter agent uses LLM to review:
   - The proposed code change
   - Each agent's evaluation and reasoning
   - Technical correctness and system impact
5. Arbiter returns final evaluation (accept or reject)
6. Arbiter's decision becomes the commit decision

---

## 3. Python Package Layout

Proposed package structure:

```text
graphbus_core/
    __init__.py
    build/                  # Build Mode: Agent Orchestration & Code Refactoring
        __init__.py
        scanner.py          # module/class discovery + source code reading
        extractor.py        # schema/prompt/dep extraction + code analysis
        graph_builder.py    # builds agent DAG with networkx
        agent_orchestrator.py  # activates agents in topological order
        code_writer.py      # applies agent-agreed code changes to files
        artifacts.py        # JSON artifact format + build log
    runtime/                # Runtime Mode: Static Code Execution
        __init__.py
        loader.py           # ArtifactLoader (loads build artifacts)
        message_bus.py      # MessageBus (pub/sub routing)
        event_router.py     # EventRouter (dispatches events to handlers)
        executor.py         # RuntimeExecutor (main orchestration)
    agents/                 # Build Mode: LLM Agent Infrastructure
        __init__.py
        agent.py            # LLM-powered agent wrapper
        negotiation.py      # negotiation engine (proposals/evaluations/commits)
        memory.py           # agent memory for negotiation context
    model/
        __init__.py
        graph.py            # GraphBusGraph / AgentGraph wrapper
        message.py          # Message/Event/Proposal/etc
        schema.py           # Schema primitives + validators
        topic.py            # Topic/Subscription
        prompt.py           # SystemPrompt
        agent_def.py        # AgentDefinition (includes source_code)
        serialization.py    # Dataclass models for JSON deserialization
    api/
        __init__.py
        public_api.py       # high-level Python API
        server.py           # HTTP/WebSocket server for Swift
    decorators.py           # @schema_method, @subscribe, etc.
    node_base.py            # GraphBusNode base class
    config.py               # configuration objects (BuildConfig, LLMConfig)
```

---

## 4. Build Mode Design (Agent Orchestration & Code Refactoring)

**Key Concept:** Build Mode is where **agents come alive** and **code is mutable**.

### 4.1 Build Flow

1. **Configuration**
   `BuildConfig` specifying:
   * root module/package
   * file patterns (e.g. `agents/*.py`)
   * list of modules to include/exclude
   * LLM configuration (model, API keys)
   * refactoring goals/constraints
   * **safety configuration** (negotiation limits, arbiter settings)

   ```python
   @dataclass
   class BuildConfig:
       root_package: str
       include_modules: list[str] | None = None
       exclude_modules: list[str] | None = None
       llm_config: LLMConfig | None = None  # for agent execution
       refactoring_goals: list[str] | None = None
       safety_config: SafetyConfig = field(default_factory=SafetyConfig)  # safety guardrails
       output_dir: str = ".graphbus"
       enable_human_in_loop: bool = False
   ```

2. **Module & Class Discovery (`scanner.py`)**
   * Use `importlib` and `pkgutil` to walk packages.
   * Import each module.
   * Introspect for subclasses of `GraphBusNode`.
   * **Read source code files** for each discovered class.

   Output: list of `(module, class_obj, source_file_path)`.

3. **Metadata Extraction (`extractor.py`)**
   For each `GraphBusNode` subclass:
   * `SYSTEM_PROMPT` (becomes LLM instruction)
   * schema-decorated methods (input/output types)
   * `SUBSCRIBE` declarations
   * implicit dependencies:
     * from explicit decorators (`@depends_on`)
     * from method type hints referencing other node classes
   * **Source code content** for the class

   Output: set of `AgentDefinition` objects:

   ```python
   @dataclass
   class AgentDefinition:
       name: str
       module: str
       class_name: str
       source_file: str  # path to .py file
       source_code: str  # actual code content
       system_prompt: SystemPrompt
       methods: list[SchemaMethod]
       subscriptions: list[Subscription]
       metadata: dict
   ```

4. **Graph Construction (`graph_builder.py`)**
   * Create `networkx.DiGraph()` representing agent dependencies.
   * Add nodes using `AgentDefinition`.
   * Add edges for:
     * `@depends_on` metadata
     * schema dependencies (producer → consumer relationships)
     * pub/sub topic relationships
   * **Topological sort** to determine agent activation order.

   Output: `AgentGraph` (DAG for orchestration).

5. **Agent Activation & Orchestration (`orchestrator.py`)**
   * **Topological Sort**: Use `networkx.topological_sort()` on AgentGraph to determine activation order
   * For each agent in topological order:
     * Instantiate LLM-powered agent with system prompt
     * Provide agent with:
       * its source code
       * graph context (which agents it depends on)
       * negotiation engine with safety limits
     * Agent analyzes its code
     * Agent checks for schema mismatches with dependencies
     * Agent may propose changes or request changes from dependencies
   * **Multi-Round Negotiation Loop**:
     * **Round N** (up to `max_negotiation_rounds`):
       1. **Proposal Phase**: Agents propose improvements (subject to rate limits)
       2. **Evaluation Phase**: All agents evaluate all proposals using LLM
       3. **Conflict Detection**: Check for ties or close votes
       4. **Arbiter Invocation**: If conflict detected and arbiter required, invoke arbiter
       5. **Commit Creation**: Create commits for accepted proposals
       6. **Apply Changes**: Modify source files on disk
       7. **Convergence Check**: Check if no new proposals for N rounds
     * Repeat until:
       * Convergence (no new proposals for `convergence_threshold` rounds), OR
       * Max rounds reached (`max_negotiation_rounds`), OR
       * Max file changes reached (`max_total_file_changes`)
   * **Safety Enforcement**: All limits enforced by `NegotiationEngine`

6. **Artifact Generation (`artifacts.py`)**
   * **Modified source code files** are written to disk
   * Serialize final graph + nodes + schemas + topics into JSON
   * Artifact files:
     * `graphbus_graph.json`
     * `graphbus_nodes.json`
     * `graphbus_schemas.json`
     * `graphbus_topics.json`
     * `build_log.json` (agent negotiation history)

### 4.2 Build Mode Public API

```python
from graphbus_core.build import BuildConfig, build_project

config = BuildConfig(
    root_package="my_project.agents",
    llm_config=LLMConfig(model="claude-sonnet-4", api_key="..."),
    refactoring_goals=["align_schemas", "add_validation"]
)

# This activates agents and runs negotiation/refactoring
artifacts = build_project(config)

# Agents have now modified source code files
# artifacts contain the final state
```

`build_project` returns an object like:

```python
@dataclass
class BuildArtifacts:
    graph: AgentGraph  # final dependency graph
    agents: list[AgentDefinition]  # agent metadata
    topics: list[Topic]
    subscriptions: list[Subscription]
    negotiations: list[CommitRecord]  # history of code changes
    modified_files: list[str]  # which files were changed
    output_dir: str
```

---

## 5. Runtime Mode Design (Static Code Execution)

**Key Concept:** Runtime Mode is where **agents are dormant** and **code is immutable**.

### 5.1 Runtime Architecture

Runtime Mode consists of four main components:

1. **ArtifactLoader** - Loads and deserializes build artifacts
2. **MessageBus** - Synchronous pub/sub message routing
3. **EventRouter** - Routes events to node handler methods
4. **RuntimeExecutor** - Orchestrates the runtime lifecycle

### 5.2 ArtifactLoader

**Primitive:** `ArtifactLoader` (`graphbus_core/runtime/loader.py`)

Responsibilities:

* Load and validate build artifacts from `.graphbus/` directory
* Deserialize JSON into proper dataclass models
* Provide access to graph, agents, topics, and subscriptions

```python
class ArtifactLoader:
    def __init__(self, artifacts_dir: str):
        self.artifacts_dir = Path(artifacts_dir)
        self._validate_directory()

    def load_graph(self) -> AgentGraph:
        """Load NetworkX graph structure"""
        graph_path = self.artifacts_dir / "graph.json"
        graph_data = GraphData.from_dict(json.load(open(graph_path)))
        # Reconstruct AgentGraph from nodes/edges
        ...

    def load_agents(self) -> List[AgentDefinition]:
        """Load all agent definitions with source code"""
        agents_path = self.artifacts_dir / "agents.json"
        return [AgentDefinition.from_dict(a) for a in json.load(open(agents_path))]

    def load_topics(self) -> List[TopicData]:
        """Load topic definitions"""
        ...

    def load_subscriptions(self) -> List[Dict[str, str]]:
        """Load subscription mappings"""
        ...

    def get_agent_by_name(self, name: str) -> AgentDefinition:
        """Get specific agent definition"""
        ...

    def validate_artifacts(self) -> List[str]:
        """Validate artifact integrity"""
        ...
```

**Artifacts Loaded:**

* `graph.json` - Agent dependency graph (NetworkX format)
* `agents.json` - Agent definitions with source code
* `topics.json` - Topic definitions and subscriptions
* `build_summary.json` - Build metadata

### 5.3 MessageBus

**Primitive:** `MessageBus` (`graphbus_core/runtime/message_bus.py`)

Responsibilities:

* Synchronous publish-subscribe message routing
* Topic-based subscription management
* Message history tracking
* Statistics and monitoring
* Error handling for failed handlers

```python
class MessageBus:
    def __init__(self):
        self._subscriptions: Dict[str, List[tuple[Callable, str]]] = defaultdict(list)
        self._message_history: List[Event] = []
        self._stats = {"messages_published": 0, "messages_delivered": 0, "errors": 0}
        self._dispatcher: Optional[EventRouter] = None

    def subscribe(self, topic: str, handler: Callable, subscriber_name: str):
        """Register handler for topic"""
        if not callable(handler):
            raise ValueError("Handler must be callable")
        self._subscriptions[topic].append((handler, subscriber_name))

    def unsubscribe(self, topic: str, handler: Callable):
        """Remove handler from topic"""
        ...

    def publish(self, topic: str, payload: Dict[str, Any], source: str = "system") -> Event:
        """Publish event to topic"""
        event = Event(
            event_id=generate_id("event_"),
            topic=topic,  # String not Topic object
            src=source,
            payload=payload
        )
        self._add_to_history(event)
        self._stats["messages_published"] += 1
        if self._dispatcher:
            self._dispatcher.dispatch_event(event)
        else:
            self.dispatch_event(event)
        return event

    def dispatch_event(self, event: Event):
        """Dispatch event to all subscribers"""
        for handler, subscriber_name in self._subscriptions.get(event.topic, []):
            try:
                handler(event)
                self._stats["messages_delivered"] += 1
            except Exception as e:
                print(f"[MessageBus] Error in {subscriber_name}: {e}")
                self._stats["errors"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        return {
            "messages_published": self._stats["messages_published"],
            "messages_delivered": self._stats["messages_delivered"],
            "errors": self._stats["errors"],
            "total_subscriptions": sum(len(subs) for subs in self._subscriptions.values()),
            "topics_with_subscribers": len(self._subscriptions)
        }

    def get_message_history(self, limit: int = 100) -> List[Event]:
        """Get recent message history (newest first)"""
        return self._message_history[:limit]
```

**Key Features:**

* Topic-based routing (e.g., `/Hello/MessageGenerated`)
* Multiple subscribers per topic
* Message history with configurable size limit
* Statistics tracking (published, delivered, errors)
* Error isolation (one handler failure doesn't stop others)

### 5.4 EventRouter

**Primitive:** `EventRouter` (`graphbus_core/runtime/event_router.py`)

Responsibilities:

* Route events to node handler methods
* Smart handler signature detection
* Automatic parameter matching
* Error handling for failed handlers

```python
class EventRouter:
    def __init__(self, bus: MessageBus):
        self.bus = bus
        self._node_handlers: Dict[str, List[tuple[GraphBusNode, str]]] = defaultdict(list)

    def register_handler(self, topic: str, node: GraphBusNode, handler_name: str):
        """Register node handler for topic"""
        self._node_handlers[topic].append((node, handler_name))

    def unregister_node(self, node: GraphBusNode):
        """Unregister all handlers for a node"""
        for topic in self._node_handlers:
            self._node_handlers[topic] = [
                (n, h) for n, h in self._node_handlers[topic] if n != node
            ]

    def route_event_to_node(self, node: GraphBusNode, handler_name: str, event: Event):
        """Route event to specific handler with smart signature detection"""
        try:
            handler = getattr(node, handler_name)
            sig = inspect.signature(handler)
            params = list(sig.parameters.keys())

            # Handler is bound method - self already applied
            if len(params) == 0:
                handler()  # No params
            elif len(params) == 1:
                handler(event.payload)  # One param - pass payload dict
            else:
                handler(event)  # Multiple params - pass Event object
        except Exception as e:
            print(f"[EventRouter] Error executing {node.name}.{handler_name}(): {e}")

    def dispatch_event(self, event: Event):
        """Dispatch event to all registered handlers"""
        for node, handler_name in self._node_handlers.get(event.topic, []):
            self.route_event_to_node(node, handler_name, event)

    def get_handlers_for_topic(self, topic: str) -> List[tuple[GraphBusNode, str]]:
        """Get all handlers registered for topic"""
        return self._node_handlers.get(topic, [])
```

**Handler Signature Detection:**

The EventRouter intelligently detects handler signatures and passes appropriate arguments:

```python
# No parameters - handler called with no arguments
def on_event(self):
    pass

# One parameter - receives payload dict (most common)
def on_event(self, payload):
    data = payload.get('data')

# Multiple parameters - receives Event object
def on_event(self, event: Event):
    topic = event.topic
    payload = event.payload
```

### 5.5 RuntimeExecutor

**Primitive:** `RuntimeExecutor` (`graphbus_core/runtime/executor.py`)

Responsibilities:

* Orchestrate runtime lifecycle (start/stop)
* Load artifacts via ArtifactLoader
* Dynamically instantiate nodes from source code
* Setup message bus and subscriptions
* Provide API for direct method calls and event publishing
* Track runtime statistics

```python
class RuntimeExecutor:
    def __init__(self, artifacts_dir: str, enable_message_bus: bool = True):
        self.artifacts_dir = artifacts_dir
        self.enable_message_bus = enable_message_bus
        self.loader = ArtifactLoader(artifacts_dir)

        # Runtime state
        self.graph: Optional[AgentGraph] = None
        self.agent_defs: Optional[List[AgentDefinition]] = None
        self.topics: Optional[List[TopicData]] = None
        self.subscriptions: Optional[List[Dict[str, str]]] = None
        self.nodes: Dict[str, GraphBusNode] = {}
        self.bus: Optional[MessageBus] = None
        self.router: Optional[EventRouter] = None
        self._is_running = False

    def start(self):
        """Start runtime - load artifacts, initialize nodes, setup message bus"""
        print("="*60)
        print("GRAPHBUS RUNTIME MODE - STARTING")
        print("="*60)

        self.load_artifacts()
        self.initialize_nodes()
        if self.enable_message_bus:
            self.setup_message_bus()

        self._is_running = True
        print(f"RUNTIME READY - {len(self.nodes)} nodes active")

    def load_artifacts(self):
        """Load all artifacts"""
        self.graph, self.agent_defs, self.topics, self.subscriptions = self.loader.load_all()

    def initialize_nodes(self):
        """Dynamically instantiate nodes from source code"""
        for agent_def in self.agent_defs:
            # Execute source code to define class
            namespace = {}
            exec(agent_def.source_code, namespace)

            # Instantiate class
            node_class = namespace[agent_def.class_name]
            node = node_class(bus=None, memory=None)
            node.set_mode("runtime")
            node.name = agent_def.name

            self.nodes[agent_def.name] = node

    def setup_message_bus(self):
        """Setup message bus with subscriptions"""
        self.bus = MessageBus()
        self.router = EventRouter(self.bus)
        self.bus._dispatcher = self.router

        # Register subscriptions
        for subscription in self.subscriptions:
            agent_name = subscription['agent']
            topic = subscription['topic']
            handler = subscription['handler']

            if agent_name in self.nodes:
                node = self.nodes[agent_name]
                self.router.register_handler(topic, node, handler)

    def call_method(self, node_name: str, method_name: str, **kwargs) -> Any:
        """Call node method directly"""
        if not self._is_running:
            raise RuntimeError("Runtime not started")
        if node_name not in self.nodes:
            raise ValueError(f"Node '{node_name}' not found")

        node = self.nodes[node_name]
        method = getattr(node, method_name)
        return method(**kwargs)

    def publish(self, topic: str, payload: Dict[str, Any], source: str = "runtime"):
        """Publish event through message bus"""
        if self.bus is None:
            raise RuntimeError("Message bus not enabled")
        self.bus.publish(topic, payload, source)

    def get_node(self, name: str) -> Optional[GraphBusNode]:
        """Get node instance by name"""
        return self.nodes.get(name)

    def get_all_nodes(self) -> Dict[str, GraphBusNode]:
        """Get all node instances"""
        return self.nodes

    def get_stats(self) -> Dict[str, Any]:
        """Get runtime statistics"""
        stats = {
            "is_running": self._is_running,
            "nodes_count": len(self.nodes),
            "message_bus": None
        }
        if self.bus:
            stats["message_bus"] = self.bus.get_stats()
        return stats

    def stop(self):
        """Stop runtime"""
        self._is_running = False
        print("RUNTIME STOPPED")


def run_runtime(artifacts_dir: str) -> RuntimeExecutor:
    """Convenience function to start runtime"""
    executor = RuntimeExecutor(artifacts_dir)
    executor.start()
    return executor
```

### 5.6 Runtime Workflow

**Standard Workflow:**

```python
from graphbus_core.runtime.executor import RuntimeExecutor

# 1. Initialize
executor = RuntimeExecutor('.graphbus')

# 2. Start (loads artifacts, initializes nodes, sets up message bus)
executor.start()

# 3. Direct method calls
result = executor.call_method('HelloService', 'generate_message')

# 4. Publish events
executor.publish('/Hello/MessageGenerated', {'message': result}, source='HelloService')

# 5. Query state
stats = executor.get_stats()
node = executor.get_node('HelloService')

# 6. Stop
executor.stop()
```

**Message Flow:**

```
1. Producer publishes event
   └─> bus.publish('/data/produced', {'value': 42}, source='Producer')

2. MessageBus creates Event object
   └─> Event(event_id=..., topic='/data/produced', src='Producer', payload={'value': 42})

3. MessageBus dispatches to EventRouter
   └─> router.dispatch_event(event)

4. EventRouter finds registered handlers
   └─> handlers = _node_handlers['/data/produced']  # [(ConsumerNode, 'on_data_produced')]

5. EventRouter routes to each handler (with signature detection)
   └─> ConsumerNode.on_data_produced({'value': 42})  # Passes payload dict

6. Handler processes and may publish next event
   └─> bus.publish('/data/consumed', {...}, source='Consumer')
```

### 5.7 No Negotiation Engine in Runtime

**Critical:** `NegotiationEngine` **does not exist** in Runtime Mode.

* Code cannot be modified
* No proposals or evaluations
* No LLM calls
* Agents are dormant metadata only
* Pure deterministic execution

### 5.8 Runtime Mode Features

**Implemented Features:**

* ✅ Artifact loading and validation
* ✅ Dynamic node instantiation from source code
* ✅ Synchronous pub/sub message bus
* ✅ Smart event routing with signature detection
* ✅ Direct method invocation
* ✅ Message history tracking
* ✅ Runtime statistics and monitoring
* ✅ Error isolation (handler failures don't crash system)
* ✅ Multiple subscribers per topic
* ✅ Configurable message bus (can be disabled)

**Future Enhancements:**

* Async/await support for event handlers
* Persistent storage (save/restore runtime state)
* Distributed execution (nodes across processes/machines)
* Hot reload (update nodes without full restart)
* Metrics export (Prometheus/OpenTelemetry)
* Event replay for debugging
* Handler middleware for cross-cutting concerns
* Type validation for payload schemas

---

## 6. Swift macOS Frontend Integration

We need a clear contract between **graphbus-core (Python)** and **SwiftUI app**.

### 6.1 Transport Choice

Two practical options:

1. **Local HTTP + WebSocket server** inside `graphbus_core.api.server`.
   * Swift uses `URLSession` + `WebSocketTask`.
2. **Local domain socket / XPC** (more complex, more native).

For v1, HTTP+WebSocket is simpler and flexible.

### 6.2 Python API Server (`api/server.py`)

Expose endpoints like:

* `GET /graph`
  → Returns nodes, edges, metadata.

* `GET /nodes`
  → Returns list of node definitions.

* `GET /nodes/{name}`
  → Returns node details (prompt, schemas, topics, subscriptions).

* `POST /runtime/start`
  → Starts runtime engine.

* `POST /runtime/stop`
  → Stops runtime.

* `POST /nodes/{name}/call`
  → Sends a direct message to node (test call).

* `POST /publish`
  → Publish event to topic.

* `GET /events/stream` (WebSocket)
  → Push logs of:
  * messages
  * events
  * proposals
  * commits

Swift frontend can:

* render graph from `/graph`
* display node details from `/nodes/{name}`
* react in real time to `/events/stream` (WebSocket).

### 6.3 Swift Frontend Responsibilities (high-level)

* **Graph view**: using `SwiftUI` + a layout algorithm (force-directed, or simple level-based).
* **Node inspector**:
  * system prompt
  * schemas
  * topics/subscriptions
* **Runtime control**:
  * start/stop runtime
  * send test requests to nodes
  * publish events to topics
* **Event stream** view:
  * show messages/negotiations as a timeline.

Swift doesn't need to know about `networkx` directly; it operates purely on JSON returned by the API.

---

## 7. Primitives Summary Checklist

For **graphbus-core** to be usable and coherent, we need the following primitives implemented:

### 7.1 Model Layer

* `SystemPrompt`
* `Schema`
* `SchemaMethod`
* `Topic`
* `Subscription`
* `Message`
* `Event`
* `Proposal`
* `ProposalEvaluation`
* `CommitRecord`
* `NodeDefinition`
* `NodeMemory`
* `GraphBusGraph` (wrapper around `networkx.DiGraph`)

### 7.2 Base Classes & Decorators

* `GraphBusNode` (base class)
* Decorators:
  * `@schema_method(input_schema, output_schema)`
  * `@subscribe(topic_name)`
  * (optional) `@depends_on(other_node_name)`

### 7.3 Build Mode (Agent-Driven)

* `BuildConfig` (with LLM config and SafetyConfig)
* `SafetyConfig` (negotiation limits and guardrails)
* `NodeScanner` (module/class discovery + source code reading)
* `MetadataExtractor` (extracts prompts, schemas, code, IS_ARBITER flag)
* `GraphBuilder` (builds agent DAG with `networkx`)
* `AgentOrchestrator` (activates agents in topological order, multi-round orchestration)
* `NegotiationEngine` (manages proposals/evaluations/commits with safety enforcement)
  * Proposal rate limiting per agent
  * Round tracking and convergence detection
  * Automatic arbiter invocation on conflicts
  * File modification limits
* `LLMAgent` (agent with `analyze_code`, `propose_improvement`, `evaluate_proposal`, `arbitrate_conflict` methods)
* Arbiter agents (special agents with `IS_ARBITER = True`)
* `CodeWriter` (applies agent-agreed changes to files)
* `BuildArtifacts` (includes modified file list)
* `build_project(config: BuildConfig) -> BuildArtifacts`

### 7.4 Runtime Mode (Static Execution)

* `RuntimeEngine` (loads and executes static code)
* `SimpleMessageBus` (optional static pub/sub routing)
* No `NegotiationEngine`
* No `NodeMemory` (or minimal for execution state only)
* No LLM integration

### 7.5 API / Integration

* REST + WebSocket server for:
  * graph introspection
  * runtime control
  * event streaming

---

## 8. Example Flow (End-to-End)

### 8.1 Build Mode (Agent-Driven Refactoring)

1. Dev creates Python package `my_project.agents` with classes inheriting `GraphBusNode`:

   ```python
   class OrderService(GraphBusNode):
       SYSTEM_PROMPT = "You manage orders. Ensure schema compatibility with InventoryService."

       @schema_method(input_schema={"order_id": str}, output_schema={"status": str})
       def create_order(self, order_id: str):
           # initial implementation
           ...
   ```

2. Dev runs Build Mode:

   ```bash
   python -m graphbus_core.build --root my_project.agents --llm-model claude-sonnet-4
   ```

   This:
   * Scans modules and reads source code
   * Activates LLM agents (one per class)
   * Agents analyze code and dependencies
   * Agents negotiate schema changes via GraphBus
   * **OrderService agent** might propose changing its output schema
   * **InventoryService agent** evaluates and accepts/counters
   * Consensus is reached → **source files are modified**
   * Writes JSON artifacts + build log to `.graphbus/`

3. Dev can observe in macOS app:
   * Agent conversation timeline
   * Proposed code changes
   * Schema negotiations
   * Final code diffs

### 8.2 Runtime Mode (Static Execution)

4. Dev runs Runtime Mode:

   ```bash
   python -m graphbus_core.runtime --artifacts .graphbus/
   ```

   This:
   * Loads the **refactored code** (agents are dormant)
   * Simply executes Python normally
   * No LLM calls, no negotiations
   * Pure code execution

5. Dev can observe in macOS app:
   * Static graph view
   * Function call traces
   * Standard logs

---

## 9. Open Questions / Future Extensions

* **Type System**: start with `type` hints; later support Pydantic or `typing.Annotated`.
* **Async Runtime**: move from sync calls to full `asyncio`-based message loops.
* **Multi-process / Multi-host**: distribute nodes across processes or machines.
* **Persistence**: durable NodeMemory and event logs.
* **Policy Engine**: constraints on which nodes can talk / subscribe to what.
* **LLM Integration**: pluggable LLM calls inside NodeRuntime (to interpret prompts, etc.).

---

If you'd like, next step could be:

* a **concrete `graphbus_core` skeleton repo layout** with minimal working code, or
* a **more detailed spec for the decorators and Node API**, so your first implementation is frictionless.

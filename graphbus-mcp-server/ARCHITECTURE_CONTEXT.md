# GraphBus Architecture Context for Claude Code

This document provides complete architectural context for Claude Code when using GraphBus MCP tools. Claude should reference this to understand sequencing, workflows, and when to use each command.

---

## Core Concepts

### 1. Two-Phase Architecture: Build Mode vs Runtime Mode

GraphBus operates in **two distinct modes** that MUST be understood to use the system correctly:

#### **Build Mode** (Compile Time)
- **Purpose**: Analyze agent source code and generate executable artifacts
- **Input**: Python files with `@agent` decorated classes in `agents/` directory
- **Output**: `.graphbus/` directory containing:
  - `agents.json` - Agent definitions with extracted metadata
  - `graph.json` - Dependency graph (NetworkX serialized)
  - `topics.json` - Topic registry with publishers/subscribers
  - `subscriptions.json` - Subscription mappings
  - `build_summary.json` - Build metadata
  - `modules/` - Prepared agent code
- **When**: After writing/modifying agent code, before execution
- **Commands**: `graphbus_build`, `graphbus_validate`, `graphbus_inspect`
- **Analogy**: Like compiling code - validates structure, resolves dependencies, prepares for execution

#### **Runtime Mode** (Execution Time)
- **Purpose**: Load artifacts and execute the agent system
- **Input**: `.graphbus/` artifacts from build phase
- **Output**: Running system with live agents, message bus, event processing
- **When**: After successful build, when ready to execute
- **Commands**: `graphbus_run`, `graphbus_call`, `graphbus_publish`, `graphbus_stats`
- **Analogy**: Like running compiled code - executes the prepared system

#### **Key Rule**: ALWAYS build before run. Runtime CANNOT run without build artifacts.

**Typical Flow**:
```
1. Write agents (Python files) → agents/*.py
2. BUILD MODE: graphbus build agents/ → creates .graphbus/
3. INSPECT (optional): graphbus inspect .graphbus/ → verify structure
4. RUNTIME MODE: graphbus run .graphbus/ → starts execution
5. INTERACT: graphbus call/publish → test running system
6. MODIFY agents → go back to step 2
```

---

### 2. NetworkX DAG (Directed Acyclic Graph) System

GraphBus uses **NetworkX** extensively for graph-based agent coordination:

#### **Agent Dependency Graph**
- **Structure**: DAG where nodes = agents, edges = dependencies
- **Purpose**: Determine activation order, validate no circular dependencies
- **Built During**: Build phase (graphbus_build)
- **Used For**:
  - Topological sort to get agent initialization order
  - Dependency validation (cycles = build error)
  - Impact analysis for contract changes
  - Visualization of system structure

#### **How Dependencies Are Determined**:
1. **Direct Method Calls**: If AgentA calls AgentB.method → AgentA depends on AgentB
2. **Topic Subscriptions**: If AgentA publishes to `/topic` and AgentB subscribes → edge in event flow graph
3. **Explicit Dependencies**: Defined in `@agent(depends_on=["ServiceB"])`

#### **Activation Order**:
```python
# NetworkX topological sort ensures correct startup order
import networkx as nx

graph = nx.DiGraph()
graph.add_edge("OrderService", "PaymentService")  # Order depends on Payment
graph.add_edge("PaymentService", "NotificationService")  # Payment depends on Notification

# Activation order: NotificationService → PaymentService → OrderService
activation_order = list(nx.topological_sort(graph))
```

#### **Contract Impact Analysis** (Tranche 4 feature):
```python
# When OrderService contract changes, find all downstream agents
import networkx as nx

affected = nx.descendants(dependency_graph, "OrderService")
# Returns: {"PaymentService", "ShipmentService", "NotificationService", ...}
# These agents need to be notified and potentially migrated
```

---

### 3. Graph-Based Messaging System

#### **Message Bus Architecture**:
- **Pattern**: Pub/Sub with topics
- **Decoupling**: Agents only know topics, not each other
- **Flow**: Publisher → Topic → All Subscribers (in separate threads)

#### **Topic Routing**:
```
Agent A                    Message Bus                    Agent B, C, D
   |                            |                              |
   | publish("/order/created")  |                              |
   |--------------------------->|                              |
   |                            |-----> route to subscribers   |
   |                            |----------------------------->| (Agent B)
   |                            |----------------------------->| (Agent C)
   |                            |----------------------------->| (Agent D)
```

#### **Event Flow Graph** (separate from dependency graph):
- **Nodes**: Agents
- **Edges**: Topic subscriptions (labeled with topic name)
- **Purpose**: Visualize message flow, trace event paths
- **Example**:
  ```
  OrderService --[/order/created]--> PaymentService
  PaymentService --[/payment/completed]--> ShipmentService
  PaymentService --[/payment/failed]--> NotificationService
  ```

#### **Coherence Tracking** (Tranche 4 feature):
Uses NetworkX to find all paths between agents and check schema consistency:
```python
# Find all paths from OrderService to ShipmentService
paths = nx.all_simple_paths(event_graph, "OrderService", "ShipmentService")
# Check each path for schema version consistency
for path in paths:
    check_schema_coherence_along_path(path)
```

---

### 4. Command Sequencing & Workflows

#### **Workflow 1: New Project from Scratch**
```
User Intent: "Create an order processing system"

Claude's Steps:
1. graphbus_init(project_name="order-system", template="microservices")
   → Creates project structure with 3 agents

2. graphbus_build(agents_dir="order-system/agents")
   → Builds artifacts in order-system/.graphbus/
   → NetworkX validates no circular dependencies
   → Creates dependency graph

3. graphbus_inspect(artifacts_dir="order-system/.graphbus", show_graph=true)
   → Shows DAG: OrderService → PaymentService → ShipmentService
   → Shows topics: /order/created, /payment/completed, /shipment/created

4. graphbus_run(artifacts_dir="order-system/.graphbus")
   → Starts runtime in topological order (ShipmentService, PaymentService, OrderService)
   → Returns session_id

5. graphbus_publish(session_id, topic="/order/created", payload={"order_id": "123"})
   → Triggers event flow through the DAG
   → OrderService → PaymentService → ShipmentService

6. graphbus_stats(session_id)
   → Shows 3 events processed, all agents healthy
```

#### **Workflow 2: Add Agent to Existing Project**
```
User Intent: "Add a notification service that sends emails when orders complete"

Claude's Steps:
1. graphbus_generate(
     name="NotificationService",
     subscribes=["/order/completed"],
     publishes=["/notification/sent"],
     output_dir="order-system/agents"
   )
   → Creates agents/notification_service.py
   → Creates tests/test_notification_service.py

2. graphbus_validate(agents_dir="order-system/agents")
   → Checks new agent for issues
   → Validates no circular dependencies with new agent

3. graphbus_build(agents_dir="order-system/agents")
   → Re-builds with new agent
   → Updates dependency graph to include NotificationService
   → Updates topic subscriptions

4. graphbus_inspect(artifacts_dir=".graphbus", show_graph=true)
   → Shows updated DAG with NotificationService
   → Shows new edge: ShipmentService → NotificationService

5. If runtime was running, suggest restart or hot reload
```

#### **Workflow 3: Debugging "Agent Not Receiving Events"**
```
User: "My PaymentService isn't receiving order created events"

Claude's Diagnostic Steps:
1. graphbus_inspect(artifacts_dir=".graphbus", show_subscriptions=true)
   → Check what PaymentService subscribes to
   → Check what OrderService publishes

2. Analyze output:
   - OrderService publishes to: "/orders/created" (plural!)
   - PaymentService subscribes to: "/order/created" (singular!)
   → Found the issue: topic mismatch

3. graphbus_contract(subcommand="list", agent="OrderService")
   → Check contract specification
   → Contract says: "/order/created" (singular)

4. Suggest fix: Update OrderService to publish to "/order/created"

5. After user fixes:
   graphbus_build(agents_dir="agents")
   → Rebuild with corrected topic

6. graphbus_run(artifacts_dir=".graphbus")
   → Test the fix

7. graphbus_publish(session_id, topic="/order/created", payload={...})
   → Verify PaymentService receives it
```

#### **Workflow 4: Deploy to Production**
```
User: "Deploy my order system to Kubernetes"

Claude's Steps:
1. graphbus_docker(subcommand="generate", artifacts_dir=".graphbus")
   → Creates Dockerfile for containerizing agents

2. graphbus_docker(subcommand="build", artifacts_dir=".graphbus", image_name="order-system")
   → Builds Docker image

3. graphbus_k8s(subcommand="generate", artifacts_dir=".graphbus", replicas=3)
   → Creates Kubernetes manifests
   → Deployment.yaml (with topological order init containers)
   → Service.yaml
   → ConfigMap.yaml
   → HorizontalPodAutoscaler.yaml

4. graphbus_k8s(subcommand="apply", artifacts_dir=".graphbus")
   → Deploys to cluster
   → Agents start in correct dependency order (from DAG)

5. graphbus_k8s(subcommand="status")
   → Checks deployment health
```

---

### 5. When to Use Each Command

#### **Project Initialization Commands**
- `graphbus_init`: Starting brand new project, want template
- `graphbus_generate`: Adding single agent to existing project
- `graphbus_load_example`: Want working example to learn from
- `graphbus_quickstart`: Interactive wizard for beginners

**Decision Tree**:
```
User wants to create project?
├─ New project from scratch?
│  ├─ Template available? → graphbus_init
│  └─ Custom from scratch → graphbus_generate (multiple times)
├─ Load working example? → graphbus_load_example
└─ Add to existing project? → graphbus_generate
```

#### **Build Phase Commands**
- `graphbus_validate`: Pre-build check, optional but recommended
- `graphbus_build`: Required before running, validates and creates artifacts
- `graphbus_inspect`: Post-build review, understand structure

**Decision Tree**:
```
User has agent code?
├─ First time / unsure if valid? → graphbus_validate → graphbus_build
├─ Code changed → graphbus_build (re-build required)
└─ Want to see structure → graphbus_inspect (after build)
```

#### **Runtime Phase Commands**
- `graphbus_run`: Start the system (creates session)
- `graphbus_call`: Direct method invocation (RPC style)
- `graphbus_publish`: Event-driven trigger (pub/sub style)
- `graphbus_stats`: Monitor running system

**Decision Tree**:
```
User wants to execute?
├─ Start system → graphbus_run (returns session_id)
├─ Test specific method → graphbus_call(session_id, agent, method)
├─ Trigger event flow → graphbus_publish(session_id, topic, payload)
└─ Check health/status → graphbus_stats(session_id)
```

#### **Development Commands**
- `graphbus_doctor`: Diagnose issues, health check
- `graphbus_profile`: Performance analysis
- `graphbus_dashboard`: Visual monitoring

**Decision Tree**:
```
User has problem?
├─ "Not working" / errors → graphbus_doctor
├─ "Slow" / performance → graphbus_profile
└─ Want visual overview → graphbus_dashboard
```

#### **Deployment Commands**
- `graphbus_docker`: Containerization
- `graphbus_k8s`: Kubernetes deployment
- `graphbus_ci`: CI/CD pipeline generation

**Decision Tree**:
```
User wants to deploy?
├─ To Docker → graphbus_docker
├─ To Kubernetes → graphbus_k8s
└─ Setup CI/CD → graphbus_ci
```

---

### 6. NetworkX Integration Points

GraphBus uses NetworkX throughout the system:

#### **Build Phase**:
1. **Dependency Resolution** (`graphbus_build`):
   ```python
   # Build agent dependency graph
   G = nx.DiGraph()
   for agent in agents:
       for dep in agent.dependencies:
           G.add_edge(agent.name, dep)

   # Check for cycles (invalid!)
   if not nx.is_directed_acyclic_graph(G):
       raise BuildError("Circular dependency detected")

   # Get activation order
   activation_order = list(nx.topological_sort(G))
   ```

2. **Topic Graph** (`graphbus_build`):
   ```python
   # Build event flow graph
   event_graph = nx.DiGraph()
   for agent in agents:
       for topic in agent.publishes:
           for subscriber in get_subscribers(topic):
               event_graph.add_edge(
                   agent.name,
                   subscriber,
                   topic=topic
               )
   ```

#### **Runtime Phase**:
1. **Agent Initialization** (`graphbus_run`):
   ```python
   # Load dependency graph from artifacts
   G = nx.node_link_graph(artifacts['graph.json'])

   # Initialize in topological order
   for agent_name in nx.topological_sort(G):
       initialize_agent(agent_name)
   ```

2. **Event Routing**:
   ```python
   # Find all subscribers for topic
   subscribers = [
       node for node in event_graph.nodes()
       if event_graph.has_edge(publisher, node)
       and event_graph[publisher][node]['topic'] == topic
   ]
   ```

#### **Contract Management** (Tranche 4):
1. **Impact Analysis** (`graphbus_contract impact`):
   ```python
   # Find all downstream agents affected by contract change
   affected = nx.descendants(G, "OrderService")

   # For each path to affected agents, check compatibility
   for agent in affected:
       paths = nx.all_simple_paths(G, "OrderService", agent)
       for path in paths:
           check_contract_compatibility_along_path(path)
   ```

2. **Migration Planning** (`graphbus_migrate plan`):
   ```python
   # Build migration dependency graph
   migration_graph = nx.DiGraph()
   for migration in migrations:
       for dep in migration.depends_on:
           migration_graph.add_edge(migration.id, dep)

   # Topological sort gives correct migration order
   migration_order = list(nx.topological_sort(migration_graph))
   ```

#### **Coherence Tracking** (Tranche 4):
1. **Path Analysis** (`graphbus_coherence check`):
   ```python
   # Find all paths in event flow graph
   for source in event_graph.nodes():
       for target in event_graph.nodes():
           if source != target:
               try:
                   paths = nx.all_simple_paths(event_graph, source, target)
                   for path in paths:
                       # Check schema consistency along path
                       check_coherence_along_path(path)
               except nx.NetworkXNoPath:
                   continue
   ```

2. **Drift Detection** (`graphbus_coherence drift`):
   ```python
   # Compare event graph at different times
   G_t1 = load_event_graph(time=t1)
   G_t2 = load_event_graph(time=t2)

   # Find schema version changes
   for edge in G_t2.edges():
       if G_t1.has_edge(*edge):
           old_version = G_t1.edges[edge]['schema_version']
           new_version = G_t2.edges[edge]['schema_version']
           if old_version != new_version:
               record_drift(edge, old_version, new_version)
   ```

---

### 7. Error Recovery Strategies

When things go wrong, Claude should follow these patterns:

#### **Build Fails**:
```
1. graphbus_validate → find specific issues
2. Show user error with line numbers
3. Suggest fix
4. After user fixes → graphbus_build
```

#### **Runtime Fails to Start**:
```
1. graphbus_doctor → check installation, dependencies
2. graphbus_inspect → verify artifacts are valid
3. Check if build is recent (artifacts vs source code timestamps)
4. If stale → graphbus_build
5. Try graphbus_run with verbose=true
```

#### **Agent Not Responding**:
```
1. graphbus_stats(session_id) → check if agent is healthy
2. graphbus_inspect(show_subscriptions=true) → verify topic configuration
3. Check event flow graph for disconnected agents
4. Suggest adding missing subscriptions or fixing topic names
```

#### **Performance Issues**:
```
1. graphbus_profile → identify bottlenecks
2. Show user slowest methods
3. Check event flow graph for excessive fan-out
4. Suggest optimization strategies
```

---

### 8. Key Mental Models for Claude

#### **Mental Model 1: Build = Compile, Run = Execute**
```
Write Code → Build (validate + generate artifacts) → Run (execute)
          ↑                                            ↓
          └─────────── Modify Code ← Observe Results ─┘
```

#### **Mental Model 2: DAG Determines Order**
```
All agent operations respect the dependency DAG:
- Initialization order (topological sort)
- Shutdown order (reverse topological)
- Migration order (dependent migrations first)
- Impact analysis (descendants of changed node)
```

#### **Mental Model 3: Topics Decouple Agents**
```
Agent A knows: "I publish /order/created"
Agent B knows: "I subscribe to /order/created"
Neither knows about each other → loose coupling
Message Bus routes messages using topic graph
```

#### **Mental Model 4: Two Graphs, Different Purposes**
```
Dependency Graph (DAG):
- Nodes: Agents
- Edges: Dependencies
- Purpose: Initialization order, validation
- Built from: Code analysis

Event Flow Graph (possibly cyclic):
- Nodes: Agents
- Edges: Topic subscriptions
- Purpose: Message routing, visualization
- Built from: @subscribes and @publishes decorators
```

---

### 9. Advanced Features Context

#### **Hot Reload** (Tranche 4):
```
User changes code → graphbus_build → hot reload in running system
- Uses importlib to reload agent modules
- Preserves agent state if requested
- Updates message bus subscriptions
- Does NOT require full restart
```

#### **Contract Management** (Tranche 4):
```
Agent API changes → graphbus_contract diff → impact analysis (NetworkX descendants)
- Identifies breaking vs non-breaking changes
- Uses DAG to find affected agents
- Generates migration recommendations
```

#### **Schema Migrations** (Tranche 4):
```
Schema version change → graphbus_migrate create → topological migration order
- Builds migration dependency graph
- Uses nx.topological_sort for correct order
- Validates no circular migration dependencies
```

---

### 10. Command Cheat Sheet by User Intent

| User Says | Command Sequence |
|-----------|-----------------|
| "Create new project" | `init` → `build` → `inspect` → `run` |
| "Add agent" | `generate` → `build` → `run` |
| "Try example" | `load_example` → `build` → `run` |
| "Show structure" | `inspect` (after build) |
| "Is code valid?" | `validate` → `build` |
| "Run system" | `build` (if needed) → `run` |
| "Test method" | `run` → `call` |
| "Trigger flow" | `run` → `publish` |
| "Check health" | `stats` (runtime) or `doctor` (installation) |
| "Deploy" | `docker generate` → `docker build` → `k8s generate` → `k8s apply` |
| "Not working" | `doctor` → diagnose → fix → `build` |
| "Performance issues" | `profile` → identify bottlenecks → optimize |

---

## Summary for Claude

When using GraphBus MCP tools:

1. **Always respect Build/Run separation**: Build first, then run
2. **Understand the DAG**: Agent order matters, cycles are errors
3. **Topics decouple agents**: Pub/sub through message bus
4. **NetworkX is everywhere**: Dependency resolution, activation order, impact analysis
5. **Follow workflow patterns**: init/load/generate → validate → build → inspect → run → interact
6. **Use appropriate commands**: Match command to user's current phase (build vs runtime)
7. **Leverage the graphs**: Dependency DAG and Event Flow Graph guide system behavior

With this context, Claude can intelligently sequence commands, understand errors, and guide users effectively through GraphBus development.

# GraphBus Runtime Mode

Runtime Mode is the execution phase of GraphBus where pre-built agent artifacts are loaded and executed without active LLM intervention. It provides a lightweight, deterministic execution environment for agent systems.

## Overview

Runtime Mode operates on artifacts generated during Build Mode:
- **Build Mode**: Analyzes code, extracts agents, builds dependency graph, generates artifacts
- **Runtime Mode**: Loads artifacts, instantiates nodes, routes messages, executes handlers

## Core Components

### 1. ArtifactLoader

**Purpose**: Loads and deserializes build artifacts from `.graphbus/` directory.

**Key Files**:
- `graphbus_core/runtime/loader.py`

**Artifacts Loaded**:
- `graph.json` - Agent dependency graph (NetworkX format)
- `agents.json` - Agent definitions with source code
- `topics.json` - Topic definitions and subscriptions
- `build_summary.json` - Build metadata

**Usage**:
```python
from graphbus_core.runtime.loader import ArtifactLoader

loader = ArtifactLoader('.graphbus')
graph, agents, topics, subscriptions = loader.load_all()

# Or load individually
graph = loader.load_graph()
agents = loader.load_agents()
agent = loader.get_agent_by_name('HelloService')
```

**Key Methods**:
- `load_graph()` - Load NetworkX graph structure
- `load_agents()` - Load all agent definitions
- `load_topics()` - Load topic definitions
- `load_subscriptions()` - Load subscription mappings
- `get_agent_by_name(name)` - Get specific agent definition
- `validate_artifacts()` - Validate artifact integrity

### 2. MessageBus

**Purpose**: Synchronous publish-subscribe message routing system.

**Key Files**:
- `graphbus_core/runtime/message_bus.py`

**Features**:
- Topic-based routing (e.g., `/Hello/MessageGenerated`)
- Multiple subscribers per topic
- Message history tracking
- Statistics and monitoring
- Error handling for failed handlers

**Usage**:
```python
from graphbus_core.runtime.message_bus import MessageBus

bus = MessageBus()

# Subscribe to topic
def handler(event):
    print(f"Received: {event.payload}")

bus.subscribe('/test/topic', handler, 'MySubscriber')

# Publish message
event = bus.publish('/test/topic', {'data': 'test'}, source='producer')

# Get statistics
stats = bus.get_stats()
print(f"Published: {stats['messages_published']}")
```

**Key Methods**:
- `subscribe(topic, handler, subscriber_name)` - Register handler for topic
- `unsubscribe(topic, handler)` - Remove handler from topic
- `publish(topic, payload, source)` - Publish event to topic
- `get_subscribers(topic)` - Get all subscribers for topic
- `get_stats()` - Get message bus statistics
- `get_message_history()` - Get recent message history

### 3. EventRouter

**Purpose**: Routes events to node handler methods based on subscriptions.

**Key Files**:
- `graphbus_core/runtime/event_router.py`

**Features**:
- Smart handler signature detection
- Automatic parameter matching (no params, payload dict, or Event object)
- Error handling for failed handlers
- Multiple handlers per topic

**Handler Signature Detection**:
```python
# No parameters - handler called with no arguments
def on_event(self):
    pass

# One parameter - receives payload dict
def on_event(self, payload):
    data = payload.get('data')

# Multiple parameters - receives Event object
def on_event(self, event: Event):
    topic = event.topic
    payload = event.payload
```

**Usage**:
```python
from graphbus_core.runtime.event_router import EventRouter

router = EventRouter(bus)

# Register handler
router.register_handler('/test/topic', node, 'on_test_event')

# Unregister all handlers for a node
router.unregister_node(node)

# Get handlers for topic
handlers = router.get_handlers_for_topic('/test/topic')
```

**Key Methods**:
- `register_handler(topic, node, handler_name)` - Register node handler for topic
- `unregister_node(node)` - Unregister all handlers for node
- `route_event_to_node(node, handler_name, event)` - Route event to specific handler
- `dispatch_event(event)` - Dispatch event to all registered handlers
- `get_handlers_for_topic(topic)` - Get all handlers for topic

### 4. RuntimeExecutor

**Purpose**: Main orchestration component that manages the runtime lifecycle.

**Key Files**:
- `graphbus_core/runtime/executor.py`

**Features**:
- Artifact loading and validation
- Dynamic node instantiation from source code
- Message bus setup with subscriptions
- Direct method invocation
- Event publishing
- Runtime statistics and monitoring

**Usage**:
```python
from graphbus_core.runtime.executor import RuntimeExecutor, run_runtime

# Full control
executor = RuntimeExecutor('.graphbus', enable_message_bus=True)
executor.start()

# Direct method call
result = executor.call_method('HelloService', 'generate_message')

# Publish event
executor.publish('/Hello/MessageGenerated', {'message': result})

# Get statistics
stats = executor.get_stats()

executor.stop()

# Convenience function
executor = run_runtime('.graphbus')
```

**Key Methods**:
- `start()` - Start runtime (load artifacts, initialize nodes, setup message bus)
- `stop()` - Stop runtime
- `call_method(node_name, method_name, **kwargs)` - Call node method directly
- `publish(topic, payload, source)` - Publish event through message bus
- `get_node(name)` - Get node instance by name
- `get_all_nodes()` - Get all node instances
- `get_stats()` - Get runtime statistics

## Data Models

### Serialization Models

**Purpose**: Type-safe deserialization of JSON artifacts (avoiding scattered `.get()` calls).

**Key Files**:
- `graphbus_core/model/serialization.py`

**Models**:
```python
@dataclass
class GraphNodeData:
    name: str
    type: str = "agent"
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GraphEdgeData:
    from_node: str
    to_node: str
    type: str = "dependency"
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GraphData:
    nodes: List[GraphNodeData]
    edges: List[GraphEdgeData]

    @classmethod
    def from_dict(cls, graph_dict: Dict[str, Any]) -> "GraphData":
        # Handles both 'name'/'id' and 'from'/'to' vs 'source'/'target' formats
        ...

@dataclass
class TopicsData:
    topics: List[TopicData]
    subscriptions: List[Dict[str, str]]
```

**Design Principle**: `.get()` calls are isolated to factory methods (`from_dict()`), while the rest of the code uses proper typed attributes.

## Runtime Workflow

### Standard Workflow

```python
# 1. Initialize executor
executor = RuntimeExecutor('.graphbus')

# 2. Start runtime (loads artifacts, initializes nodes, sets up message bus)
executor.start()

# 3. Interact with nodes
result = executor.call_method('ServiceName', 'method_name', arg1='value')

# 4. Publish events
executor.publish('/topic/name', {'data': 'value'}, source='source_name')

# 5. Query state
node = executor.get_node('ServiceName')
stats = executor.get_stats()

# 6. Stop runtime
executor.stop()
```

### Message Flow

```
1. Producer publishes event:
   bus.publish('/data/produced', {'value': 42}, source='Producer')

2. MessageBus creates Event object:
   Event(event_id=..., topic='/data/produced', src='Producer', payload={'value': 42})

3. MessageBus dispatches to EventRouter:
   router.dispatch_event(event)

4. EventRouter finds registered handlers:
   handlers = _node_handlers['/data/produced']  # [(ConsumerNode, 'on_data_produced')]

5. EventRouter routes to each handler:
   router.route_event_to_node(ConsumerNode, 'on_data_produced', event)

6. EventRouter detects handler signature and calls:
   ConsumerNode.on_data_produced({'value': 42})  # Passes payload dict

7. Handler processes and publishes next event:
   bus.publish('/data/consumed', {'value': 42, 'processed': True}, source='Consumer')

8. Process repeats for next stage...
```

## Runtime Configuration

### RuntimeExecutor Options

```python
executor = RuntimeExecutor(
    artifacts_dir='.graphbus',      # Path to artifacts directory
    enable_message_bus=True         # Enable/disable message bus
)
```

### Node Instantiation

Nodes are dynamically instantiated from source code in `agents.json`:

1. Extract source code from agent definition
2. Execute source code to define class
3. Instantiate class: `node = NodeClass(bus=None, memory=None)`
4. Set runtime mode: `node.set_mode("runtime")`
5. Set node name: `node.name = agent_def.name`
6. Register with executor: `self.nodes[name] = node`

### Subscription Registration

Subscriptions from `topics.json` are automatically registered:

```python
for subscription in subscriptions:
    agent_name = subscription['agent']
    topic = subscription['topic']
    handler = subscription['handler']

    node = nodes[agent_name]
    router.register_handler(topic, node, handler)
```

## Statistics and Monitoring

### Message Bus Statistics

```python
stats = executor.get_stats()

{
    'is_running': True,
    'nodes_count': 3,
    'message_bus': {
        'messages_published': 10,
        'messages_delivered': 20,
        'errors': 0,
        'total_subscriptions': 5,
        'topics_with_subscribers': 3
    }
}
```

### Message History

```python
history = executor.bus.get_message_history()

# Returns list of Event objects (newest first)
for event in history:
    print(f"{event.topic}: {event.payload} from {event.src}")
```

## Runtime vs Build Mode

| Aspect | Build Mode | Runtime Mode |
|--------|-----------|--------------|
| **Purpose** | Extract agents, build graph | Execute pre-built agents |
| **LLM Usage** | Active (agents refactor code) | None (static execution) |
| **Input** | Python source files | Build artifacts (JSON) |
| **Output** | Artifacts in `.graphbus/` | Runtime execution results |
| **Agents** | Active GraphBusNode instances | Instantiated from source code |
| **Determinism** | Non-deterministic (LLM) | Deterministic (static code) |
| **Speed** | Slow (LLM calls) | Fast (direct execution) |
| **Use Case** | Initial setup, refactoring | Production execution |

## Error Handling

### Handler Errors

Errors in event handlers are caught and tracked but don't stop the system:

```python
try:
    handler(event.payload)
except Exception as e:
    print(f"[EventRouter] Error executing {node.name}.{handler_name}(): {e}")
    # Error tracked in stats but system continues
```

### Artifact Loading Errors

Missing or malformed artifacts raise exceptions during initialization:

```python
try:
    executor = RuntimeExecutor('.graphbus')
    executor.start()
except FileNotFoundError as e:
    print(f"Missing artifacts: {e}")
except json.JSONDecodeError as e:
    print(f"Malformed artifact: {e}")
```

## Testing Runtime Mode

### Test Structure

```
tests/runtime/
├── unit/              # Component tests
│   ├── test_loader.py
│   ├── test_message_bus.py
│   ├── test_event_router.py
│   └── test_executor.py
├── functional/        # Workflow tests
│   ├── test_artifact_loading.py
│   └── test_message_flow.py
└── integration/       # End-to-end tests
    ├── test_hello_world_runtime.py
    └── test_end_to_end.py
```

### Running Runtime Tests

```bash
# All runtime tests
pytest tests/runtime/

# Unit tests only
pytest tests/runtime/unit/

# Integration tests only
pytest tests/runtime/integration/
```

## Example: Hello World Runtime

```python
from graphbus_core.runtime.executor import run_runtime

def main():
    # Start runtime
    executor = run_runtime('.graphbus')

    # Test 1: Direct method call
    message = executor.call_method('HelloService', 'generate_message')
    print(f"Generated: {message}")

    # Test 2: Publish event (triggers LoggerService)
    executor.publish(
        '/Hello/MessageGenerated',
        {'message': message},
        source='HelloService'
    )

    # Test 3: Check statistics
    stats = executor.get_stats()
    print(f"Nodes: {stats['nodes_count']}")
    print(f"Messages published: {stats['message_bus']['messages_published']}")
    print(f"Messages delivered: {stats['message_bus']['messages_delivered']}")

    # Stop runtime
    executor.stop()

if __name__ == '__main__':
    main()
```

## Best Practices

### Node Design for Runtime

1. **Stateless Handlers**: Keep handlers simple and stateless when possible
2. **Error Handling**: Handle errors gracefully in handlers
3. **Payload Validation**: Validate payload data in handlers
4. **Circular Prevention**: Limit iterations in circular event flows

### Message Bus Usage

1. **Topic Naming**: Use hierarchical topics (e.g., `/Service/Event`)
2. **Payload Structure**: Keep payloads simple dicts
3. **Source Attribution**: Always specify source when publishing
4. **Subscription Cleanup**: Unsubscribe when nodes are done

### Performance

1. **Message Bus Overhead**: Minimal overhead for pub/sub routing
2. **Node Instantiation**: One-time cost during startup
3. **Event Routing**: Fast signature detection and dispatch
4. **Memory Usage**: Message history has configurable size limit

## Future Enhancements

Potential future additions to Runtime Mode:

1. **Async Support**: Async/await for event handlers
2. **Persistent Storage**: Save/restore runtime state
3. **Remote Execution**: Distributed nodes across processes/machines
4. **Hot Reload**: Update nodes without full restart
5. **Metrics Export**: Prometheus/OpenTelemetry integration
6. **Event Replay**: Replay message history for debugging
7. **Handler Middleware**: Interceptors for cross-cutting concerns
8. **Type Validation**: Runtime validation of payload schemas

## See Also

- [Design Document](design.md) - Overall architecture
- [Progress Document](progress.md) - Implementation status
- [Test README](../../tests/README.md) - Testing documentation
- [Hello World Example](../../examples/hello_graphbus/) - Complete example

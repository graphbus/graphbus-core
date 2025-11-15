# GraphBus MCP Quick Start Guide

## Setup Complete ✅

GraphBus is now installed and ready to use with Claude Code!

```bash
# Verify installation
graphbus --version  # Should show: graphbus, version 0.1.0

# The hello world agent has been built
ls .graphbus/       # Should show: agents.json, graph.json, etc.
```

## Understanding How User Intent Flows

You asked: **"How does GraphBus actually utilize user intent? How does intent propagate through the graph?"**

Great question! Let me explain the two main ways intent flows in GraphBus:

### 1. Direct Method Invocation (Synchronous Intent)

**User Intent → Runtime → Specific Agent Method**

```
User: "Say hello to Alice"
  ↓
Claude Code (via MCP)
  ↓
graphbus_call tool
  ↓
Runtime.call_agent("HelloAgent", "say_hello", {"name": "Alice"})
  ↓
HelloAgent.say_hello(name="Alice")
  ↓
Returns: {"message": "Hello, Alice!", "greeting_number": 1, ...}
```

**Example**:
```bash
# Start runtime
graphbus run .graphbus --interactive

# In the REPL:
>>> call HelloAgent.say_hello(name="Alice")
{"message": "Hello, Alice!", "greeting_number": 1, "greeted": "Alice"}
```

### 2. Event-Driven Propagation (Asynchronous Intent)

**User Intent → Event → Message Bus → All Subscribed Agents**

Let's look at a more complex example with event propagation:

```python
# Order Processing System
class OrderService(GraphBusNode):
    @schema_method(...)
    def create_order(self, order_data: dict):
        # User intent: "Create an order"
        order = self.process_order(order_data)

        # Publish event - intent propagates!
        self.publish("/order/created", order)

        return order

class PaymentService(GraphBusNode):
    @subscribe("/order/created")  # Listens for order events
    def handle_new_order(self, event_data: dict):
        # Receives intent automatically!
        order_id = event_data['order_id']
        self.process_payment(order_id)

        # Publish next intent
        self.publish("/payment/completed", {"order_id": order_id})

class ShippingService(GraphBusNode):
    @subscribe("/payment/completed")  # Listens for payment events
    def handle_payment(self, event_data: dict):
        # Receives cascading intent!
        order_id = event_data['order_id']
        self.ship_order(order_id)
```

**Intent Flow**:
```
User: "Create order for customer #123"
  ↓
OrderService.create_order()
  ↓
publishes("/order/created") ← Intent becomes EVENT
  ↓
Message Bus routes event
  ├→ PaymentService.handle_new_order() ← Intent received!
  ├→ NotificationService.send_email()  ← Intent received!
  └→ InventoryService.update_stock()    ← Intent received!
        ↓
PaymentService publishes("/payment/completed") ← New intent!
  ↓
Message Bus routes event
  └→ ShippingService.handle_payment() ← Cascading intent!
```

### 3. User Intent via Claude Code (MCP)

When you use Claude Code, intent flows through the MCP protocol:

```
You: "Build the agents and inspect the graph"
  ↓
Claude Code (LLM understands intent)
  ↓
Calls graphbus_build tool via MCP
  ↓
MCP server (server.py)
  ↓
graphbus_cli.commands.build.build()
  ↓
Build artifacts created
  ↓
Claude Code calls graphbus_inspect tool
  ↓
Shows you the graph structure
  ↓
Claude presents results naturally
```

**The key**: Claude Code translates your natural language intent into the appropriate GraphBus tool calls!

## Practical Examples

### Example 1: Simple Direct Call

```bash
# Start the runtime
graphbus run .graphbus --interactive

# Your intent: "I want to say hello to Bob"
>>> call HelloAgent.say_hello(name="Bob")

# Result:
{"message": "Hello, Bob!", "greeting_number": 1, "greeted": "Bob"}
```

### Example 2: Get Agent Statistics

```bash
# Your intent: "Show me how many greetings have been sent"
>>> call HelloAgent.get_stats()

# Result:
{"total_greetings": 1, "agent_name": "HelloAgent", "status": "active"}
```

### Example 3: Via Claude Code (Natural Language)

**You**: "Build the agents in examples/hello_world_mcp/agents/ and show me the graph"

**Claude Code** (behind the scenes):
1. Calls `graphbus_build(agents_dir="examples/hello_world_mcp/agents/")`
2. Waits for success
3. Calls `graphbus_inspect(artifacts_dir=".graphbus", show_graph=True)`
4. Presents results to you naturally

**Claude**: "I've built your agent system. You have 1 agent (HelloAgent) with 2 methods..."

### Example 4: Event-Driven Intent Propagation

To see event propagation, let's look at a multi-agent example:

```python
# examples/order_system/agents/

class OrderService(GraphBusNode):
    @schema_method(...)
    def create_order(self, items: list):
        order = {"id": 123, "items": items, "total": 99.99}
        self.publish("/order/created", order)  # ← Intent becomes event
        return order

class PaymentService(GraphBusNode):
    @subscribe("/order/created")  # ← Receives intent automatically
    def process_order_payment(self, event_data):
        order_id = event_data["id"]
        # Process payment...
        self.publish("/payment/completed", {"order_id": order_id})

class ShippingService(GraphBusNode):
    @subscribe("/payment/completed")  # ← Receives cascading intent
    def ship_order(self, event_data):
        order_id = event_data["order_id"]
        # Ship the order...
```

**Intent Flow**:
```
User calls: OrderService.create_order(items=["Book", "Pen"])
  ↓
Event published: /order/created
  ↓ ↓ ↓
Three agents receive the event simultaneously:
  - PaymentService
  - InventoryService
  - NotificationService
    ↓
Each agent processes the intent independently
  ↓
PaymentService publishes: /payment/completed
  ↓
ShippingService receives and ships
```

## Key Concepts

### 1. **Build Mode vs Runtime Mode**

- **Build Mode**: Analyzes your agents and creates execution plan
  - Intent: "Understand agent structure"
  - Command: `graphbus build agents/`

- **Runtime Mode**: Executes agents and routes messages
  - Intent: "Run the system and handle events"
  - Command: `graphbus run .graphbus`

### 2. **Intent Propagation Mechanisms**

| Mechanism | When to Use | Example |
|-----------|-------------|---------|
| **Direct Call** | Synchronous, specific action | `call OrderService.create_order()` |
| **Event Publish** | Async, notify multiple agents | `self.publish("/order/created", data)` |
| **Subscribe** | React to events from any agent | `@subscribe("/order/created")` |

### 3. **The Message Bus (Event Router)**

The message bus is how intent propagates asynchronously:

```
Agent A: self.publish("/topic", data)
  ↓
Message Bus
  ├→ Agent B (subscribed to /topic)
  ├→ Agent C (subscribed to /topic)
  └→ Agent D (subscribed to /topic)
```

All subscribers receive the event **concurrently** - the intent fans out!

## Using with Claude Code (MCP)

Once you configure the MCP server (see README.md), you can use natural language:

**Natural Language → Tool Calls → Intent Execution**

### Example Conversations:

**You**: "Build the agents and show me what was created"

**Claude**: *Uses graphbus_build then graphbus_inspect*
"I've built your agent system. You have:
- 1 agent (HelloAgent)
- 2 methods (say_hello, get_stats)
- 0 dependencies"

---

**You**: "Run the system and have HelloAgent say hello to everyone on the team"

**Claude**: *Uses graphbus_run then multiple graphbus_call*
"Started the runtime. HelloAgent said:
- Hello, Alice! (greeting #1)
- Hello, Bob! (greeting #2)
- Hello, Carol! (greeting #3)"

---

**You**: "Enable agent orchestration so the agents can improve themselves"

**Claude**: *Uses graphbus_build with enable_agents=true*
"I've enabled LLM agent orchestration. The agents will now analyze their code and propose improvements through multi-round negotiation. Would you like me to show you the negotiation history?"

## Next Steps

1. **Try it locally**:
   ```bash
   cd examples/hello_world_mcp
   graphbus build agents/
   graphbus inspect .graphbus --graph --agents
   graphbus run .graphbus --interactive
   ```

2. **Configure MCP** (see README.md):
   - Add GraphBus to Claude Code config
   - Restart Claude Code
   - Start chatting naturally!

3. **Build complex systems**:
   - Look at examples/order_system for event-driven patterns
   - See TRANCHE_4.5.md for agent orchestration
   - Use `graphbus init my-project` to start fresh

## Summary: How Intent Propagates

1. **User Intent** → You express what you want (via CLI, Claude Code, or API)

2. **GraphBus Routes It**:
   - **Direct**: Runtime calls specific agent method
   - **Event**: Message bus routes to all subscribers
   - **MCP**: Claude translates natural language to tool calls

3. **Agents Execute**:
   - Receive intent as method call or event
   - Process and potentially publish new events
   - Intent cascades through the system

4. **Results Flow Back**:
   - Return values for direct calls
   - Events trigger cascading agent actions
   - Claude presents results naturally

**The magic**: GraphBus handles all the routing, dependency resolution, and message delivery. You just express intent, and the framework makes it happen! 🚀

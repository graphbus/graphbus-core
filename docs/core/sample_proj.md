# GraphBus Core – Hello World Example (Build + Runtime Modes)

## 0. Goal & Scope

**Goal:**
Design a **graphbus-core** Python library + macOS Swift app that demonstrates the Build/Runtime distinction through a simple Hello World example.

**Key Distinction:**
* **Build Mode**: Agents are active, can negotiate and refactor code
* **Runtime Mode**: Agents are dormant, code executes statically

This document shows how a Hello World project flows through both modes.

---

## 1. Hello World – Two-Phase Flow

### 1.1 Phase 1: Build Mode (Agents Active)

On the macOS app:

1. Open GraphBus, click **"New Project" → Hello World**.
2. App scaffolds:
   * Python project `hello_graphbus/`
   * Three starter classes with basic implementations:
     * `HelloService`
     * `PrinterService`
     * `LoggerService`
3. User clicks **"Build"** (or **"Refactor"**).
4. Build Mode activates:
   * **LLM agents** are instantiated (one per class)
   * Agents read their source code
   * Agents analyze dependencies and schemas
   * **Agents negotiate** potential improvements:
     * `HelloService` agent: "Should we parameterize the greeting?"
     * `PrinterService` agent: "I can add colored output support"
     * `LoggerService` agent: "Let me add timestamps"
   * Agents reach consensus on changes
   * **Source code files are modified** based on agreements
   * Build artifacts are emitted
5. User sees in the Mac app:
   * Agent conversation timeline
   * Proposed code changes
   * Final code diffs
   * "Build Complete - 3 files modified"

### 1.2 Phase 2: Runtime Mode (Agents Dormant)

6. User clicks **"Run"**.
7. Runtime Mode executes:
   * Loads the **refactored Python code** (agents dormant)
   * Simply executes the code:
     * calls `HelloService.generate_message()`
     * routes result to PrinterService and LoggerService
   * No LLM reasoning, no negotiations, just code execution
8. Output:
   * Console prints `Hello, World!` (with colors if agents added that)
   * Log shows `[2025-11-14 10:30:00] Greeting generated: Hello, World!`
9. User sees in the Mac app:
   * Execution trace
   * Standard debugging logs

---

## 2. Hello World Code Example

### 2.1 Initial Code (Before Build Mode)

```python
# hello_graphbus/agents/hello.py
from graphbus_core import GraphBusNode, schema_method

class HelloService(GraphBusNode):
    SYSTEM_PROMPT = """
    You generate greeting messages.
    In Build Mode, you can negotiate with other services to improve
    the greeting format and content.
    """

    @schema_method(
        input_schema={},
        output_schema={"message": str}
    )
    def generate_message(self):
        return {"message": "Hello, World!"}
```

```python
# hello_graphbus/agents/printer.py
from graphbus_core import GraphBusNode, schema_method

class PrinterService(GraphBusNode):
    SYSTEM_PROMPT = """
    You print messages to the console.
    In Build Mode, you can propose adding formatting capabilities
    like colors or styling to improve output readability.
    """

    @schema_method(
        input_schema={"message": str},
        output_schema={}
    )
    def print_message(self, message: str):
        print(message)
        return {}
```

```python
# hello_graphbus/agents/logger.py
from graphbus_core import GraphBusNode, subscribe

class LoggerService(GraphBusNode):
    SYSTEM_PROMPT = """
    You log events when greetings are generated.
    In Build Mode, you can negotiate with other services about
    what information should be logged and in what format.
    """

    @subscribe("/Hello/MessageGenerated")
    def on_message_generated(self, event):
        print(f"[LOG] Greeting generated: {event['message']}")
```

```python
# hello_graphbus/agents/arbiter.py
from graphbus_core import GraphBusNode

class ArbiterService(GraphBusNode):
    """
    Special arbiter agent that resolves conflicts when other agents disagree.
    """

    SYSTEM_PROMPT = """
You are an impartial arbiter agent responsible for resolving conflicts during code negotiations.

Your role:
- Review proposals that have conflicting evaluations
- Consider technical correctness, code quality, and system impact
- Make fair, unbiased decisions based on engineering principles
- Provide clear reasoning for your arbitration decisions

You should:
- Favor changes that improve code quality without breaking functionality
- Reject changes that introduce bugs or reduce maintainability
- Consider the opinions of both accepting and rejecting agents
- Be conservative - when in doubt, reject risky changes
"""

    IS_ARBITER = True  # Mark this as an arbiter agent

    def __init__(self, bus=None, memory=None):
        super().__init__(bus, memory)
```

### 2.2 Build Mode Execution

```bash
# User runs build mode
python -m graphbus_core.build --root hello_graphbus.agents --llm-model claude-sonnet-4
```

**What happens internally:**

1. **Graph construction**: NetworkX builds dependency graph
2. **Topological sort**: Determines activation order: [HelloService, PrinterService, LoggerService, ArbiterService]
3. **Agents activated** in topological order:
   - HelloService (no dependencies)
   - PrinterService (depends on Hello)
   - LoggerService (subscribes to Hello events)
   - ArbiterService (marked with IS_ARBITER=True)
4. **Safety limits loaded**:
   - max_negotiation_rounds=10
   - max_proposals_per_agent=3
   - convergence_threshold=2
   - require_arbiter_on_conflict=True
5. **PrinterService agent** proposes:
   ```python
   Proposal(
       intent="add_color_support",
       code_change={
           "file": "hello_graphbus/agents/printer.py",
           "reason": "Adding color makes output more readable",
           "new_code": """
   def print_message(self, message: str):
       print(f"\\033[92m{message}\\033[0m")  # green text
       return {}
           """
       }
   )
   ```

3. **LoggerService agent** evaluates and accepts, then proposes its own change:
   ```python
   Proposal(
       intent="add_timestamp",
       code_change={
           "file": "hello_graphbus/agents/logger.py",
           "reason": "Timestamps help with debugging",
           "new_code": """
   from datetime import datetime

   def on_message_generated(self, event):
       timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
       print(f"[LOG {timestamp}] Greeting generated: {event['message']}")
           """
       }
   )
   ```

4. **Evaluation Phase**:
   - All agents evaluate both proposals
   - Both proposals get majority accept (no conflicts)
   - No arbiter needed (unanimous/majority consensus)

5. **Commits are made** → source files are modified

6. **Round 2**: No new proposals (agents satisfied)
7. **Round 3**: No new proposals → convergence detected → negotiation stops

### 2.3 Code After Build Mode (Agent-Refactored)

```python
# hello_graphbus/agents/printer.py (MODIFIED BY AGENTS)
from graphbus_core import GraphBusNode, schema_method

class PrinterService(GraphBusNode):
    SYSTEM_PROMPT = """
    You print messages to the console.
    In Build Mode, you can propose adding formatting capabilities
    like colors or styling to improve output readability.
    """

    @schema_method(
        input_schema={"message": str},
        output_schema={}
    )
    def print_message(self, message: str):
        # Added by agent negotiation: colored output
        print(f"\033[92m{message}\033[0m")  # green text
        return {}
```

```python
# hello_graphbus/agents/logger.py (MODIFIED BY AGENTS)
from graphbus_core import GraphBusNode, subscribe
from datetime import datetime

class LoggerService(GraphBusNode):
    SYSTEM_PROMPT = """
    You log events when greetings are generated.
    In Build Mode, you can negotiate with other services about
    what information should be logged and in what format.
    """

    @subscribe("/Hello/MessageGenerated")
    def on_message_generated(self, event):
        # Added by agent negotiation: timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[LOG {timestamp}] Greeting generated: {event['message']}")
```

### 2.4 Runtime Mode Execution

```python
# hello_graphbus/run_hello.py (Runtime entrypoint)
from graphbus_core.runtime import RuntimeEngine, BuildArtifacts

def main():
    # Load artifacts from Build Mode
    artifacts = BuildArtifacts.load(".graphbus/")

    # Runtime engine - NO AGENTS, just code execution
    engine = RuntimeEngine(artifacts)
    engine.load_modules()

    # Import the refactored code (agents are dormant)
    from hello_graphbus.agents.hello import HelloService
    from hello_graphbus.agents.printer import PrinterService

    # Execute the refactored code
    hello = HelloService()
    result = hello.generate_message()

    printer = PrinterService()
    printer.print_message(result["message"])

    # Pub/sub routing (static, no agent reasoning)
    # LoggerService's subscription is triggered automatically

if __name__ == "__main__":
    main()
```

**Output:**
```
Hello, World!  # in green color (agent added this)
[LOG 2025-11-14 10:30:00] Greeting generated: Hello, World!  # agent added timestamp
```

---

## 3. Key Distinctions Illustrated

### 3.1 Build Mode Characteristics

* **Agents are active** - each class has an LLM-powered agent
* **Code is mutable** - agents can propose and commit changes
* **Negotiation happens** - agents communicate via GraphBus
* **Graph is used for orchestration** - topological sort determines agent activation
* **Output**: Modified source code + build artifacts

### 3.2 Runtime Mode Characteristics

* **Agents are dormant** - no LLM reasoning
* **Code is immutable** - execution only, no modifications
* **No negotiation** - pure static execution
* **Graph is documentation** - shows structure but doesn't drive execution
* **Output**: Program execution results

---

## 4. Advanced Example: Arbiter Resolving Conflict

### 4.1 Scenario: Disagreement on Error Handling

Imagine a more complex scenario where agents disagree:

**Proposal from PaymentService:**
```python
Proposal(
    intent="add_retry_logic",
    code_change={
        "file": "payment.py",
        "target": "process_payment",
        "reason": "Add retry logic for transient failures",
        "old_code": """
def process_payment(self, amount: float):
    return self.gateway.charge(amount)
        """,
        "new_code": """
def process_payment(self, amount: float):
    for attempt in range(3):
        try:
            return self.gateway.charge(amount)
        except TransientError:
            if attempt == 2:
                raise
            time.sleep(1)
        """
    }
)
```

**Evaluations:**
* **OrderService**: Accept - "Retries improve reliability"
* **AuditService**: Reject - "Could cause duplicate charges"
* **LoggerService**: Accept - "We can log each attempt"

**Vote:** 2 accept, 1 reject (close vote within 1)

### 4.2 Arbiter Invocation

Because `abs(2 - 1) <= 1` (close vote) and `require_arbiter_on_conflict=True`, the arbiter is invoked:

```python
# NegotiationEngine detects conflict
needs_arbitration = True  # 2 vs 1 is close

# Get arbiter
arbiter = arbiter_agents[0]  # ArbiterService

# Invoke arbiter
arbiter_eval = arbiter.arbitrate_conflict(
    proposal=payment_proposal,
    evaluations=[order_eval, audit_eval, logger_eval],
    round_num=1
)
```

### 4.3 Arbiter Decision

**ArbiterService LLM Analysis:**
```
Reviewing proposal: add_retry_logic

Proposed Change:
- Adds 3-attempt retry loop
- 1-second delay between retries
- Only retries TransientError

Evaluations:
- OrderService (accept): "Improves reliability"
- AuditService (reject): "Could cause duplicate charges"
- LoggerService (accept): "We can log each attempt"

Analysis:
1. Technical Correctness: The retry logic only catches TransientError,
   not permanent failures. This is safe.
2. Duplicate Charge Risk: The concern is valid but the code only retries
   on TransientError, which by definition means the charge didn't go through.
   The gateway should handle idempotency.
3. Impact: Improves system resilience without introducing significant risk.

Decision: ACCEPT
Reasoning: The retry logic is technically sound and the duplicate charge
concern is mitigated by the gateway's idempotency guarantees. The benefit
of improved reliability outweighs the minimal risk.
```

**Arbiter Evaluation:**
```python
ProposalEvaluation(
    proposal_id="prop_payment_001",
    evaluator="ArbiterService (ARBITER)",
    round=1,
    decision="accept",
    reasoning="[ARBITER] The retry logic is technically sound. The duplicate charge concern is valid but mitigated by the gateway's idempotency. Benefit outweighs risk.",
    confidence=1.0  # Final decision
)
```

### 4.4 Commit Created with Arbiter Consensus

```python
CommitRecord(
    commit_id="commit_003",
    proposal_id="prop_payment_001",
    round=1,
    proposer="PaymentService",
    evaluators=["OrderService", "AuditService", "LoggerService", "ArbiterService (ARBITER)"],
    consensus_type="arbiter",  # Decided by arbiter
    resolution={
        "file_path": "payment.py",
        "target": "process_payment",
        "old_code": "...",
        "new_code": "..."
    },
    files_modified=["payment.py"]
)
```

**Result:** Despite initial disagreement, arbiter made binding decision to accept. Code is modified.

### 4.5 Key Takeaways: Arbiter System

1. **Automatic Invocation**: Arbiter triggered on close/tied votes
2. **Impartial Review**: Arbiter sees all evidence and makes unbiased decision
3. **LLM-Powered**: Uses AI to analyze technical merits
4. **Binding Decision**: Arbiter's verdict becomes final commit decision
5. **Traceable**: Consensus type "arbiter" marks these special commits
6. **Safety**: Prevents deadlocks when agents can't agree

---

## 5. macOS App UX for Hello World

### 5.1 Build Mode UI

**Main View:**
* Graph visualization showing 3 nodes (HelloService, PrinterService, LoggerService)
* "Build" button prominent

**During Build:**
* Agent conversation panel shows:
  ```
  [PrinterService] Proposing: Add color support to output
  [LoggerService] Evaluating proposal from PrinterService
  [LoggerService] Decision: Accept
  [LoggerService] Proposing: Add timestamps to logs
  [PrinterService] Evaluating proposal from LoggerService
  [PrinterService] Decision: Accept
  [NegotiationEngine] Committing changes to 2 files
  ```
* Code diff panel shows before/after for each file
* Progress indicator: "Building... Agents active"

**After Build:**
* Success message: "Build Complete - 2 files modified"
* Button changes to "Run"

### 5.2 Runtime Mode UI

**During Runtime:**
* Console output panel shows:
  ```
  Hello, World!  # in green
  [LOG 2025-11-14 10:30:00] Greeting generated: Hello, World!
  ```
* Execution trace shows function calls
* No agent conversations (agents dormant)

---

## 6. Progressive Complexity

This Hello World example demonstrates the minimum viable Build/Runtime flow.

**What's minimal here:**
* Only 3 simple classes
* Simple schema negotiations (no complex type mismatches)
* Simple code changes (add features, no refactoring)

**What can be added later:**
* Complex schema reconciliation (type conflicts)
* Multi-file refactoring (agents coordinate across multiple files)
* Dependency resolution (agents negotiate who provides what)
* Error handling negotiations
* Performance optimization negotiations

But the **core Build/Runtime distinction** is demonstrated: agents refactor in Build Mode, code executes statically in Runtime Mode.

---

## 7. Implementation Priority

For the Hello World proof of concept:

**Must-Have (v0):**
* Build Mode agent activation (simple LLM wrapper)
* Basic negotiation (proposal → evaluation → commit)
* Code file writing (apply agreed changes)
* Runtime Mode static execution (import and run)
* macOS app showing both modes

**Nice-to-Have (v0.1+):**
* Advanced schema negotiation
* Multi-round negotiation with counters
* Agent memory across negotiation rounds
* Build artifact caching
* Incremental builds

---

The key insight: **Hello World proves the system works even with minimal agent intelligence**, then complexity can be layered on top.

# GraphBus Core Pipeline – Agent Negotiation & Code Refactoring

This document provides detailed specifications for the **NEGOTIATION_LOOP** stage in Build Mode, where agents actively negotiate and refactor code.

**Context:** This only applies to **Build Mode**. Runtime Mode has no negotiation.

---

## 1. Negotiation in Build Mode

### 1.1 Core Concept

During Build Mode, **LLM-powered agents** use a negotiation protocol to:

* **Identify code quality issues** (schema mismatches, missing validation, etc.)
* **Propose code changes** to fix issues or add improvements
* **Evaluate each other's proposals** using LLM reasoning
* **Reach consensus** on what changes to make
* **Commit agreed changes** to source files

This is **NOT** runtime negotiation of resources or tasks. This is **build-time negotiation of code refactorings**.

---

## 2. Negotiation Pipeline Stage Detail

### 2.1 NEGOTIATION_LOOP Stage Breakdown

The `NEGOTIATION_LOOP` stage from the Build Mode pipeline is itself a multi-step process:

```text
NEGOTIATION_LOOP
├── SEED_INITIAL_PROPOSALS
├── ROUND_LOOP (iterative)
│   ├── SEND_PROPOSALS
│   ├── RECEIVE_PROPOSALS
│   ├── EVALUATE_PROPOSALS
│   ├── SEND_EVALUATIONS
│   ├── PROCESS_EVALUATIONS
│   ├── CREATE_COMMITS
│   └── CHECK_CONVERGENCE
└── NEGOTIATION_COMPLETE
```

### 2.2 Stage-by-Stage Semantics

#### `SEED_INITIAL_PROPOSALS`

**Input:**
* `schema_conflicts` (from DETECT_SCHEMA_CONFLICTS)
* `active_agents`

**Behavior:**
* For each schema conflict, generate initial proposal from affected agent
* Agent uses LLM to draft code change that resolves conflict

**Output:**
```python
context["proposals"] = {
    "proposal_001": Proposal(
        proposal_id="proposal_001",
        src="HelloService",
        dst="PrinterService",
        intent="align_schema",
        code_change={
            "file": "printer.py",
            "method": "print_message",
            "old_signature": "def print_message(self, msg):",
            "new_signature": "def print_message(self, message: str):",
            "reason": "Align with HelloService output schema which uses 'message' field"
        }
    ),
    ...
}
```

---

#### `ROUND_LOOP`

The negotiation proceeds in rounds until convergence.

**Round N:**

##### `SEND_PROPOSALS`

**Input:** `proposals` (current round's new proposals)

**Behavior:**
* For each proposal:
  * Agent Bus routes proposal to target agent(s)
  * If `dst` is None, broadcast to all relevant agents
  * Proposal includes full context (code change, reason, dependencies)

**Output:** Proposals in flight on the bus

---

##### `RECEIVE_PROPOSALS`

**Input:** Messages from Agent Bus

**Behavior:**
* Each agent receives proposals addressed to it
* Proposals are queued in agent's inbox

**Output:** `agent_inboxes[agent_name] = [proposal1, proposal2, ...]`

---

##### `EVALUATE_PROPOSALS`

**Critical: LLM-Powered Evaluation**

**Input:** `agent_inboxes`

**Behavior:**
* For each agent that received proposals:
  * Agent uses **LLM to evaluate each proposal**:
    * Read the proposed code change
    * Understand impact on its own code
    * Consider dependencies and contracts
    * Decide: accept, reject, or counter-propose
  * Agent generates `ProposalEvaluation` with reasoning

**Example LLM prompt for evaluation:**

```text
You are the PrinterService agent. You received this proposal:

Proposal from HelloService:
- Intent: Change your print_message parameter from 'msg' to 'message'
- Reason: Align with schema output from HelloService
- Code change:
  OLD: def print_message(self, msg):
  NEW: def print_message(self, message: str):

Your current code:
[source code of PrinterService]

Evaluate this proposal and respond with:
1. Decision: accept, reject, or counter
2. Reasoning: Why you made this decision
3. Counter-proposal (if applicable): Alternative change that would work better

Consider:
- Does this improve schema consistency?
- Will this break any existing callers?
- Are there better alternatives?
```

**Output:**
```python
context["evaluations"] = {
    "proposal_001": [
        ProposalEvaluation(
            proposal_id="proposal_001",
            evaluator="PrinterService",
            decision="accept",
            reason="This aligns parameter naming with schema field, improves consistency",
            counter_proposal=None
        )
    ],
    ...
}
```

---

##### `SEND_EVALUATIONS`

**Input:** `evaluations`

**Behavior:**
* Send evaluations back to proposing agents via Agent Bus

**Output:** Evaluations routed to original proposers

---

##### `PROCESS_EVALUATIONS`

**Input:** Evaluations received by proposing agents

**Behavior:**
* Proposing agent receives all evaluations for its proposal
* If all evaluations are "accept" → proceed to commit
* If any "reject" → proposal fails (unless countered)
* If "counter" → new proposals generated for next round

**Output:**
```python
context["proposal_status"] = {
    "proposal_001": "ready_to_commit",
    "proposal_002": "rejected",
    "proposal_003": "countered"
}
```

---

##### `CREATE_COMMITS`

**Input:** Proposals with status "ready_to_commit"

**Behavior:**
* For each accepted proposal:
  * Create `CommitRecord` with all participants
  * Mark proposal as committed
  * Add to commit queue

**Output:**
```python
context["commits"] = [
    CommitRecord(
        proposal_id="proposal_001",
        participants=["HelloService", "PrinterService"],
        resolution={
            "file": "printer.py",
            "change": "rename parameter msg -> message"
        },
        files_modified=["printer.py"],
        timestamp=time.time()
    ),
    ...
]
```

---

##### `CHECK_CONVERGENCE`

**Input:**
* `proposals` (new proposals this round)
* `evaluations`
* `commits`
* Round counter

**Behavior:**
* Check termination conditions:
  * No new proposals generated → converged
  * Max rounds reached → stop
  * All schema conflicts resolved → success

**Output:** `continue_negotiation: bool`

---

#### `NEGOTIATION_COMPLETE`

**Input:** Final state of negotiations

**Behavior:**
* Log summary of negotiations
* Prepare commit list for APPLY_CODE_CHANGES stage

**Output:**
```python
context["negotiation_summary"] = {
    "total_proposals": 15,
    "accepted": 12,
    "rejected": 2,
    "still_pending": 1,
    "rounds": 3,
    "commits_ready": [commit1, commit2, ...]
}
```

---

## 3. Negotiation Primitives (Build Mode Only)

### 3.1 Enhanced Proposal Structure

```python
@dataclass
class Proposal:
    proposal_id: str
    round: int  # which negotiation round
    src: str  # proposing agent
    dst: str | None  # target agent (None = broadcast)
    intent: str  # "align_schema", "add_validation", "refactor_method", etc.

    # Code change details
    code_change: CodeChange
    schema_change: SchemaChange | None

    # Negotiation context
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
    diff: str  # unified diff format

@dataclass
class SchemaChange:
    method: str
    input_schema_before: dict
    input_schema_after: dict
    output_schema_before: dict
    output_schema_after: dict
```

### 3.2 Enhanced Evaluation Structure

```python
@dataclass
class ProposalEvaluation:
    proposal_id: str
    evaluator: str  # evaluating agent
    round: int

    # Decision
    decision: str  # "accept", "reject", "counter", "defer"
    confidence: float  # 0.0-1.0, how confident the LLM is

    # LLM reasoning
    reasoning: str  # detailed explanation from LLM
    concerns: list[str]  # specific issues identified
    suggestions: list[str]  # improvements even if accepting

    # Counter-proposal (if applicable)
    counter_proposal: Proposal | None

    # Impact assessment
    impact_assessment: dict  # {
                             #   "breaks_contracts": bool,
                             #   "affects_dependencies": list[str],
                             #   "estimated_risk": "low" | "medium" | "high"
                             # }
```

### 3.3 Enhanced Commit Structure

```python
@dataclass
class CommitRecord:
    commit_id: str
    proposal_id: str
    round: int

    # Participants
    proposer: str
    evaluators: list[str]
    consensus_type: str  # "unanimous", "majority", "override"

    # Resolution
    resolution: dict  # final agreed code change
    files_modified: list[str]
    schema_changes: list[SchemaChange]

    # Metadata
    timestamp: float
    negotiation_log: list[dict]  # full conversation history
```

---

## 4. Agent LLM Integration

### 4.1 Agent Implementation

```python
class LLMAgent:
    """
    LLM-powered agent that can analyze code and negotiate changes.
    Only exists in Build Mode.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        source_code: str,
        bus: AgentBus,
        negotiation_engine: NegotiationEngine,
        llm_client: LLMClient
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.source_code = source_code
        self.bus = bus
        self.negotiation_engine = negotiation_engine
        self.llm = llm_client
        self.memory = AgentMemory()

    def analyze_code(self) -> dict:
        """
        Use LLM to understand own code.
        """
        prompt = f"""
        {self.system_prompt}

        Your current code:
        ```python
        {self.source_code}
        ```

        Analyze your code and identify:
        1. What this class is responsible for
        2. What methods it exposes (with schemas)
        3. What dependencies it has on other classes
        4. Any potential issues or improvements

        Return analysis as JSON.
        """
        response = self.llm.generate(prompt)
        analysis = parse_json(response)
        self.memory.store("code_analysis", analysis)
        return analysis

    def propose_change(self, intent: str, context: dict) -> Proposal:
        """
        Use LLM to generate a proposal for code change.
        """
        prompt = f"""
        {self.system_prompt}

        Context: {context}
        Intent: {intent}

        Your current code:
        ```python
        {self.source_code}
        ```

        Propose a specific code change to address this intent.
        Return proposal with:
        - Target method/class
        - Old code (exact match from above)
        - New code (your proposed change)
        - Detailed reasoning
        """
        response = self.llm.generate(prompt)
        proposal = parse_proposal(response)
        proposal.src = self.name
        return proposal

    def evaluate_proposal(self, proposal: Proposal) -> ProposalEvaluation:
        """
        Use LLM to evaluate another agent's proposal.
        """
        prompt = f"""
        {self.system_prompt}

        You received this proposal from {proposal.src}:

        Intent: {proposal.intent}
        Reason: {proposal.reason}

        Proposed code change:
        ```python
        # OLD
        {proposal.code_change.old_code}

        # NEW
        {proposal.code_change.new_code}
        ```

        Your current code:
        ```python
        {self.source_code}
        ```

        Evaluate this proposal:
        1. Will this improve code quality?
        2. Does it align with schemas/contracts?
        3. Will it break anything?
        4. Do you accept, reject, or counter?

        Return evaluation with reasoning.
        """
        response = self.llm.generate(prompt)
        evaluation = parse_evaluation(response)
        evaluation.evaluator = self.name
        return evaluation
```

### 4.2 LLM Client Interface

```python
class LLMClient:
    """
    Abstraction over LLM API (Anthropic, OpenAI, etc.)
    """

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate LLM response for a prompt.
        Used by agents for analysis, proposals, evaluations.
        """
        # Call LLM API (e.g., Anthropic Claude)
        response = anthropic.messages.create(
            model="claude-sonnet-4",
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.content[0].text
```

---

## 5. Negotiation Scenarios

### 5.1 Simple Schema Alignment

**Scenario:** HelloService outputs `{"message": str}` but PrinterService expects `{"msg": str}`.

**Negotiation Flow:**

1. **DETECT_SCHEMA_CONFLICTS** identifies mismatch
2. **HelloService agent** proposes: "PrinterService should rename parameter to 'message'"
3. **PrinterService agent** evaluates:
   * LLM analyzes impact
   * Decides: "Accept - improves consistency, no breaking changes"
4. **Commit created**: Rename `msg` to `message` in `printer.py`
5. **APPLY_CODE_CHANGES**: File modified

**Rounds:** 1
**Proposals:** 1
**Commits:** 1

---

### 5.2 Complex Multi-Agent Refactoring

**Scenario:** OrderService, InventoryService, PaymentService have inconsistent error handling schemas.

**Negotiation Flow:**

**Round 1:**
1. **OrderService** proposes: "All services should return `{"status": str, "error": str | None}`"
2. **InventoryService** evaluates: "Counter - I prefer `{"success": bool, "error_message": str}`"
3. **PaymentService** evaluates: "Accept OrderService proposal"

**Round 2:**
4. **InventoryService** sends counter-proposal
5. **OrderService** evaluates counter: "Reject - 'status' string is more flexible than bool"
6. **PaymentService** evaluates counter: "Agree with OrderService"

**Round 3:**
7. **InventoryService** evaluates rejection: "Accept original - majority agrees"
8. **Commit created**: All three services adopt OrderService schema

**Rounds:** 3
**Proposals:** 2 (1 original + 1 counter)
**Commits:** 1 (final consensus)

---

## 6. Safety Guardrails & Arbitration Mechanics

### 6.1 SafetyConfig: Comprehensive Protection

GraphBus implements multi-layered safety guardrails to prevent runaway negotiation:

```python
@dataclass
class SafetyConfig:
    # Negotiation round limits
    max_negotiation_rounds: int = 10
    convergence_threshold: int = 2  # Rounds without proposals before stopping

    # Proposal rate limiting
    max_proposals_per_agent: int = 3  # Total budget per agent
    max_proposals_per_round: int = 1  # Per round per agent
    max_back_and_forth: int = 3  # Counter-proposal depth

    # Arbiter configuration
    require_arbiter_on_conflict: bool = True
    arbiter_agents: list[str] = []  # Optional: pre-designated arbiters

    # File modification limits
    max_file_changes_per_commit: int = 1
    max_total_file_changes: int = 10

    # Code protection
    allow_external_dependencies: bool = False
    protected_files: list[str] = []  # Immutable files
```

### 6.2 Proposal Rate Limiting

**Problem:** Without limits, agents could spam proposals indefinitely.

**Solution:** Per-agent proposal budgets enforced by `NegotiationEngine`.

**Implementation:**
```python
class NegotiationEngine:
    def can_agent_propose(self, agent_name: str) -> tuple[bool, str]:
        count = self.proposal_counts.get(agent_name, 0)
        if count >= self.safety_config.max_proposals_per_agent:
            return False, f"Max proposals reached ({count}/{max})"
        return True, ""

    def add_proposal(self, proposal: Proposal) -> bool:
        can_propose, reason = self.can_agent_propose(proposal.src)
        if not can_propose:
            print(f"Rejected: {reason}")
            return False
        self.proposal_counts[proposal.src] += 1
        # ... add proposal
```

**Effect:**
* Agents can only make N proposals total across all rounds
* Prevents spam and forces agents to prioritize
* Ensures negotiation eventually terminates

### 6.3 File Modification Limits

**Problem:** Runaway negotiation could modify entire codebase.

**Solution:** Hard caps on file modifications.

**Limits:**
1. **Per-commit limit**: `max_file_changes_per_commit = 1`
   - Each commit can only modify 1 file
   - Forces focused, atomic changes
2. **Total limit**: `max_total_file_changes = 10`
   - Entire build session capped at 10 file modifications
   - Prevents excessive code churn

**Enforcement:**
```python
def create_commits(self, agents):
    for proposal in self.proposals:
        if decision == "accept":
            if self.total_files_modified >= self.safety_config.max_total_file_changes:
                print(f"Max file changes reached, skipping commit")
                continue
            # Create commit
            self.total_files_modified += 1
```

### 6.4 Protected Files

**Problem:** Certain files should never be modified by agents.

**Solution:** Protected files list in SafetyConfig.

**Example:**
```python
SafetyConfig(
    protected_files=[
        "config.py",
        "secrets.yaml",
        "__init__.py"
    ]
)
```

**Enforcement:**
```python
def add_proposal(self, proposal: Proposal) -> bool:
    if proposal.code_change.file_path in self.safety_config.protected_files:
        print(f"Rejected: {file_path} is protected")
        return False
```

### 6.5 Convergence Detection

**Problem:** How do we know when agents are "done" negotiating?

**Solution:** Track rounds without new proposals.

**Algorithm:**
```python
if new_proposals == 0:
    self.rounds_without_proposals += 1
    if self.rounds_without_proposals >= self.convergence_threshold:
        print("CONVERGENCE DETECTED")
        return  # Stop negotiation
else:
    self.rounds_without_proposals = 0  # Reset counter
```

**Typical Flow:**
```
Round 0: 3 proposals → rounds_without_proposals = 0
Round 1: 1 proposal  → rounds_without_proposals = 0
Round 2: 0 proposals → rounds_without_proposals = 1
Round 3: 0 proposals → rounds_without_proposals = 2 (>= threshold)
→ CONVERGENCE DETECTED, stop
```

### 6.6 Arbiter Agents: Conflict Resolution

**Problem:** Agents may disagree (tie votes or close decisions).

**Solution:** Special arbiter agents make final binding decisions.

#### 6.6.1 Arbiter Agent Definition

```python
class ArbiterService(GraphBusNode):
    SYSTEM_PROMPT = """
    You are an impartial arbiter agent responsible for resolving conflicts
    during code negotiations. Review proposals that have conflicting evaluations
    and make fair, unbiased decisions based on engineering principles.
    """

    IS_ARBITER = True  # Mark as arbiter
```

**Key Attribute:** `IS_ARBITER = True` flags this agent as an arbiter.

#### 6.6.2 When Arbiters Are Invoked

**Conflict Detection Logic:**
```python
accepts = sum(1 for e in evaluations if e.decision == "accept")
rejects = sum(1 for e in evaluations if e.decision == "reject")

needs_arbitration = False
if require_arbiter_on_conflict:
    if accepts == rejects:  # Tie
        needs_arbitration = True
    elif abs(accepts - rejects) <= 1:  # Close vote (e.g., 3-2)
        needs_arbitration = True
```

**Trigger Conditions:**
* **Tie vote**: 2 accept, 2 reject
* **Close vote**: 3 accept, 2 reject (within 1 vote)
* Only triggered if `require_arbiter_on_conflict = True`

#### 6.6.3 Arbitration Process

**Flow:**
1. Conflict detected for `proposal_123`
2. Engine selects arbiter: `arbiter_agents[0]`
3. Engine calls: `arbiter.arbitrate_conflict(proposal, evaluations, round_num)`
4. Arbiter agent uses LLM to review:
   - Proposed code change
   - All agent evaluations with reasoning
   - Technical merits and risks
5. Arbiter returns `ProposalEvaluation` with final decision
6. Arbiter's decision is **binding** and becomes the commit decision

**Arbiter LLM Prompt:**
```python
prompt = f"""
You are acting as an arbiter to resolve a disputed proposal.

Proposal:
- From: {proposal.src}
- Intent: {proposal.intent}
- Target: {proposal.code_change.target}

Proposed change:
OLD: {proposal.code_change.old_code}
NEW: {proposal.code_change.new_code}

Evaluations ({accepts} accept, {rejects} reject):
- AgentA: accept - "Improves readability"
- AgentB: reject - "Could break existing callers"
- AgentC: accept - "Good change"

As an arbiter, make a final decision based on:
1. Technical correctness
2. System impact
3. Quality of reasoning

Return: {{"decision": "accept" or "reject", "reasoning": "..."}}
"""
```

**Arbiter Evaluation:**
```python
ProposalEvaluation(
    proposal_id="proposal_123",
    evaluator="ArbiterService (ARBITER)",
    round=0,
    decision="accept",
    reasoning="[ARBITER] The change improves code quality and the risk of breaking callers is low",
    confidence=1.0  # Arbiter decisions are final
)
```

#### 6.6.4 Consensus Types

After arbitration, commits are marked with consensus type:

```python
CommitRecord(
    consensus_type="arbiter",  # vs "unanimous" or "majority"
    evaluators=["AgentA", "AgentB", "AgentC", "ArbiterService (ARBITER)"],
    # ...
)
```

**Consensus Types:**
* **"unanimous"**: All agents accepted, no arbiter needed
* **"majority"**: More accepts than rejects, no arbiter needed
* **"arbiter"**: Arbiter made the final decision

### 6.7 Multi-Arbiter Support (Future)

Current implementation uses first arbiter found. Future versions could:
* Support multiple arbiters with voting
* Allow configurable arbiter selection strategies
* Enable domain-specific arbiters (e.g., security arbiter, performance arbiter)

### 6.8 Termination Guarantees

**GraphBus guarantees negotiation will always terminate:**

1. **Max rounds hard limit**: `max_negotiation_rounds`
2. **Convergence detection**: `convergence_threshold` rounds without proposals
3. **File modification cap**: `max_total_file_changes`
4. **Proposal budgets**: `max_proposals_per_agent`

**Even in worst case:**
* All agents use their proposal budget
* Max rounds reached
* System stops gracefully with partial results

## 6.9 Convergence & Termination Summary

Negotiation loop terminates when **any** of these conditions are met:

1. **Convergence**: No new proposals for `convergence_threshold` consecutive rounds
2. **Round limit**: `current_round >= max_negotiation_rounds`
3. **File limit**: `total_files_modified >= max_total_file_changes`
4. **Manual stop**: User intervention via API/UI (future)

**Termination Status:**
```python
{
    "terminated": True,
    "reason": "convergence" | "max_rounds" | "file_limit" | "manual",
    "rounds_executed": 4,
    "proposals_made": 8,
    "commits_created": 6,
    "files_modified": 5
}
```

---

## 7. Relationship to Runtime Mode

**Critical:** Everything in this document applies **ONLY to Build Mode**.

**Runtime Mode has:**
* No negotiation
* No LLM agents
* No proposals/evaluations/commits
* No code modifications

**The code produced by Build Mode negotiations is what Runtime Mode executes statically.**

---

## 8. Implementation Priority for v0

**Must-Have:**
* Basic proposal/evaluation/commit flow
* Single-round negotiation (no counters)
* Simple schema alignment use cases
* LLM integration for evaluation

**Nice-to-Have:**
* Multi-round negotiation with counters
* Complex refactoring scenarios
* Sophisticated convergence detection
* Human-in-the-loop approval gates

---

The negotiation system is the **core innovation** of GraphBus: agents collaboratively refactor code during Build Mode, then the refined code runs deterministically in Runtime Mode.

"""
LLM-powered agent for Build Mode
"""

import json
from typing import Optional

from graphbus_core.node_base import GraphBusNode
from graphbus_core.model.agent_def import AgentDefinition, NodeMemory
from graphbus_core.model.message import Proposal, ProposalEvaluation, CodeChange, generate_id
from graphbus_core.agents.llm_client import LLMClient
from graphbus_core.exceptions import (
    IntentRelevanceError,
    CodeAnalysisError,
    ProposalGenerationError,
    EvaluationError,
    LLMResponseError
)
from graphbus_core.utils import parse_json_from_llm_response, validate_json_structure
from graphbus_core.agents.schemas import (
    INTENT_RELEVANCE_SCHEMA,
    CODE_ANALYSIS_SCHEMA,
    CODE_SUGGESTIONS_SCHEMA,
    PROPOSAL_SCHEMA,
    EVALUATION_SCHEMA,
    CLARIFYING_QUESTIONS_SCHEMA,
    RECONCILIATION_SCHEMA,
    ARBITRATION_SCHEMA
)


class LLMAgent(GraphBusNode):
    """
    Minimal LLM-powered agent that can analyze code and propose changes.

    In this simplified version:
    - Agent can analyze its own code
    - Agent can propose simple improvements (like adding timestamps)
    - Agent can evaluate proposals from other agents
    """

    def __init__(
        self,
        agent_def: AgentDefinition,
        llm_client: LLMClient,
        memory: Optional[NodeMemory] = None,
        user_intent: str = None
    ):
        """
        Initialize the LLM agent.

        Args:
            agent_def: AgentDefinition with source code and system prompt
            llm_client: LLM client for API calls
            memory: Agent memory (optional)
            user_intent: Optional user intent/goal to guide agent behavior
        """
        # Initialize GraphBusNode base class
        super().__init__(bus=None, memory=memory or NodeMemory())

        # Set Build Mode since LLMAgent is always used in Build Mode
        self.set_mode("build")

        # LLM-specific attributes
        self.name = agent_def.name
        self.agent_def = agent_def
        self.llm = llm_client
        self.user_intent = user_intent  # Store for later use

        # Combine base GraphBusNode collaboration protocol with agent-specific prompt
        base_protocol = GraphBusNode.SYSTEM_PROMPT
        agent_specific_prompt = agent_def.system_prompt.text

        # Build combined system prompt with user intent if provided
        if agent_specific_prompt:
            self.system_prompt = f"""{base_protocol}

---

# Agent-Specific Instructions for {agent_def.name}

{agent_specific_prompt}

---

"""
            # Add user intent section if provided
            if user_intent:
                self.system_prompt += f"""# User Intent/Goal

The user has specified the following goal for this negotiation:

**{user_intent}**

Keep this goal in mind when:
- Analyzing your code
- Proposing improvements
- Evaluating other agents' proposals
- Asking clarifying questions

All your actions should align with and support this user intent.

---

"""
            self.system_prompt += "Remember: Apply both the collaboration protocol above AND your specific role instructions when participating in negotiation."
        else:
            # If no agent-specific prompt, just use the base protocol
            self.system_prompt = base_protocol
            if user_intent:
                self.system_prompt += f"""

---

# User Intent/Goal

**{user_intent}**

All your actions should align with and support this user intent.
"""

        self.is_arbiter = agent_def.is_arbiter
        self.proposal_count = 0  # Track number of proposals made
        self.code_line_count = len(agent_def.source_code.split('\n'))

    def get_system_prompt(self) -> str:
        """
        Override GraphBusNode.get_system_prompt() to return instance-level prompt.

        In Build Mode, agents are dynamically created from AgentDefinition,
        so we use the instance-level system_prompt instead of class-level SYSTEM_PROMPT.
        """
        return self.system_prompt

    def check_intent_relevance(self, user_intent: str) -> dict:
        """
        Check if the user intent is relevant to this agent's scope.

        Args:
            user_intent: User's goal or intent

        Returns:
            Dict with relevance decision and reasoning
        """
        prompt = f"""
You are {self.name}. Here is your current code:

```python
{self.agent_def.source_code}
```

User Intent: {user_intent}

Is this user intent relevant to your agent's scope and responsibilities?

Respond using the check_intent_relevance tool with your structured assessment."""

        try:
            relevance_data = self.llm.generate_with_tool(
                prompt,
                tool_name="check_intent_relevance",
                tool_schema=INTENT_RELEVANCE_SCHEMA,
                system=self.system_prompt
            )
            return relevance_data
        except Exception as e:
            print(f"Warning: Agent {self.name} intent relevance check failed: {e}")
            return {"relevant": False, "reasoning": "LLM response error", "confidence": 0.0}

    def check_code_size(self) -> dict:
        """
        Check if agent code exceeds size threshold (100 lines).

        Returns:
            Dict with size check results and refactoring suggestions
        """
        if self.code_line_count <= 100:
            return {
                "exceeds_threshold": False,
                "line_count": self.code_line_count,
                "suggestions": []
            }

        prompt = f"""
This agent has {self.code_line_count} lines of code, exceeding the 100-line threshold.

```python
{self.agent_def.source_code}
```

Analyze the code and suggest how to refactor it. Return ONLY a JSON object:
{{
  "suggestions": [
    "suggestion 1: what to abstract or subdivide",
    "suggestion 2: ...",
    ...
  ],
  "potential_new_agents": [
    {{"name": "NewAgentName", "responsibility": "what it would handle"}}
  ]
}}
"""

        try:
            response = self.llm.generate(prompt, system=self.system_prompt)
            refactor_data = parse_json_from_llm_response(response, context=f"{self.name} code size check")

            # Validate required keys
            validate_json_structure(refactor_data, ["suggestions"], context="Code size check response")

            refactor_data["exceeds_threshold"] = True
            refactor_data["line_count"] = self.code_line_count
            return refactor_data
        except LLMResponseError as e:
            print(f"Warning: Agent {self.name} size check failed: {e}")
            return {
                "exceeds_threshold": True,
                "line_count": self.code_line_count,
                "suggestions": ["Consider breaking into smaller agents"],
                "potential_new_agents": []
            }
        except CodeAnalysisError as e:
            print(f"Warning: Agent {self.name} size check failed: {e}")
            return {
                "exceeds_threshold": True,
                "line_count": self.code_line_count,
                "suggestions": ["Analysis failed - manual review needed"],
                "potential_new_agents": []
            }

    def generate_clarifying_questions(self, user_intent: str) -> list:
        """
        Generate intelligent clarifying questions for the user based on intent and agent scope.

        This allows agents to gather more context before making proposals, leading to
        better, more production-ready solutions.

        Args:
            user_intent: User's stated goal or intent

        Returns:
            List of question dicts with structure:
            {
                "question": "The question to ask",
                "options": ["option1", "option2", ...],
                "context": "Why this question matters",
                "agent": "Which agent is asking"
            }
        """
        prompt = f"""
You are {self.name}. Here is your code:

```python
{self.agent_def.source_code}
```

User Intent: {user_intent}

Generate 1-3 intelligent clarifying questions that would help you implement this intent better.
Questions should be:
- Specific and actionable
- Related to edge cases, production concerns, or design choices
- Something the user needs to decide (not something you can infer)

Return ONLY a JSON array:
[
  {{
    "question": "How should the system handle X edge case?",
    "options": ["Option A with trade-offs", "Option B with trade-offs", "Option C"],
    "context": "Why this matters for production deployment",
    "importance": "critical" or "nice-to-have"
  }},
  ...
]

If no questions are needed, return an empty array: []
"""

        try:
            response = self.llm.generate(prompt, system=self.system_prompt)

            # Parse JSON (could be array or object)
            parsed = parse_json_from_llm_response(response, context=f"{self.name} question generation")

            # Ensure it's a list
            if isinstance(parsed, dict):
                questions = [parsed]
            elif isinstance(parsed, list):
                questions = parsed
            else:
                questions = []

            # Add agent name to each question
            for q in questions:
                if isinstance(q, dict):
                    q['agent'] = self.name

            return questions
        except LLMResponseError as e:
            print(f"Warning: Agent {self.name} question generation failed: {e}")
            return []

    def analyze_code(self, user_intent: str = None) -> dict:
        """
        Use LLM to analyze the agent's own code.

        Args:
            user_intent: Optional user intent/goal to guide analysis

        Returns:
            Analysis dict with insights
        """
        intent_context = ""
        if user_intent:
            intent_context = f"""

USER INTENT: {user_intent}

Focus your analysis on improvements that align with this user intent.
"""

        prompt = f"""
Analyze this code and identify potential improvements:

```python
{self.agent_def.source_code}
```
{intent_context}

Provide a structured analysis with issues, improvements, priority level, and summary."""

        try:
            analysis = self.llm.generate_with_tool(
                prompt,
                tool_name="analyze_code",
                tool_schema=CODE_ANALYSIS_SCHEMA,
                system=self.system_prompt
            )

            self.memory.store("code_analysis", analysis)
            return analysis
        except Exception as e:
            print(f"Warning: Agent {self.name} analysis failed: {e}")
            return {
                "issues": [],
                "potential_improvements": [],
                "priority": "low",
                "summary": "Analysis failed"
            }

    def propose_improvement(self, improvement_idea: str, round_num: int = 0, user_intent: str = None) -> Optional[Proposal]:
        """
        Generate a proposal for a specific improvement.

        Args:
            improvement_idea: What to improve (e.g., "add timestamps")
            round_num: Negotiation round number
            user_intent: Optional user intent/goal to align proposal with

        Returns:
            Proposal object or None if can't generate one
        """
        intent_context = ""
        if user_intent:
            intent_context = f"""

USER INTENT: {user_intent}

Ensure your proposed change aligns with and supports this user intent.
"""

        prompt = f"""
Given this code:

```python
{self.agent_def.source_code}
```

Propose a specific code change to implement this improvement: {improvement_idea}
{intent_context}

Make the change minimal and focused. Provide your proposal with exact code before and after,
impact level, and clear rationale."""

        try:
            change_data = self.llm.generate_with_tool(
                prompt,
                tool_name="propose_improvement",
                tool_schema=PROPOSAL_SCHEMA,
                system=self.system_prompt
            )

            # Create proposal
            code_change = CodeChange(
                file_path=self.agent_def.source_file,
                target=change_data.get("target_method", "unknown"),
                change_type="modify",
                old_code=change_data.get("old_code", ""),
                new_code=change_data.get("new_code", ""),
                diff=None
            )

            proposal = Proposal(
                proposal_id=generate_id("prop_"),
                round=round_num,
                src=self.name,
                dst=None,  # Broadcast to all agents
                intent=f"improve_{improvement_idea.replace(' ', '_')}",
                code_change=code_change,
                reason=change_data.get("reason", improvement_idea),
                priority=1
            )

            return proposal

        except LLMResponseError as e:
            print(f"Warning: Agent {self.name} failed to generate proposal - LLM response error: {e}")
            return None
        except ProposalGenerationError as e:
            print(f"Warning: Agent {self.name} failed to generate proposal: {e}")
            return None

    def evaluate_proposal(self, proposal: Proposal, round_num: int = 0) -> ProposalEvaluation:
        """
        Evaluate another agent's proposal using LLM.

        Args:
            proposal: Proposal to evaluate
            round_num: Negotiation round number

        Returns:
            ProposalEvaluation with decision
        """
        # For minimal version: auto-accept if proposal doesn't affect this agent
        # In full version, use LLM to evaluate impact

        # Check if this proposal affects this agent's file
        if proposal.code_change.file_path != self.agent_def.source_file:
            # Doesn't affect me, accept
            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                evaluator=self.name,
                round=round_num,
                decision="accept",
                reasoning=f"Proposal doesn't affect {self.name}",
                confidence=1.0
            )

        # It affects this agent's file - use LLM to evaluate
        prompt = f"""
A proposal has been made to modify your code:

Your current code:
```python
{self.agent_def.source_code}
```

Proposed change:
- Target: {proposal.code_change.target}
- Reason: {proposal.reason}
- Old code:
{proposal.code_change.old_code}
- New code:
{proposal.code_change.new_code}

Should you accept this proposal? Return ONLY a JSON object:
{{
  "decision": "accept" or "reject",
  "reasoning": "brief explanation"
}}
"""

        try:
            response = self.llm.generate(prompt, system=self.system_prompt)
            eval_data = parse_json_from_llm_response(response, context=f"{self.name} proposal evaluation")

            # Validate required keys
            validate_json_structure(eval_data, ["decision"], context="Proposal evaluation")

            # Validate decision value
            decision = eval_data.get("decision", "accept")
            if decision not in ["accept", "reject"]:
                print(f"Warning: Invalid decision '{decision}', defaulting to 'accept'")
                decision = "accept"

            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                evaluator=self.name,
                round=round_num,
                decision=decision,
                reasoning=eval_data.get("reasoning", "Evaluated by LLM"),
                confidence=0.8
            )

        except LLMResponseError as e:
            print(f"Warning: Agent {self.name} evaluation failed - LLM response error: {e}, defaulting to accept")
            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                evaluator=self.name,
                round=round_num,
                decision="accept",
                reasoning="Evaluation failed: LLM response error",
                confidence=0.0
            )
        except EvaluationError as e:
            print(f"Warning: Agent {self.name} evaluation failed: {e}, defaulting to accept")
            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                evaluator=self.name,
                round=round_num,
                decision="accept",
                reasoning="Evaluation failed, defaulting to accept",
                confidence=0.5
            )

    def reconcile_all_proposals(
        self,
        proposals: list[Proposal],
        user_intent: str = None
    ) -> dict:
        """
        Arbiter reviews all proposals holistically and reconciles what each agent should do.

        This happens BEFORE individual evaluations, allowing the arbiter to:
        - Identify conflicts or overlaps between proposals
        - Ensure proposals align with user intent
        - Suggest modifications or prioritization
        - Recommend which proposals should proceed

        Args:
            proposals: All proposals from all agents
            user_intent: User's stated goal/intent

        Returns:
            Dict with reconciliation decisions for each proposal
        """
        if not self.is_arbiter:
            raise ValueError(f"Agent {self.name} is not configured as an arbiter")

        # Build summary of all proposals
        proposal_summary = []
        for prop in proposals:
            proposal_summary.append(
                f"- {prop.proposal_id} from {prop.src}: {prop.intent}\n"
                f"  Target: {prop.code_change.target} in {prop.code_change.file_path}\n"
                f"  Reason: {prop.reason}"
            )

        intent_context = ""
        if user_intent:
            intent_context = f"\n\nUSER INTENT: {user_intent}\nEnsure reconciliation aligns with this intent."

        prompt = f"""
You are acting as an arbiter to reconcile {len(proposals)} proposals from different agents.

PROPOSALS:
{chr(10).join(proposal_summary)}
{intent_context}

Review all proposals holistically and provide reconciliation guidance:
1. Identify any conflicts or overlaps between proposals
2. Determine priority order if proposals affect related code
3. Suggest modifications to avoid conflicts
4. Recommend which proposals should proceed and which should be deferred

Return ONLY a JSON object:
{{
  "overall_assessment": "brief summary of the proposals as a whole",
  "conflicts": [
    {{"proposals": ["prop_id1", "prop_id2"], "issue": "description of conflict"}}
  ],
  "recommendations": {{
    "prop_id1": {{"action": "proceed|defer|modify", "reasoning": "why", "priority": 1-5}},
    "prop_id2": {{"action": "proceed|defer|modify", "reasoning": "why", "priority": 1-5}}
  }},
  "suggested_modifications": [
    {{"proposal": "prop_id", "suggestion": "what to change"}}
  ]
}}
"""

        try:
            response = self.llm.generate(prompt, system=self.system_prompt + "\n\nYou are an impartial arbiter reconciling proposals.")
            reconciliation_data = parse_json_from_llm_response(response, context=f"Arbiter {self.name} reconciliation")

            # Validate structure
            if not isinstance(reconciliation_data, dict):
                raise LLMResponseError(f"Expected dict, got {type(reconciliation_data).__name__}")

            return reconciliation_data
        except LLMResponseError as e:
            print(f"Warning: Arbiter {self.name} reconciliation failed - LLM response error: {e}")
            # Return safe default - allow all to proceed
            return {
                "overall_assessment": "Reconciliation failed, proceeding with all proposals",
                "conflicts": [],
                "recommendations": {
                    prop.proposal_id: {"action": "proceed", "reasoning": "Default", "priority": 3}
                    for prop in proposals
                },
                "suggested_modifications": []
            }

    def arbitrate_conflict(
        self,
        proposal: Proposal,
        evaluations: list[ProposalEvaluation],
        round_num: int = 0
    ) -> ProposalEvaluation:
        """
        Act as arbiter to resolve conflicting evaluations.

        Args:
            proposal: The disputed proposal
            evaluations: All evaluations from other agents
            round_num: Current negotiation round

        Returns:
            Final arbitration decision
        """
        if not self.is_arbiter:
            raise ValueError(f"Agent {self.name} is not configured as an arbiter")

        # Count votes
        accepts = sum(1 for e in evaluations if e.decision == "accept")
        rejects = sum(1 for e in evaluations if e.decision == "reject")

        # Prepare evaluation summary for LLM
        eval_summary = []
        for ev in evaluations:
            eval_summary.append(f"- {ev.evaluator}: {ev.decision} (confidence: {ev.confidence}) - {ev.reasoning}")

        prompt = f"""
You are acting as an arbiter to resolve a disputed proposal.

Proposal:
- ID: {proposal.proposal_id}
- From: {proposal.src}
- Intent: {proposal.intent}
- Reason: {proposal.reason}
- Target: {proposal.code_change.target}
- File: {proposal.code_change.file_path}

Proposed change:
OLD:
{proposal.code_change.old_code[:200]}...

NEW:
{proposal.code_change.new_code[:200]}...

Evaluations ({accepts} accept, {rejects} reject):
{chr(10).join(eval_summary)}

As an arbiter, make a final decision. Consider:
1. Technical correctness of the change
2. Potential impact on the system
3. Quality of reasoning from both sides

Return ONLY a JSON object:
{{
  "decision": "accept" or "reject",
  "reasoning": "detailed explanation of your arbitration decision"
}}
"""

        try:
            response = self.llm.generate(prompt, system=self.system_prompt + "\n\nYou are an impartial arbiter.")
            arbiter_data = parse_json_from_llm_response(response, context=f"Arbiter {self.name} decision")

            # Validate required keys
            validate_json_structure(arbiter_data, ["decision"], context="Arbiter decision")

            # Validate decision value
            decision = arbiter_data.get("decision", "reject")
            if decision not in ["accept", "reject"]:
                print(f"Warning: Invalid arbiter decision '{decision}', defaulting to 'reject'")
                decision = "reject"

            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                evaluator=f"{self.name} (ARBITER)",
                round=round_num,
                decision=decision,
                reasoning=f"[ARBITER] {arbiter_data.get('reasoning', 'Arbitrated')}",
                confidence=1.0  # Arbiter decisions are final
            )

        except LLMResponseError as e:
            print(f"Warning: Arbiter {self.name} failed - LLM response error: {e}, defaulting to reject")
            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                evaluator=f"{self.name} (ARBITER)",
                round=round_num,
                decision="reject",
                reasoning=f"[ARBITER] Arbitration failed: LLM response error",
                confidence=0.5
            )
        except EvaluationError as e:
            print(f"Warning: Arbiter {self.name} failed: {e}, defaulting to reject")
            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                evaluator=f"{self.name} (ARBITER)",
                round=round_num,
                decision="reject",
                reasoning=f"[ARBITER] Arbitration failed: {str(e)}",
                confidence=0.5
            )

"""
LLM-powered agent for Build Mode
"""

import json
from typing import Optional

from graphbus_core.model.agent_def import AgentDefinition, NodeMemory
from graphbus_core.model.message import Proposal, ProposalEvaluation, CodeChange, generate_id
from graphbus_core.agents.llm_client import LLMClient


class LLMAgent:
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
        memory: Optional[NodeMemory] = None
    ):
        """
        Initialize the LLM agent.

        Args:
            agent_def: AgentDefinition with source code and system prompt
            llm_client: LLM client for API calls
            memory: Agent memory (optional)
        """
        self.name = agent_def.name
        self.agent_def = agent_def
        self.llm = llm_client
        self.memory = memory or NodeMemory()
        self.system_prompt = agent_def.system_prompt.text
        self.is_arbiter = agent_def.is_arbiter
        self.proposal_count = 0  # Track number of proposals made

    def analyze_code(self) -> dict:
        """
        Use LLM to analyze the agent's own code.

        Returns:
            Analysis dict with insights
        """
        prompt = f"""
Analyze this code and identify potential improvements:

```python
{self.agent_def.source_code}
```

Return a JSON object with:
- "summary": Brief summary of what this code does
- "potential_improvements": List of specific improvements (e.g., "add timestamps", "add color output")

Keep it simple and practical.
"""

        try:
            response = self.llm.generate(prompt, system=self.system_prompt)
            # Try to parse JSON response
            analysis = json.loads(response)
            self.memory.store("code_analysis", analysis)
            return analysis
        except json.JSONDecodeError:
            # Fallback if LLM doesn't return valid JSON
            return {
                "summary": "Code analysis completed",
                "potential_improvements": []
            }
        except Exception as e:
            print(f"Warning: Agent {self.name} analysis failed: {e}")
            return {
                "summary": "Analysis failed",
                "potential_improvements": []
            }

    def propose_improvement(self, improvement_idea: str, round_num: int = 0) -> Optional[Proposal]:
        """
        Generate a proposal for a specific improvement.

        Args:
            improvement_idea: What to improve (e.g., "add timestamps")
            round_num: Negotiation round number

        Returns:
            Proposal object or None if can't generate one
        """
        prompt = f"""
Given this code:

```python
{self.agent_def.source_code}
```

Propose a specific code change to implement this improvement: {improvement_idea}

Return ONLY a JSON object with:
{{
  "target_method": "name of method to modify",
  "old_code": "exact old code to replace",
  "new_code": "new code to insert",
  "reason": "why this improves the code"
}}

Make the change minimal and focused. The old_code must be an exact match.
"""

        try:
            response = self.llm.generate(prompt, system=self.system_prompt)

            # Try to parse JSON
            change_data = json.loads(response)

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

        except Exception as e:
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
            eval_data = json.loads(response)

            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                evaluator=self.name,
                round=round_num,
                decision=eval_data.get("decision", "accept"),
                reasoning=eval_data.get("reasoning", "Evaluated by LLM"),
                confidence=0.8
            )

        except Exception as e:
            print(f"Warning: Agent {self.name} evaluation failed: {e}, defaulting to accept")
            # Default to accept if evaluation fails
            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                evaluator=self.name,
                round=round_num,
                decision="accept",
                reasoning="Evaluation failed, defaulting to accept",
                confidence=0.5
            )

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
            arbiter_data = json.loads(response)

            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                evaluator=f"{self.name} (ARBITER)",
                round=round_num,
                decision=arbiter_data.get("decision", "reject"),
                reasoning=f"[ARBITER] {arbiter_data.get('reasoning', 'Arbitrated')}",
                confidence=1.0  # Arbiter decisions are final
            )

        except Exception as e:
            print(f"Warning: Arbiter {self.name} failed: {e}, defaulting to reject")
            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                evaluator=f"{self.name} (ARBITER)",
                round=round_num,
                decision="reject",
                reasoning=f"[ARBITER] Arbitration failed: {e}",
                confidence=0.5
            )

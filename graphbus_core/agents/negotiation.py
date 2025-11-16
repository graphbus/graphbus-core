"""
Simple negotiation engine for Build Mode
"""

from typing import Dict, List, Optional
from graphbus_core.model.message import Proposal, ProposalEvaluation, CommitRecord, generate_id
from graphbus_core.agents.agent import LLMAgent
from graphbus_core.config import SafetyConfig


class NegotiationEngine:
    """
    Negotiation engine that manages proposal → evaluation → commit flow with safety guards.

    Features:
    - Multi-round negotiation with limits
    - Arbiter support for conflict resolution
    - Safety guardrails to prevent runaway negotiation
    - Proposal tracking per agent
    """

    def __init__(self, safety_config: Optional[SafetyConfig] = None, user_intent: Optional[str] = None):
        """
        Initialize negotiation engine.

        Args:
            safety_config: Safety configuration with limits and guardrails
            user_intent: User's goal or intent for the negotiation
        """
        self.safety_config = safety_config or SafetyConfig()
        self.user_intent = user_intent
        self.proposals: Dict[str, Proposal] = {}
        self.evaluations: Dict[str, List[ProposalEvaluation]] = {}
        self.commits: List[CommitRecord] = []
        self.current_round = 0
        self.proposal_counts: Dict[str, int] = {}  # Track proposals per agent
        self.rounds_without_proposals = 0  # Track convergence
        self.total_files_modified = 0  # Track total file changes

    def can_agent_propose(self, agent_name: str) -> tuple[bool, str]:
        """
        Check if agent can make more proposals based on safety limits.

        Args:
            agent_name: Name of the agent

        Returns:
            Tuple of (can_propose, reason)
        """
        # Check total proposals per agent
        count = self.proposal_counts.get(agent_name, 0)
        if count >= self.safety_config.max_proposals_per_agent:
            return False, f"Agent has reached max proposals ({self.safety_config.max_proposals_per_agent})"

        # Check max negotiation rounds
        if self.current_round >= self.safety_config.max_negotiation_rounds:
            return False, f"Max negotiation rounds reached ({self.safety_config.max_negotiation_rounds})"

        # Check convergence
        if self.rounds_without_proposals >= self.safety_config.convergence_threshold:
            return False, f"Negotiation has converged (no new proposals for {self.rounds_without_proposals} rounds)"

        return True, ""

    def add_proposal(self, proposal: Proposal) -> bool:
        """
        Add a proposal to the negotiation with safety checks.

        Args:
            proposal: Proposal from an agent

        Returns:
            True if proposal was added, False if rejected by safety guards
        """
        # Check if agent can propose
        can_propose, reason = self.can_agent_propose(proposal.src)
        if not can_propose:
            print(f"  [Negotiation] Proposal from {proposal.src} rejected: {reason}")
            return False

        # Check protected files
        if proposal.code_change.file_path in self.safety_config.protected_files:
            print(f"  [Negotiation] Proposal rejected: {proposal.code_change.file_path} is protected")
            return False

        # Add proposal
        self.proposals[proposal.proposal_id] = proposal
        self.evaluations[proposal.proposal_id] = []
        self.proposal_counts[proposal.src] = self.proposal_counts.get(proposal.src, 0) + 1
        print(f"  [Negotiation] Proposal {proposal.proposal_id} from {proposal.src}: {proposal.intent}")
        return True

    def add_evaluation(self, evaluation: ProposalEvaluation) -> None:
        """
        Add an evaluation of a proposal.

        Args:
            evaluation: Evaluation from an agent
        """
        if evaluation.proposal_id in self.evaluations:
            self.evaluations[evaluation.proposal_id].append(evaluation)
            print(f"  [Negotiation] {evaluation.evaluator} evaluated {evaluation.proposal_id}: {evaluation.decision}")

    def evaluate_all_proposals(self, agents: Dict[str, LLMAgent]) -> None:
        """
        Have all agents evaluate all proposals.

        Args:
            agents: Dict of agent name -> LLMAgent
        """
        print("\n[Negotiation] Agents evaluating proposals...")

        for proposal_id, proposal in self.proposals.items():
            # Skip if already has evaluations
            if self.evaluations[proposal_id]:
                continue

            # Each agent evaluates the proposal
            for agent_name, agent in agents.items():
                # Skip if agent is the proposer
                if agent_name == proposal.src:
                    continue

                evaluation = agent.evaluate_proposal(proposal, self.current_round)
                self.add_evaluation(evaluation)

    def create_commits(self, agents: Dict[str, LLMAgent]) -> List[CommitRecord]:
        """
        Create commit records for accepted proposals with arbiter support.

        Logic:
        - If majority accept → create commit
        - If tie or conflict and arbiter required → invoke arbiter
        - Apply safety limits on file changes

        Args:
            agents: Dict of agent name -> LLMAgent (needed for arbitration)

        Returns:
            List of new commits
        """
        new_commits = []

        # Get arbiter agents if configured
        arbiter_agents = [a for a in agents.values() if a.is_arbiter]

        for proposal_id, proposal in self.proposals.items():
            evaluations = self.evaluations[proposal_id]

            if not evaluations:
                print(f"  [Negotiation] No evaluations for {proposal_id}, skipping")
                continue

            # Count accept vs reject (exclude arbiter evaluations from initial count)
            non_arbiter_evals = [e for e in evaluations if "(ARBITER)" not in e.evaluator]
            accepts = sum(1 for e in non_arbiter_evals if e.decision == "accept")
            rejects = sum(1 for e in non_arbiter_evals if e.decision == "reject")

            # Check if we need arbitration
            needs_arbitration = False
            if self.safety_config.require_arbiter_on_conflict:
                # Tie or close vote → need arbitration
                if accepts == rejects or abs(accepts - rejects) <= 1:
                    needs_arbitration = True

            decision = None
            if needs_arbitration and arbiter_agents:
                # Invoke arbiter
                arbiter = arbiter_agents[0]  # Use first arbiter
                print(f"  [Negotiation] Conflict detected for {proposal_id}, invoking arbiter {arbiter.name}")
                arbiter_eval = arbiter.arbitrate_conflict(proposal, non_arbiter_evals, self.current_round)
                self.evaluations[proposal_id].append(arbiter_eval)
                decision = arbiter_eval.decision
                evaluations = self.evaluations[proposal_id]  # Update with arbiter eval
            else:
                # Simple majority
                decision = "accept" if accepts > rejects else "reject"

            # Check safety limits before creating commit
            if decision == "accept":
                # Check total file changes limit
                if self.total_files_modified >= self.safety_config.max_total_file_changes:
                    print(f"  [Negotiation] ✗ Cannot create commit for {proposal_id}: max file changes reached ({self.safety_config.max_total_file_changes})")
                    continue

                # Create commit
                commit = CommitRecord(
                    commit_id=generate_id("commit_"),
                    proposal_id=proposal_id,
                    round=self.current_round,
                    proposer=proposal.src,
                    evaluators=[e.evaluator for e in evaluations],
                    consensus_type="arbiter" if needs_arbitration else ("majority" if rejects > 0 else "unanimous"),
                    resolution={
                        "file_path": proposal.code_change.file_path,
                        "target": proposal.code_change.target,
                        "old_code": proposal.code_change.old_code,
                        "new_code": proposal.code_change.new_code
                    },
                    files_modified=[proposal.code_change.file_path],
                    negotiation_log=[
                        {"type": "proposal", "data": proposal.to_dict()},
                        {"type": "evaluations", "data": [e.to_dict() for e in evaluations]}
                    ]
                )

                self.commits.append(commit)
                new_commits.append(commit)
                self.total_files_modified += 1

                print(f"  [Negotiation] ✓ Commit created for {proposal_id} ({accepts} accepts, {rejects} rejects)")
            else:
                print(f"  [Negotiation] ✗ Proposal {proposal_id} rejected ({accepts} accepts, {rejects} rejects)")

        return new_commits

    def get_all_commits(self) -> List[CommitRecord]:
        """Get all commits created during negotiation."""
        return self.commits

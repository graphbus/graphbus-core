"""
Async negotiation engine - parallel agent operations

Runs agent operations (proposal, evaluation, etc.) concurrently
instead of sequentially, then collates results for consensus.
"""

import asyncio
from typing import Dict, List, Optional, Callable
from graphbus_core.model.message import Proposal, ProposalEvaluation, CommitRecord
from graphbus_core.agents.agent import LLMAgent
from graphbus_core.config import SafetyConfig


class AsyncNegotiationEngine:
    """
    Async negotiation engine that manages proposal → evaluation → commit flow.

    Runs all agent operations in parallel:
    - All agents propose simultaneously (not sequentially)
    - All agents evaluate proposals in parallel
    - Results collated for quorum/consensus

    This dramatically speeds up negotiation rounds.
    """

    def __init__(self, safety_config: Optional[SafetyConfig] = None, user_intent: Optional[str] = None):
        """
        Initialize async negotiation engine.

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
        self.proposal_counts: Dict[str, int] = {}
        self.rounds_without_proposals = 0
        self.total_files_modified = 0
        self.reconciliation: Dict = {}
        self.log_callback: Optional[Callable[[str], None]] = None

    def _log(self, message: str) -> None:
        """Log message via callback or print."""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def can_agent_propose(self, agent_name: str) -> tuple[bool, str]:
        """Check if agent can make more proposals based on safety limits."""
        count = self.proposal_counts.get(agent_name, 0)
        if count >= self.safety_config.max_proposals_per_agent:
            return False, f"Agent has reached max proposals ({self.safety_config.max_proposals_per_agent})"

        if self.current_round >= self.safety_config.max_negotiation_rounds:
            return False, f"Max negotiation rounds reached ({self.safety_config.max_negotiation_rounds})"

        if self.rounds_without_proposals >= self.safety_config.convergence_threshold:
            return False, f"Negotiation has converged (no new proposals for {self.rounds_without_proposals} rounds)"

        return True, ""

    def add_proposal(self, proposal: Proposal) -> bool:
        """Add a proposal with safety checks."""
        can_propose, reason = self.can_agent_propose(proposal.src)
        if not can_propose:
            self._log(f"  [Negotiation] Proposal from {proposal.src} rejected: {reason}")
            return False

        if proposal.code_change.file_path in self.safety_config.protected_files:
            self._log(f"  [Negotiation] Proposal rejected: {proposal.code_change.file_path} is protected")
            return False

        self.proposals[proposal.proposal_id] = proposal
        self.evaluations[proposal.proposal_id] = []
        self.proposal_counts[proposal.src] = self.proposal_counts.get(proposal.src, 0) + 1
        self._log(f"  [Negotiation] Proposal {proposal.proposal_id} from {proposal.src}: {proposal.intent}")
        return True

    def add_evaluation(self, evaluation: ProposalEvaluation) -> None:
        """Add an evaluation of a proposal."""
        if evaluation.proposal_id in self.evaluations:
            self.evaluations[evaluation.proposal_id].append(evaluation)
            self._log(f"  [Negotiation] {evaluation.evaluator} evaluated {evaluation.proposal_id}: {evaluation.decision}")

    async def evaluate_all_proposals_async(self, agents: Dict[str, LLMAgent]) -> None:
        """
        Have all agents evaluate all proposals IN PARALLEL.

        Instead of:
          for proposal in proposals:
              for agent in agents:
                  evaluate(proposal, agent)  # Sequential: O(N*M)

        Do:
          for proposal in proposals:
              await gather([evaluate(proposal, agent) for agent])  # Parallel: O(max(N,M))

        Args:
            agents: Dict of agent name -> LLMAgent
        """
        self._log("\n[Negotiation] Agents evaluating proposals in parallel...")

        # For each proposal, gather all evaluations in parallel
        tasks = []
        proposal_eval_map = {}

        for proposal_id, proposal in self.proposals.items():
            # Skip if already has evaluations
            if self.evaluations[proposal_id]:
                continue

            proposal_tasks = []
            for agent_name, agent in agents.items():
                # Skip if agent is the proposer
                if agent_name == proposal.src:
                    continue

                # Create async task for evaluation
                task = asyncio.create_task(
                    self._evaluate_proposal_async(agent, proposal, self.current_round)
                )
                proposal_tasks.append((proposal_id, agent_name, task))

            tasks.extend(proposal_tasks)

        # Wait for all evaluations to complete in parallel
        if tasks:
            for proposal_id, agent_name, task in tasks:
                try:
                    evaluation = await task
                    self.add_evaluation(evaluation)
                except Exception as e:
                    self._log(f"  [Negotiation] Error evaluating proposal {proposal_id}: {e}")

    async def _evaluate_proposal_async(self, agent: LLMAgent, proposal: Proposal, round_num: int) -> ProposalEvaluation:
        """
        Evaluate a proposal (runs in thread pool to avoid blocking).

        Args:
            agent: Agent performing evaluation
            proposal: Proposal to evaluate
            round_num: Negotiation round

        Returns:
            ProposalEvaluation
        """
        # Run synchronous evaluation in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            agent.evaluate_proposal,
            proposal,
            round_num
        )

    async def propose_all_agents_async(self, agents: Dict[str, LLMAgent], user_intent: Optional[str] = None) -> None:
        """
        Have all agents propose improvements IN PARALLEL.

        All agents analyze and propose simultaneously instead of sequentially.

        Args:
            agents: Dict of agent name -> LLMAgent
            user_intent: Optional user intent to guide proposals
        """
        self._log("\n[Orchestrator] Running proposal phase (parallel)...")

        tasks = []
        for agent_name, agent in agents.items():
            task = asyncio.create_task(
                self._propose_agent_async(agent_name, agent, user_intent)
            )
            tasks.append((agent_name, task))

        # Wait for all proposals to complete in parallel
        if tasks:
            for agent_name, task in tasks:
                try:
                    proposal = await task
                    if proposal:
                        self.add_proposal(proposal)
                except Exception as e:
                    self._log(f"  [Orchestrator] Proposal from {agent_name} failed: {e}")

    async def _propose_agent_async(self, agent_name: str, agent: LLMAgent, user_intent: Optional[str]) -> Optional[Proposal]:
        """
        Get proposal from single agent (runs in thread pool).

        Args:
            agent_name: Name of agent
            agent: LLMAgent instance
            user_intent: Optional user intent

        Returns:
            Proposal or None
        """
        loop = asyncio.get_event_loop()

        # Run synchronous operations in thread pool
        analysis = await loop.run_in_executor(
            None,
            agent.analyze_code,
            user_intent
        )

        improvements = analysis.get("potential_improvements", [])

        if not improvements:
            self._log(f"  {agent_name}: No improvements proposed")
            return None

        improvement = improvements[0] if improvements else None
        if improvement:
            self._log(f"  {agent_name}: Proposing '{improvement}' (parallel)...")
            proposal = await loop.run_in_executor(
                None,
                agent.propose_improvement,
                improvement,
                self.current_round,
                user_intent
            )
            return proposal

        return None

    def create_commits(self, agents: Dict[str, LLMAgent]) -> List[CommitRecord]:
        """
        Create commit records for accepted proposals with arbiter support.

        Note: This remains synchronous as it's the consensus/quorum phase.

        Args:
            agents: Dict of agent name -> LLMAgent

        Returns:
            List of new commits
        """
        new_commits = []
        arbiter_agents = [a for a in agents.values() if a.is_arbiter]

        for proposal_id, proposal in self.proposals.items():
            # Check if already committed
            if any(c.proposal_id == proposal_id for c in self.commits):
                continue

            evaluations = self.evaluations.get(proposal_id, [])
            if not evaluations:
                continue

            # Count votes
            accepts = sum(1 for e in evaluations if e.decision == "accept")
            rejects = sum(1 for e in evaluations if e.decision == "reject")
            total_votes = len(evaluations)

            # Require majority acceptance
            if accepts > rejects:
                # Create commit
                commit = CommitRecord(
                    proposal_id=proposal_id,
                    proposer=proposal.src,
                    round=self.current_round,
                    code_changes=[proposal.code_change],
                    consensus_type="majority_accept",
                    consensus_ratio=f"{accepts}/{total_votes}"
                )

                new_commits.append(commit)
                self.commits.append(commit)
                self.total_files_modified += 1
                self._log(f"  [Negotiation] COMMITTED {proposal_id}: {accepts}/{total_votes} votes")

        return new_commits

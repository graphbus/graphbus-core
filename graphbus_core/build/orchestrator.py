"""
Agent orchestrator - activates agents and runs negotiation
"""

from typing import Dict, List
from graphbus_core.model.agent_def import AgentDefinition
from graphbus_core.model.graph import AgentGraph
from graphbus_core.agents.llm_client import LLMClient
from graphbus_core.agents.agent import LLMAgent
from graphbus_core.agents.negotiation import NegotiationEngine
from graphbus_core.build.code_writer import CodeWriter
from graphbus_core.model.message import CommitRecord
from graphbus_core.config import SafetyConfig


class AgentOrchestrator:
    """
    Orchestrates agent activation and multi-round negotiation in Build Mode.

    Features:
    - Activates agents in topological order
    - Multi-round negotiation with safety guards
    - Arbiter support for conflict resolution
    - Convergence detection
    """

    def __init__(
        self,
        agent_definitions: List[AgentDefinition],
        agent_graph: AgentGraph,
        llm_client: LLMClient,
        safety_config: SafetyConfig = None,
        user_intent: str = None
    ):
        """
        Initialize orchestrator.

        Args:
            agent_definitions: List of all agent definitions
            agent_graph: Agent dependency graph
            llm_client: LLM client for agents
            safety_config: Safety configuration with limits
            user_intent: User's goal or intent for the negotiation
        """
        self.agent_definitions = {a.name: a for a in agent_definitions}
        self.agent_graph = agent_graph
        self.llm_client = llm_client
        self.safety_config = safety_config or SafetyConfig()
        self.user_intent = user_intent

        self.agents: Dict[str, LLMAgent] = {}
        self.negotiation_engine = NegotiationEngine(safety_config=self.safety_config, user_intent=user_intent)
        self.code_writer = CodeWriter(dry_run=False)

    def activate_agents(self) -> None:
        """
        Activate all agents (instantiate LLM agents).
        """
        print("\n[Orchestrator] Activating agents...")

        # Get activation order from topological sort
        activation_order = self.agent_graph.get_agent_activation_order()

        for agent_name in activation_order:
            if agent_name in self.agent_definitions:
                agent_def = self.agent_definitions[agent_name]
                agent = LLMAgent(
                    agent_def=agent_def,
                    llm_client=self.llm_client
                )
                self.agents[agent_name] = agent
                print(f"  ✓ Activated {agent_name}")

        print(f"[Orchestrator] {len(self.agents)} agents activated")

    def run_analysis_phase(self) -> None:
        """
        Each agent analyzes its own code.
        Includes intent relevance and code size checks.
        """
        print("\n[Orchestrator] Running analysis phase...")
        if self.user_intent:
            print(f"[Orchestrator] User intent: {self.user_intent}")

        intent_relevance_results = {}
        code_size_results = {}

        for agent_name, agent in self.agents.items():
            print(f"  Analyzing {agent_name}...")

            # Check intent relevance if user intent is provided
            if self.user_intent:
                try:
                    relevance = agent.check_intent_relevance(self.user_intent)
                    intent_relevance_results[agent_name] = relevance
                    if relevance.get("relevant", False):
                        print(f"    ✓ Intent relevant (confidence: {relevance.get('confidence', 0):.2f})")
                        print(f"      Reason: {relevance.get('reasoning', 'N/A')}")
                    else:
                        print(f"    ✗ Intent NOT relevant (confidence: {relevance.get('confidence', 0):.2f})")
                        print(f"      Reason: {relevance.get('reasoning', 'N/A')}")
                except Exception as e:
                    print(f"    Warning: Intent relevance check failed: {e}")

            # Check code size
            try:
                size_check = agent.check_code_size()
                code_size_results[agent_name] = size_check
                if size_check.get("exceeds_threshold", False):
                    print(f"    ⚠ Code size exceeds 100 lines ({size_check.get('line_count')} lines)")
                    suggestions = size_check.get("suggestions", [])
                    if suggestions:
                        print(f"      Refactoring suggestions:")
                        for sugg in suggestions[:2]:  # Show first 2
                            print(f"        - {sugg}")
                    new_agents = size_check.get("potential_new_agents", [])
                    if new_agents:
                        print(f"      Potential new agents:")
                        for new_agent in new_agents[:2]:
                            print(f"        - {new_agent.get('name')}: {new_agent.get('responsibility')}")
            except Exception as e:
                print(f"    Warning: Code size check failed: {e}")

            # Regular code analysis
            try:
                analysis = agent.analyze_code(user_intent=self.user_intent)
                improvements = analysis.get("potential_improvements", [])
                if improvements:
                    print(f"    Found {len(improvements)} potential improvements:")
                    for imp in improvements[:3]:  # Show first 3
                        print(f"      - {imp}")
            except Exception as e:
                print(f"    Warning: Analysis failed: {e}")

        # Store results in orchestrator for later use
        self.intent_relevance_results = intent_relevance_results
        self.code_size_results = code_size_results

        # Check if no agent found the intent relevant
        if self.user_intent and intent_relevance_results:
            relevant_agents = [name for name, result in intent_relevance_results.items()
                             if result.get("relevant", False)]
            if not relevant_agents:
                print("\n[Orchestrator] ⚠ WARNING: No agent found the intent relevant!")
                print("[Orchestrator] This may indicate a need for a NEW AGENT to handle this intent.")
                print(f"[Orchestrator] Intent: {self.user_intent}")
                print("[Orchestrator] Consider creating a new agent with this responsibility.")

    def run_proposal_phase(self) -> None:
        """
        Each agent proposes improvements based on its analysis.
        """
        print("\n[Orchestrator] Running proposal phase...")

        for agent_name, agent in self.agents.items():
            # Get analysis from memory
            analysis = agent.memory.retrieve("code_analysis", {})
            improvements = analysis.get("potential_improvements", [])

            if not improvements:
                print(f"  {agent_name}: No improvements proposed")
                continue

            # Propose first improvement (keep it minimal)
            improvement = improvements[0] if improvements else None
            if improvement:
                print(f"  {agent_name}: Proposing '{improvement}'...")
                try:
                    proposal = agent.propose_improvement(improvement, round_num=0, user_intent=self.user_intent)
                    if proposal:
                        self.negotiation_engine.add_proposal(proposal)
                except Exception as e:
                    print(f"    Warning: Proposal failed: {e}")

    def run_reconciliation_phase(self) -> dict:
        """
        Arbiter reconciles all proposals holistically before individual evaluations.

        This phase allows the arbiter to:
        - Review all proposals together
        - Identify conflicts or overlaps
        - Provide priority and guidance
        - Recommend which proposals should proceed

        Returns:
            Reconciliation data with recommendations
        """
        print("\n[Orchestrator] Running reconciliation phase...")

        # Get all proposals
        proposals = list(self.negotiation_engine.proposals.values())

        if not proposals:
            print("[Orchestrator] No proposals to reconcile")
            return {}

        # Find arbiter agent
        arbiter_agents = [a for a in self.agents.values() if a.is_arbiter]

        if not arbiter_agents:
            print("[Orchestrator] No arbiter configured, skipping reconciliation")
            return {}

        arbiter = arbiter_agents[0]
        print(f"[Orchestrator] Arbiter {arbiter.name} reconciling {len(proposals)} proposals...")

        try:
            reconciliation = arbiter.reconcile_all_proposals(proposals, user_intent=self.user_intent)

            # Display reconciliation results
            print(f"\n[Orchestrator] Reconciliation complete:")
            print(f"  Overall: {reconciliation.get('overall_assessment', 'N/A')}")

            conflicts = reconciliation.get('conflicts', [])
            if conflicts:
                print(f"\n  Conflicts identified ({len(conflicts)}):")
                for conflict in conflicts:
                    print(f"    - {conflict.get('issue', 'N/A')}")
                    print(f"      Proposals: {conflict.get('proposals', [])}")

            recommendations = reconciliation.get('recommendations', {})
            if recommendations:
                print(f"\n  Recommendations:")
                for prop_id, rec in recommendations.items():
                    action = rec.get('action', 'proceed')
                    priority = rec.get('priority', 3)
                    reasoning = rec.get('reasoning', 'N/A')

                    symbol = "✓" if action == "proceed" else ("⚠" if action == "modify" else "✗")
                    print(f"    {symbol} {prop_id}: {action.upper()} (priority: {priority})")
                    print(f"       {reasoning}")

            modifications = reconciliation.get('suggested_modifications', [])
            if modifications:
                print(f"\n  Suggested modifications ({len(modifications)}):")
                for mod in modifications:
                    print(f"    - {mod.get('proposal', 'N/A')}: {mod.get('suggestion', 'N/A')}")

            # Store reconciliation in negotiation engine for later use
            self.negotiation_engine.reconciliation = reconciliation
            return reconciliation

        except Exception as e:
            print(f"[Orchestrator] Warning: Reconciliation failed: {e}")
            return {}

    def run_negotiation_round(self) -> List[CommitRecord]:
        """
        Run one round of negotiation:
        - Agents evaluate all proposals
        - Create commits for accepted proposals (with arbiter support)

        Returns:
            List of commits created
        """
        print(f"\n[Orchestrator] Running negotiation round {self.negotiation_engine.current_round}...")

        # Agents evaluate proposals
        self.negotiation_engine.evaluate_all_proposals(self.agents)

        # Create commits from accepted proposals (passes agents for arbitration)
        commits = self.negotiation_engine.create_commits(self.agents)

        print(f"[Orchestrator] Round {self.negotiation_engine.current_round}: {len(commits)} commits created")
        return commits

    def apply_code_changes(self, commits: List[CommitRecord]) -> List[str]:
        """
        Apply code changes from commits.

        Args:
            commits: List of commits to apply

        Returns:
            List of modified file paths
        """
        return self.code_writer.apply_commits(commits)

    def run(self) -> List[str]:
        """
        Run the full multi-round agent orchestration:
        1. Activate agents
        2. Initial analysis phase
        3. Multi-round negotiation loop:
           - Proposal phase
           - Evaluation phase
           - Commit creation (with arbitration)
           - Apply changes
           - Check convergence
        4. Return modified files

        Returns:
            List of modified file paths
        """
        print("\n" + "="*60)
        print("AGENT ORCHESTRATION - BUILD MODE")
        if self.user_intent:
            print(f"User Intent: {self.user_intent}")
        print(f"Safety: max_rounds={self.safety_config.max_negotiation_rounds}, ")
        print(f"        max_proposals_per_agent={self.safety_config.max_proposals_per_agent}")
        print(f"        arbiter_on_conflict={self.safety_config.require_arbiter_on_conflict}")
        print("="*60)

        # Stage 1: Activate agents
        self.activate_agents()

        # Stage 2: Initial analysis (all agents analyze their code once)
        self.run_analysis_phase()

        # Stage 3: Multi-round negotiation
        all_modified_files = []
        all_commits = []

        for round_num in range(self.safety_config.max_negotiation_rounds):
            self.negotiation_engine.current_round = round_num

            print(f"\n{'='*60}")
            print(f"NEGOTIATION ROUND {round_num + 1}/{self.safety_config.max_negotiation_rounds}")
            print(f"{'='*60}")

            # Proposals phase
            proposals_before = len(self.negotiation_engine.proposals)
            self.run_proposal_phase()
            proposals_after = len(self.negotiation_engine.proposals)
            new_proposals = proposals_after - proposals_before

            if new_proposals == 0:
                self.negotiation_engine.rounds_without_proposals += 1
                print(f"[Orchestrator] No new proposals in this round ({self.negotiation_engine.rounds_without_proposals}/{self.safety_config.convergence_threshold})")

                if self.negotiation_engine.rounds_without_proposals >= self.safety_config.convergence_threshold:
                    print(f"[Orchestrator] Convergence reached - stopping negotiation")
                    break
            else:
                self.negotiation_engine.rounds_without_proposals = 0

            # Reconciliation phase (if arbiter exists and new proposals were made)
            if new_proposals > 0:
                self.run_reconciliation_phase()

            # Negotiation & commits
            commits = self.run_negotiation_round()
            all_commits.extend(commits)

            # Apply changes
            if commits:
                modified_files = self.apply_code_changes(commits)
                all_modified_files.extend(modified_files)
            else:
                print("[Orchestrator] No commits to apply this round")

            # Check if we've hit file modification limits
            if self.negotiation_engine.total_files_modified >= self.safety_config.max_total_file_changes:
                print(f"[Orchestrator] Max file changes limit reached ({self.safety_config.max_total_file_changes}) - stopping")
                break

        print("\n" + "="*60)
        print(f"ORCHESTRATION COMPLETE")
        print(f"  Total rounds: {self.negotiation_engine.current_round + 1}")
        print(f"  Total commits: {len(all_commits)}")
        print(f"  Files modified: {len(set(all_modified_files))}")
        print("="*60)

        return list(set(all_modified_files))

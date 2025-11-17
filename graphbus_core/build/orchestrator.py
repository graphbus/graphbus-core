"""
Agent orchestrator - activates agents and runs negotiation
"""

from typing import Dict, List, Optional
from graphbus_core.model.agent_def import AgentDefinition
from graphbus_core.model.graph import AgentGraph
from graphbus_core.agents.llm_client import LLMClient
from graphbus_core.agents.agent import LLMAgent
from graphbus_core.agents.negotiation import NegotiationEngine
from graphbus_core.build.code_writer import CodeWriter
from graphbus_core.build.artifacts import BuildArtifacts
from graphbus_core.build.refactoring import RefactoringValidator
from graphbus_core.build.contract_validator import ContractValidator
from graphbus_core.build.negotiation_session import NegotiationSessionManager, GitWorkflowManager, NegotiationSession
from graphbus_core.model.message import CommitRecord
from graphbus_core.config import SafetyConfig, LLMConfig


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
        user_intent: str = None,
        project_root: str = ".",
        session: Optional[NegotiationSession] = None,
        enable_git_workflow: bool = True
    ):
        """
        Initialize orchestrator.

        Args:
            agent_definitions: List of all agent definitions
            agent_graph: Agent dependency graph
            llm_client: LLM client for agents
            safety_config: Safety configuration with limits
            user_intent: User's goal or intent for the negotiation
            project_root: Root directory of the project
            session: Optional pre-created negotiation session
            enable_git_workflow: Enable git branch/PR workflow
        """
        self.agent_definitions = {a.name: a for a in agent_definitions}
        self.agent_graph = agent_graph
        self.llm_client = llm_client
        self.safety_config = safety_config or SafetyConfig()
        self.user_intent = user_intent
        self.project_root = project_root
        self.enable_git_workflow = enable_git_workflow

        self.agents: Dict[str, LLMAgent] = {}
        self.negotiation_engine = NegotiationEngine(safety_config=self.safety_config, user_intent=user_intent)
        self.code_writer = CodeWriter(dry_run=False)
        self.refactoring_validator = RefactoringValidator()
        self.contract_validator = ContractValidator()

        # Git workflow integration
        self.session_manager = NegotiationSessionManager(project_root=project_root)
        self.git_workflow = GitWorkflowManager(project_root=project_root)
        self.session = session
        self.pr_feedback_context = None  # Will be populated if previous PR found

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
                # Build enhanced context with PR feedback if available
                analysis_context = self.user_intent
                if self.pr_feedback_context:
                    # Format PR feedback for agent
                    feedback_summary = "\n\nDeveloper Feedback from Previous PR:\n"
                    for comment in self.pr_feedback_context.get("comments", []):
                        feedback_summary += f"- {comment['author']}: {comment['body']}\n"
                    for review in self.pr_feedback_context.get("review_comments", []):
                        feedback_summary += f"- {review['author']} ({review['state']}): {review['body']}\n"

                    analysis_context = f"{self.user_intent}{feedback_summary}"

                analysis = agent.analyze_code(user_intent=analysis_context)
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

    def reload_agent_source_code(self, modified_files: List[str]) -> None:
        """
        Reload agent source code after modifications.

        This ensures agents see cumulative changes in subsequent rounds,
        preventing duplicate proposals.

        Args:
            modified_files: List of file paths that were modified
        """
        print(f"\n[Orchestrator] Reloading source code for modified agents...")

        for file_path in modified_files:
            # Find which agent owns this file
            for agent_name, agent in self.agents.items():
                if agent.agent_def.source_file == file_path:
                    try:
                        # Read updated source
                        with open(file_path, 'r', encoding='utf-8') as f:
                            new_source = f.read()

                        # Update agent definition
                        agent.agent_def.source_code = new_source
                        agent.code_line_count = len(new_source.split('\n'))

                        print(f"  ↻ Reloaded {agent_name} ({agent.code_line_count} lines)")

                    except Exception as e:
                        print(f"  Warning: Could not reload {agent_name}: {e}")

    def run_refactoring_validation_phase(self) -> None:
        """
        Validate code across all agents for refactoring opportunities.

        Detects:
        - Code duplication across agents
        - Methods that should be extracted to shared modules
        - Complexity violations
        """
        print("\n[Orchestrator] Running refactoring validation...")

        # Collect all agent source code
        agent_sources = {
            agent_name: agent.agent_def.source_code
            for agent_name, agent in self.agents.items()
        }

        # Detect duplication across agents
        duplications = self.refactoring_validator.detect_duplication_across_agents(agent_sources)

        if duplications:
            print(f"\n[Orchestrator] ⚠️  Found {len(duplications)} code duplications:")
            for dup in duplications:
                print(f"  • {dup['method_name']} duplicated in {dup['agent1']} and {dup['agent2']}")
                print(f"    Similarity: {dup['similarity']:.0%}, Lines: {dup['lines']}")

            # Get extraction suggestions
            suggestions = self.refactoring_validator.suggest_extraction(duplications)

            if suggestions:
                print(f"\n[Orchestrator] 💡 Refactoring suggestions:")
                for suggestion in suggestions:
                    print(f"  • Extract {suggestion['method_name']} → {suggestion['suggested_module']}.py")
                    print(f"    Affects: {', '.join(suggestion['affected_agents'])}")
        else:
            print("[Orchestrator] ✓ No code duplication detected")

        # Validate individual agent code
        for agent_name, agent in self.agents.items():
            validation = self.refactoring_validator.validate_source_code(
                agent.agent_def.source_code,
                agent_name
            )

            if validation['violations']:
                print(f"\n[Orchestrator] ⚠️  {agent_name} refactoring issues:")
                for violation in validation['violations']:
                    print(f"    - {violation}")

            if validation['suggestions']:
                print(f"  💡 Suggestions:")
                for suggestion in validation['suggestions']:
                    print(f"    - {suggestion}")

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

        # Stage 0: Git workflow setup (if enabled)
        if self.enable_git_workflow:
            # Check for previous PR sessions with related context
            if self.user_intent:
                intent_keywords = self.user_intent.split()[:3]  # Use first 3 words as keywords
                previous_session = self.session_manager.get_latest_session_with_pr(intent_keywords)

                if previous_session:
                    print(f"\n[Context] Found previous session: {previous_session.session_id}")
                    print(f"  PR: {previous_session.pr_url}")
                    print(f"  Retrieving developer feedback...")

                    self.pr_feedback_context = self.session_manager.get_pr_feedback_context(
                        previous_session.session_id,
                        self.git_workflow
                    )

                    if self.pr_feedback_context and (self.pr_feedback_context.get("comments") or self.pr_feedback_context.get("review_comments")):
                        comment_count = len(self.pr_feedback_context.get("comments", []))
                        review_count = len(self.pr_feedback_context.get("review_comments", []))
                        print(f"  ✓ Retrieved {comment_count} comments, {review_count} reviews")
                        print(f"  Agents will use this feedback during analysis")
                    else:
                        print(f"  No feedback found on previous PR")
                        self.pr_feedback_context = None

            # Create session if not provided
            if not self.session:
                intent = self.user_intent or "Agent-driven code improvements"
                self.session = self.session_manager.create_session(intent)

            # Create feature branch
            original_branch = self.git_workflow.get_current_branch()
            success = self.git_workflow.create_branch(self.session.branch_name, from_branch=original_branch)
            if not success:
                print(f"  ⚠️  Warning: Could not create git branch, continuing without git workflow")
                self.enable_git_workflow = False

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

                # Record commits in session
                if self.enable_git_workflow and self.session:
                    for commit in commits:
                        self.session_manager.record_commit(self.session.session_id, commit.to_dict())

                # Commit to git branch
                if self.enable_git_workflow and modified_files:
                    commit_msg = f"Round {round_num + 1}: Apply {len(commits)} agent proposals\n\n"
                    if self.user_intent:
                        commit_msg += f"Intent: {self.user_intent}\n\n"
                    commit_msg += f"- {len(modified_files)} files modified\n"
                    commit_msg += f"- {len(commits)} commits applied"

                    success = self.git_workflow.commit_changes(modified_files, commit_msg)
                    if success:
                        self.session_manager.update_session(
                            self.session.session_id,
                            modified_files=list(set(all_modified_files))
                        )

                # Reload agent source code for next round
                self.reload_agent_source_code(modified_files)

                # Run refactoring validation after changes
                self.run_refactoring_validation_phase()
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

        # Stage 4: Create pull request (if git workflow enabled and changes were made)
        if self.enable_git_workflow and self.session and all_modified_files:
            # Push branch
            push_success = self.git_workflow.push_branch(self.session.branch_name)

            if push_success:
                # Create PR
                pr_title = self.user_intent or "Agent-driven code improvements"
                pr_body = self._generate_pr_description(all_commits, all_modified_files)

                pr_info = self.git_workflow.create_pr(
                    branch_name=self.session.branch_name,
                    title=pr_title,
                    body=pr_body
                )

                if pr_info:
                    # Update session with PR info
                    self.session_manager.update_session(
                        self.session.session_id,
                        pr_number=pr_info['number'],
                        pr_url=pr_info['url'],
                        status="pr_created"
                    )
                    print(f"\n✓ Pull request created: {pr_info['url']}")
                    print(f"  Session ID: {self.session.session_id}")
                    print(f"  Tracked in: .graphbus/negotiations/{self.session.session_id}/")

        return list(set(all_modified_files))

    def _generate_pr_description(self, commits: List[CommitRecord], modified_files: List[str]) -> str:
        """Generate PR description from negotiation results"""
        description = "# Agent Negotiation Results\n\n"

        if self.user_intent:
            description += f"## Intent\n{self.user_intent}\n\n"

        description += f"## Summary\n"
        description += f"- **Rounds completed**: {self.negotiation_engine.current_round + 1}\n"
        description += f"- **Commits applied**: {len(commits)}\n"
        description += f"- **Files modified**: {len(set(modified_files))}\n\n"

        description += f"## Modified Files\n"
        for file_path in sorted(set(modified_files)):
            description += f"- `{file_path}`\n"

        description += f"\n## Negotiation Details\n"
        description += f"This PR was created by GraphBus Build Mode agent negotiation.\n"
        description += f"Session ID: `{self.session.session_id if self.session else 'N/A'}`\n\n"

        description += f"### Commit Breakdown\n"
        for i, commit in enumerate(commits[:10], 1):  # Show first 10 commits
            description += f"{i}. **{commit.proposer}**: {commit.proposal_id} ({commit.consensus_type})\n"

        if len(commits) > 10:
            description += f"\n_...and {len(commits) - 10} more commits_\n"

        description += f"\n---\n"
        description += f"🤖 Generated with [GraphBus](https://github.com/graphbusio/graphbus)\n"

        return description


def run_negotiation(
    artifacts_dir: str,
    llm_config: LLMConfig,
    safety_config: SafetyConfig,
    user_intent: str = None,
    verbose: bool = False,
    project_root: str = ".",
    enable_git_workflow: bool = True
) -> dict:
    """
    Run negotiation on existing build artifacts.

    This is a standalone function that can be called by the negotiate command
    to run agent negotiation without rebuilding the project.

    IMPORTANT: Creates a fresh AgentOrchestrator and NegotiationEngine for
    each call, ensuring all counters (total_files_modified, proposal_counts, etc.)
    reset to 0 for each negotiation session.

    Args:
        artifacts_dir: Path to .graphbus artifacts directory
        llm_config: LLM configuration
        safety_config: Safety configuration (max_total_file_changes defaults to 10)
        user_intent: Optional user intent/goal
        verbose: Enable verbose output
        project_root: Root directory of the project (for .graphbus/ and git)
        enable_git_workflow: Enable git branch/PR workflow

    Returns:
        Dict with negotiation results
    """
    print(f"\n[Negotiation] Loading artifacts from {artifacts_dir}...")

    # Load artifacts
    try:
        artifacts = BuildArtifacts.load(artifacts_dir)
    except Exception as e:
        raise ValueError(f"Failed to load artifacts: {e}")

    print(f"[Negotiation] Loaded {len(artifacts.agents)} agents")
    for agent in artifacts.agents:
        print(f"  - {agent.name}")

    # Create LLM client
    llm_client = LLMClient(
        model=llm_config.model,
        api_key=llm_config.api_key
    )

    # Create orchestrator (fresh instance with counters at 0)
    orchestrator = AgentOrchestrator(
        agent_definitions=artifacts.agents,
        agent_graph=artifacts.graph,
        llm_client=llm_client,
        safety_config=safety_config,
        user_intent=user_intent,
        project_root=project_root,
        enable_git_workflow=enable_git_workflow
    )

    print(f"[Negotiation] Safety limits: max_file_changes={safety_config.max_total_file_changes}, max_rounds={safety_config.max_negotiation_rounds}")
    print(f"[Negotiation] Counters initialized: files_modified=0, proposals=0")
    if enable_git_workflow:
        print(f"[Negotiation] Git workflow: enabled (branch + PR)")

    # Run orchestration
    modified_files = orchestrator.run()

    # Save updated artifacts with new negotiations
    artifacts.negotiations = orchestrator.negotiation_engine.get_all_commits()
    artifacts.modified_files = modified_files
    artifacts.save(artifacts_dir)

    # Return results
    result = {
        "rounds_completed": orchestrator.negotiation_engine.current_round + 1,
        "total_proposals": len(orchestrator.negotiation_engine.proposals),
        "accepted_proposals": len(artifacts.negotiations),
        "files_changed": len(set(modified_files)),
        "modified_files": modified_files,
        "negotiations": artifacts.negotiations
    }

    # Add session info if git workflow was used
    if orchestrator.session:
        result["session"] = {
            "session_id": orchestrator.session.session_id,
            "branch_name": orchestrator.session.branch_name,
            "pr_number": orchestrator.session.pr_number,
            "pr_url": orchestrator.session.pr_url,
            "status": orchestrator.session.status
        }

    return result

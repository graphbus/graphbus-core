"""
Negotiate command - Run agent negotiation on existing build artifacts
"""

import click
import json
from pathlib import Path

from graphbus_core.config import LLMConfig, SafetyConfig
from graphbus_core.constants import DEFAULT_LLM_MODEL
from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header
)
from graphbus_cli.utils.errors import BuildError
from graphbus_cli.utils.websocket import (
    start_websocket_server,
    stop_websocket_server,
    ask_question_sync,
    has_connected_clients,
    is_websocket_available
)


@click.command()
@click.argument('artifacts_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    '--rounds',
    type=int,
    default=5,
    help='Number of negotiation rounds to run (default: 5)'
)
@click.option(
    '--llm-model',
    type=str,
    default=DEFAULT_LLM_MODEL,
    help=f'LLM model for agent orchestration (default: {DEFAULT_LLM_MODEL})'
)
@click.option(
    '--llm-api-key',
    type=str,
    envvar='ANTHROPIC_API_KEY',
    help='LLM API key (or set ANTHROPIC_API_KEY env var)'
)
@click.option(
    '--max-proposals-per-agent',
    type=int,
    default=5,
    help='Maximum proposals per agent (default: 5)'
)
@click.option(
    '--convergence-threshold',
    type=int,
    default=2,
    help='Rounds without proposals before convergence (default: 2)'
)
@click.option(
    '--protected-files',
    type=str,
    multiple=True,
    help='Files that agents cannot modify (can specify multiple)'
)
@click.option(
    '--arbiter-agent',
    type=str,
    help='Agent name to use as arbiter for conflict resolution'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Verbose output'
)
@click.option(
    '--intent',
    type=str,
    help='User intent/goal for the negotiation (e.g., "optimize performance", "improve error handling")'
)
@click.option(
    '--no-git',
    is_flag=True,
    help='Disable git workflow (branch creation, PR)'
)
@click.option(
    '--project-root',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default='.',
    help='Project root directory (default: current directory)'
)
def negotiate(
    artifacts_dir: str,
    rounds: int,
    llm_model: str,
    llm_api_key: str,
    max_proposals_per_agent: int,
    convergence_threshold: int,
    protected_files: tuple,
    arbiter_agent: str,
    verbose: bool,
    intent: str,
    no_git: bool,
    project_root: str
):
    """
    Run LLM agent negotiation on existing build artifacts.

    \b
    This command runs agent negotiation on already-built artifacts, allowing
    agents to collaboratively improve the codebase through multi-round
    negotiation without rebuilding from scratch.

    \b
    Use Cases:
      - Re-run negotiation with different parameters
      - Incremental improvements after initial build
      - Experiment with agent interactions
      - Iterate on improvements after manual code changes
      - Guide improvements with specific user intent

    \b
    Examples:
      graphbus negotiate .graphbus --rounds 5
      graphbus negotiate .graphbus --intent "optimize performance"
      graphbus negotiate .graphbus --intent "improve error handling" --arbiter-agent CoreAgent
      graphbus negotiate .graphbus --llm-model gpt-4-turbo
      graphbus negotiate .graphbus --rounds 3 --max-proposals-per-agent 3
      graphbus negotiate .graphbus --protected-files agents/core.py

    \b
    How It Works:
      1. Load agents from build artifacts
      2. Check for previous PR feedback (if intent matches)
      3. Create feature branch (graphbus/negotiate-<intent>-<id>)
      4. Activate agents as LLM agents
      5. Agents check intent relevance and code size
      6. Each agent analyzes code and proposes improvements
      7. Arbiter reconciles all proposals holistically (if configured)
      8. Agents evaluate each other's proposals
      9. Arbiter resolves conflicts if needed
      10. Accepted proposals are committed to branch
      11. Repeat for N rounds or until convergence
      12. Push branch and create pull request

    \b
    NEW: User Intent Integration
      Use --intent to guide agent improvements toward a specific goal.
      Agents will:
        - Check if intent is relevant to their scope
        - Focus improvements on the stated goal
        - Suggest new agents if intent doesn't match any existing agent

    \b
    NEW: Arbiter Reconciliation
      When an arbiter is configured, it reviews ALL proposals together:
        - Identifies conflicts before evaluation
        - Provides priority recommendations
        - Suggests modifications to align proposals
        - Ensures proposals work together harmoniously

    \b
    NEW: Git Workflow Integration
      By default, negotiation creates a feature branch and PR:
        - Creates branch: graphbus/negotiate-<intent-slug>-<uuid>
        - Commits each negotiation round to the branch
        - Pushes branch and creates PR with summary
        - PR includes commit breakdown and session tracking
        - Developer can review PR and add comments
        - Run negotiate again with same intent to incorporate feedback
        - Use --no-git to disable this workflow

    \b
    NEW: PR Feedback Integration
      When you run negotiate with an intent that matches a previous PR:
        - Retrieves comments and reviews from the PR
        - Agents analyze feedback from developers
        - Proposals incorporate developer suggestions
        - Enables iterative improvement based on human feedback

    \b
    Output:
      The negotiation process creates:
        - Feature branch with negotiation commits
        - Pull request for developer review
        - Session tracking in .graphbus/negotiations/<session-id>/
        - Source file changes (committed to branch)
        - .graphbus/negotiations.json with session index
    """
    try:
        # Start WebSocket server for UI communication (if available)
        websocket_server = None
        use_websocket = False
        if is_websocket_available():
            try:
                websocket_server = start_websocket_server(wait_for_client=False, timeout=2.0)
                if websocket_server and has_connected_clients():
                    print_info("UI connected via WebSocket - using graphical interface")
                    use_websocket = True
                elif websocket_server:
                    print_info("WebSocket server started (waiting for UI connection...)")
            except Exception as e:
                if verbose:
                    print_info(f"Note: Could not start WebSocket server: {e}")

        artifacts_path = Path(artifacts_dir).resolve()

        # Verify artifacts directory contains necessary files
        graphbus_dir = artifacts_path if artifacts_path.name == '.graphbus' else artifacts_path / '.graphbus'
        if not graphbus_dir.exists():
            raise BuildError(
                f"Artifacts directory not found: {graphbus_dir}\n"
                "Run 'graphbus build' first to create artifacts."
            )

        agents_json = graphbus_dir / 'agents.json'
        if not agents_json.exists():
            raise BuildError(
                f"agents.json not found in {graphbus_dir}\n"
                "The artifacts directory must contain a valid build."
            )

        # Display negotiation info
        print_header("GraphBus Agent Negotiation")
        print_info(f"Artifacts directory: {graphbus_dir}")
        print_info(f"LLM model: {llm_model}")
        print_info(f"Max rounds: {rounds}")
        print_info(f"Max proposals per agent: {max_proposals_per_agent}")
        if intent:
            print_info(f"User intent: {intent}")
        console.print()

        # Validate API key
        if not llm_api_key:
            raise BuildError(
                "LLM API key required for agent negotiation. "
                "Provide via --llm-api-key or ANTHROPIC_API_KEY environment variable."
            )

        # Create LLM config
        llm_config = LLMConfig(
            model=llm_model,
            api_key=llm_api_key
        )

        # Create safety config
        arbiter_list = [arbiter_agent] if arbiter_agent else []
        safety_config = SafetyConfig(
            max_negotiation_rounds=rounds,
            max_proposals_per_agent=max_proposals_per_agent,
            convergence_threshold=convergence_threshold,
            protected_files=list(protected_files),
            arbiter_agents=arbiter_list
        )

        # Collect clarifying questions from agents (if intent provided)
        enhanced_intent = intent
        if intent:
            print_info("Collecting clarifying questions from agents...")
            console.print()

            from graphbus_core.build.orchestrator import collect_agent_questions

            try:
                questions = collect_agent_questions(
                    artifacts_dir=str(graphbus_dir),
                    llm_config=llm_config,
                    user_intent=intent,
                    project_root=project_root
                )

                if questions:
                    console.print(f"\n[yellow]✨ Agents have {len(questions)} clarifying question(s)[/yellow]\n")

                    # Ask each question interactively
                    answers = []
                    for i, q in enumerate(questions, 1):
                        # Try WebSocket first if UI is connected
                        answer = None
                        if use_websocket and has_connected_clients():
                            try:
                                # Send question via WebSocket
                                options = q.get('options', [])
                                context = q.get('context')
                                question_text = f"[{q['agent']}] {q['question']}"

                                print_info(f"Waiting for UI response to question {i}/{len(questions)}...")
                                answer = ask_question_sync(
                                    question=question_text,
                                    options=options,
                                    context=context,
                                    timeout=300  # 5 minute timeout
                                )

                                if answer:
                                    print_success(f"✓ Received answer: {answer}")
                                else:
                                    print_info("No response from UI, falling back to CLI prompt")
                                    use_websocket = False  # Fall back for remaining questions
                            except Exception as e:
                                if verbose:
                                    print_info(f"WebSocket error: {e}, falling back to CLI")
                                use_websocket = False

                        # Fall back to CLI prompt if WebSocket not available or failed
                        if not answer:
                            console.print(f"[bold cyan]Question {i}/{len(questions)} from {q['agent']}:[/bold cyan]")
                            console.print(f"{q['question']}")

                            if q.get('context'):
                                console.print(f"[dim]Context: {q['context']}[/dim]")

                            console.print()
                            options = q.get('options', [])

                            # Display options
                            for idx, opt in enumerate(options, 1):
                                console.print(f"  {idx}. {opt}")

                            console.print()

                            # Get user choice
                            while True:
                                try:
                                    choice = click.prompt(
                                        "Your answer (enter number or custom text)",
                                        type=str,
                                        default="1"
                                    )

                                    # Try to parse as number
                                    try:
                                        choice_idx = int(choice) - 1
                                        if 0 <= choice_idx < len(options):
                                            answer = options[choice_idx]
                                        else:
                                            answer = choice
                                    except ValueError:
                                        answer = choice

                                    break
                                except (KeyboardInterrupt, click.Abort):
                                    console.print("\n[yellow]Skipping remaining questions...[/yellow]")
                                    break

                            console.print()

                        # Store answer if we got one
                        if answer:
                            answers.append({
                                "question": q['question'],
                                "answer": answer,
                                "agent": q['agent']
                            })

                    if answers:
                        # Enhance intent with answers
                        enhanced_intent = f"{intent}\n\nUser Clarifications:\n"
                        for a in answers:
                            enhanced_intent += f"- [{a['agent']}] {a['question']}\n  → {a['answer']}\n"

                        print_success(f"✓ Received {len(answers)} answer(s) - agents will use this context")
                        console.print()

            except Exception as e:
                if verbose:
                    print_info(f"Note: Could not collect questions: {e}")
                console.print()

        # Run negotiation
        print_info("Starting negotiation...")
        if not no_git:
            print_info("Git workflow: enabled (branch + PR will be created)")
        console.print()

        from graphbus_core.build.orchestrator import run_negotiation

        results = run_negotiation(
            artifacts_dir=str(graphbus_dir),
            llm_config=llm_config,
            safety_config=safety_config,
            user_intent=enhanced_intent,  # Use enhanced intent with answers
            verbose=verbose,
            project_root=project_root,
            enable_git_workflow=not no_git
        )

        _display_negotiation_summary(results)

    except Exception as e:
        console.print()
        raise BuildError(f"Negotiation failed: {str(e)}")
    finally:
        # Stop WebSocket server if it was started
        if websocket_server:
            stop_websocket_server()


def _display_negotiation_summary(results):
    """Display negotiation summary"""
    print_header("Negotiation Summary")

    num_rounds = results.get('rounds_completed', 0)
    num_proposals = results.get('total_proposals', 0)
    num_accepted = results.get('accepted_proposals', 0)
    num_files_changed = results.get('files_changed', 0)

    console.print(f"[cyan]Rounds completed:[/cyan] {num_rounds}")
    console.print(f"[cyan]Proposals made:[/cyan] {num_proposals}")
    console.print(f"[cyan]Proposals accepted:[/cyan] {num_accepted}")
    console.print(f"[cyan]Files modified:[/cyan] {num_files_changed}")

    # Display session/PR info if available
    session = results.get('session')
    if session:
        console.print()
        console.print(f"[cyan]Session ID:[/cyan] {session.get('session_id')}")
        console.print(f"[cyan]Branch:[/cyan] {session.get('branch_name')}")

        if session.get('pr_url'):
            console.print(f"[cyan]Pull Request:[/cyan] {session.get('pr_url')}")
            console.print(f"[cyan]PR Status:[/cyan] {session.get('status')}")
            console.print()
            print_success(f"Pull request created! Review at: {session.get('pr_url')}")
            console.print()
            console.print("[yellow]Next steps:[/yellow]")
            console.print("  1. Review the PR and add comments with feedback")
            console.print(f"  2. Run 'graphbus negotiate' again with the same intent to incorporate feedback")
            console.print(f"  3. Session tracked in: .graphbus/negotiations/{session.get('session_id')}/")

    console.print()

    if num_accepted > 0:
        print_success(f"Negotiation completed: {num_accepted} improvements applied")
    else:
        print_info("Negotiation completed: no changes proposed")

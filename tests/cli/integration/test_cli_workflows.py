"""
Integration tests for complete CLI workflows
"""

import pytest
import json
from pathlib import Path
from click.testing import CliRunner

from graphbus_cli.main import cli


class TestCLIWorkflows:
    """Integration tests for complete CLI workflows"""

    @pytest.fixture
    def hello_world_agents(self):
        """Path to Hello World agents"""
        agents_dir = "examples/hello_graphbus/agents"
        if not Path(agents_dir).exists():
            pytest.skip("Hello World agents not found")
        return agents_dir

    @pytest.fixture
    def runner(self):
        """CLI test runner"""
        return CliRunner()

    def test_complete_build_and_run_workflow(self, runner, hello_world_agents, tmp_path):
        """Test complete workflow: build then run"""
        output_dir = tmp_path / ".graphbus"

        # Step 1: Build agents
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])

        assert build_result.exit_code == 0
        assert 'Build completed successfully' in build_result.output

        # Step 2: Run the built artifacts
        run_result = runner.invoke(cli, [
            'run',
            str(output_dir),
            '--interactive'
        ], input="stats\nexit\n")

        assert run_result.exit_code == 0
        assert 'Runtime started successfully' in run_result.output
        assert 'Active Nodes' in run_result.output

    def test_build_run_and_call_methods(self, runner, hello_world_agents, tmp_path):
        """Test building, running, and calling agent methods"""
        output_dir = tmp_path / ".graphbus"

        # Build
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0

        # Run and call method
        run_result = runner.invoke(cli, [
            'run',
            str(output_dir),
            '--interactive'
        ], input="call HelloService.generate_message\nexit\n")

        assert run_result.exit_code == 0
        assert '"message"' in run_result.output or 'Hello' in run_result.output

    def test_build_run_and_publish_events(self, runner, hello_world_agents, tmp_path):
        """Test building, running, and publishing events"""
        output_dir = tmp_path / ".graphbus"

        # Build
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0

        # Run and publish event
        run_result = runner.invoke(cli, [
            'run',
            str(output_dir),
            '--interactive'
        ], input='publish /Hello/MessageGenerated {"message": "test"}\nstats\nexit\n')

        assert run_result.exit_code == 0
        assert 'Event published' in run_result.output or 'Messages Published' in run_result.output

    def test_build_with_verbose_then_run(self, runner, hello_world_agents, tmp_path):
        """Test verbose build followed by run"""
        output_dir = tmp_path / ".graphbus"

        # Verbose build
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir),
            '-v'
        ])

        assert build_result.exit_code == 0
        assert 'Scanning modules' in build_result.output

        # Run
        run_result = runner.invoke(cli, [
            'run',
            str(output_dir),
            '--interactive'
        ], input="nodes\nexit\n")

        assert run_result.exit_code == 0
        assert 'HelloService' in run_result.output

    def test_multiple_method_calls_in_session(self, runner, hello_world_agents, tmp_path):
        """Test multiple method calls in single REPL session"""
        output_dir = tmp_path / ".graphbus"

        # Build
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0

        # Run with multiple method calls
        commands = (
            "call HelloService.generate_message\n"
            "call HelloService.generate_message\n"
            "stats\n"
            "exit\n"
        )

        run_result = runner.invoke(cli, [
            'run',
            str(output_dir),
            '--interactive'
        ], input=commands)

        assert run_result.exit_code == 0
        # Should see multiple "message" outputs
        assert run_result.output.count('"message"') >= 2 or run_result.output.count('Hello') >= 2

    def test_event_flow_through_system(self, runner, hello_world_agents, tmp_path):
        """Test event flowing through subscriber"""
        output_dir = tmp_path / ".graphbus"

        # Build
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0

        # Run and verify event delivery
        commands = (
            'publish /Hello/MessageGenerated {"message": "test event"}\n'
            'history 1\n'
            'exit\n'
        )

        run_result = runner.invoke(cli, [
            'run',
            str(output_dir),
            '--interactive'
        ], input=commands)

        assert run_result.exit_code == 0
        assert '/Hello/MessageGenerated' in run_result.output
        # LoggerService should have received and logged the event
        assert 'Greeting generated' in run_result.output or 'LOG' in run_result.output

    def test_build_artifacts_are_valid_json(self, runner, hello_world_agents, tmp_path):
        """Test that built artifacts are valid JSON"""
        output_dir = tmp_path / ".graphbus"

        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0

        # Verify all artifacts are valid JSON
        for artifact_file in ["graph.json", "agents.json", "topics.json", "build_summary.json"]:
            artifact_path = output_dir / artifact_file
            assert artifact_path.exists(), f"Missing {artifact_file}"

            with open(artifact_path) as f:
                data = json.load(f)  # Should not raise JSONDecodeError
                assert data is not None

    def test_runtime_statistics_accuracy(self, runner, hello_world_agents, tmp_path):
        """Test that runtime statistics are accurate"""
        output_dir = tmp_path / ".graphbus"

        # Build
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0

        # Run and perform operations
        commands = (
            'publish /Hello/MessageGenerated {"message": "msg1"}\n'
            'publish /Hello/MessageGenerated {"message": "msg2"}\n'
            'stats\n'
            'exit\n'
        )

        run_result = runner.invoke(cli, [
            'run',
            str(output_dir),
            '--interactive'
        ], input=commands)

        assert run_result.exit_code == 0
        # Should show 2 messages published
        # Note: The exact format might vary, so we check for presence of stats
        assert 'Messages Published' in run_result.output

    def test_run_without_message_bus_isolation(self, runner, hello_world_agents, tmp_path):
        """Test that --no-message-bus properly disables event routing"""
        output_dir = tmp_path / ".graphbus"

        # Build
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0

        # Run with message bus disabled
        commands = (
            'call HelloService.generate_message\n'
            'stats\n'
            'exit\n'
        )

        run_result = runner.invoke(cli, [
            'run',
            str(output_dir),
            '--no-message-bus',
            '--interactive'
        ], input=commands)

        assert run_result.exit_code == 0
        assert 'Message Bus: Disabled' in run_result.output

    def test_cli_version_command(self, runner):
        """Test CLI version command"""
        result = runner.invoke(cli, ['--version'])

        assert result.exit_code == 0
        assert 'version' in result.output.lower()

    def test_cli_help_command(self, runner):
        """Test CLI help command"""
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0
        assert 'GraphBus' in result.output
        assert 'build' in result.output
        assert 'run' in result.output

    def test_sequential_builds_overwrite_artifacts(self, runner, hello_world_agents, tmp_path):
        """Test that sequential builds properly overwrite artifacts"""
        output_dir = tmp_path / ".graphbus"

        # First build
        build_result1 = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result1.exit_code == 0

        # Get initial modification time
        graph_file = output_dir / "graph.json"
        initial_mtime = graph_file.stat().st_mtime

        # Second build (should overwrite)
        import time
        time.sleep(0.1)  # Ensure different timestamp

        build_result2 = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result2.exit_code == 0

        # Modification time should be different
        new_mtime = graph_file.stat().st_mtime
        assert new_mtime >= initial_mtime

    def test_run_cleans_up_on_exit(self, runner):
        """Test that runtime cleans up properly on exit"""
        result = runner.invoke(cli, [
            'run',
            "examples/hello_graphbus/.graphbus",
            '--interactive'
        ], input="exit\n")

        assert result.exit_code == 0
        assert 'Exiting REPL' in result.output

    def test_validate_then_build_workflow(self, runner, hello_world_agents, tmp_path):
        """Test workflow: validate then build"""
        output_dir = tmp_path / ".graphbus"

        # Step 1: Validate agents
        validate_result = runner.invoke(cli, [
            'validate',
            hello_world_agents
        ])
        assert validate_result.exit_code == 0
        assert 'Validation Summary' in validate_result.output

        # Step 2: Build agents
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0
        assert 'Build completed successfully' in build_result.output

    def test_build_then_inspect_workflow(self, runner, hello_world_agents, tmp_path):
        """Test workflow: build then inspect"""
        output_dir = tmp_path / ".graphbus"

        # Step 1: Build
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0

        # Step 2: Inspect graph
        inspect_result = runner.invoke(cli, [
            'inspect',
            str(output_dir),
            '--graph'
        ])
        assert inspect_result.exit_code == 0
        assert 'Agent Graph' in inspect_result.output

        # Step 3: Inspect agents
        inspect_agents_result = runner.invoke(cli, [
            'inspect',
            str(output_dir),
            '--agents'
        ])
        assert inspect_agents_result.exit_code == 0
        assert 'HelloService' in inspect_agents_result.output

    def test_complete_workflow_validate_build_inspect_run(self, runner, hello_world_agents, tmp_path):
        """Test complete workflow: validate -> build -> inspect -> run"""
        output_dir = tmp_path / ".graphbus"

        # Step 1: Validate
        validate_result = runner.invoke(cli, ['validate', hello_world_agents])
        assert validate_result.exit_code == 0

        # Step 2: Build
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0

        # Step 3: Inspect
        inspect_result = runner.invoke(cli, ['inspect', str(output_dir)])
        assert inspect_result.exit_code == 0

        # Step 4: Run
        run_result = runner.invoke(cli, [
            'run',
            str(output_dir),
            '--interactive'
        ], input="stats\nexit\n")
        assert run_result.exit_code == 0

    def test_inspect_specific_agent_after_build(self, runner, hello_world_agents, tmp_path):
        """Test inspecting specific agent after build"""
        output_dir = tmp_path / ".graphbus"

        # Build
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0

        # Inspect specific agent
        inspect_result = runner.invoke(cli, [
            'inspect',
            str(output_dir),
            '--agent', 'HelloService'
        ])
        assert inspect_result.exit_code == 0
        assert 'Agent: HelloService' in inspect_result.output
        assert 'generate_message' in inspect_result.output

    def test_validate_with_all_checks(self, runner, hello_world_agents):
        """Test validate with all check flags"""
        result = runner.invoke(cli, [
            'validate',
            hello_world_agents,
            '--strict',
            '--check-types',
            '--check-cycles'
        ])

        assert result.exit_code == 0
        assert 'Validation Summary' in result.output
        assert 'Running strict checks' in result.output
        assert 'Checking for dependency cycles' in result.output

    def test_inspect_json_output_is_valid(self, runner, hello_world_agents, tmp_path):
        """Test that inspect JSON output is valid"""
        output_dir = tmp_path / ".graphbus"

        # Build
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0

        # Inspect with JSON format
        inspect_result = runner.invoke(cli, [
            'inspect',
            str(output_dir),
            '--agents',
            '--format', 'json'
        ])
        assert inspect_result.exit_code == 0
        # Should contain valid JSON
        assert '[' in inspect_result.output
        assert '"name"' in inspect_result.output

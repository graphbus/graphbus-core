"""
Functional tests for run command
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from graphbus_cli.main import cli


class TestRunCommand:
    """Functional tests for graphbus run command"""

    @pytest.fixture
    def hello_world_artifacts(self):
        """Path to Hello World artifacts"""
        artifacts_dir = "examples/hello_graphbus/.graphbus"
        if not Path(artifacts_dir).exists():
            pytest.skip("Hello World artifacts not found - run build first")
        return artifacts_dir

    @pytest.fixture
    def runner(self):
        """CLI test runner"""
        return CliRunner()

    def test_run_help(self, runner):
        """Test run command help"""
        result = runner.invoke(cli, ['run', '--help'])

        assert result.exit_code == 0
        assert 'Run agent graph' in result.output
        assert '--interactive' in result.output
        assert '--verbose' in result.output
        assert '--no-message-bus' in result.output

    def test_run_missing_artifacts(self, runner):
        """Test run with non-existent artifacts directory"""
        result = runner.invoke(cli, [
            'run',
            'nonexistent/.graphbus'
        ])

        assert result.exit_code != 0

    def test_run_interactive_basic_commands(self, runner, hello_world_artifacts):
        """Test run in interactive mode with basic commands"""
        # Simulate REPL input
        input_commands = "nodes\nstats\nexit\n"

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--interactive'
        ], input=input_commands)

        # Should complete successfully
        assert result.exit_code == 0
        assert 'Runtime started successfully' in result.output
        assert 'GraphBus Runtime REPL' in result.output

    def test_run_interactive_call_method(self, runner, hello_world_artifacts):
        """Test calling agent method in interactive mode"""
        input_commands = "call HelloService.generate_message\nexit\n"

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--interactive'
        ], input=input_commands)

        assert result.exit_code == 0
        # Check that method was called and returned result
        assert '"message"' in result.output or 'Hello' in result.output

    def test_run_interactive_list_nodes(self, runner, hello_world_artifacts):
        """Test listing nodes in interactive mode"""
        input_commands = "nodes\nexit\n"

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--interactive'
        ], input=input_commands)

        assert result.exit_code == 0
        assert 'HelloService' in result.output
        assert 'LoggerService' in result.output

    def test_run_interactive_show_stats(self, runner, hello_world_artifacts):
        """Test showing stats in interactive mode"""
        input_commands = "stats\nexit\n"

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--interactive'
        ], input=input_commands)

        assert result.exit_code == 0
        assert 'Active Nodes' in result.output or 'RUNNING' in result.output

    def test_run_interactive_list_topics(self, runner, hello_world_artifacts):
        """Test listing topics in interactive mode"""
        input_commands = "topics\nexit\n"

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--interactive'
        ], input=input_commands)

        assert result.exit_code == 0
        assert '/Hello/MessageGenerated' in result.output
        assert 'LoggerService' in result.output

    def test_run_interactive_publish_event(self, runner, hello_world_artifacts):
        """Test publishing event in interactive mode"""
        input_commands = 'publish /Hello/MessageGenerated {"message": "test"}\nstats\nexit\n'

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--interactive'
        ], input=input_commands)

        assert result.exit_code == 0
        assert 'Event published' in result.output or 'Messages Published' in result.output

    def test_run_interactive_history(self, runner, hello_world_artifacts):
        """Test showing message history in interactive mode"""
        input_commands = 'publish /Hello/MessageGenerated {"message": "test"}\nhistory 5\nexit\n'

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--interactive'
        ], input=input_commands)

        assert result.exit_code == 0
        # History should show the published message
        assert '/Hello/MessageGenerated' in result.output

    def test_run_interactive_help_command(self, runner, hello_world_artifacts):
        """Test help command in interactive mode"""
        input_commands = "help\nexit\n"

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--interactive'
        ], input=input_commands)

        assert result.exit_code == 0
        assert 'Available commands' in result.output
        assert 'call' in result.output
        assert 'publish' in result.output

    def test_run_with_no_message_bus(self, runner, hello_world_artifacts):
        """Test run with message bus disabled"""
        input_commands = "stats\nexit\n"

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--no-message-bus',
            '--interactive'
        ], input=input_commands)

        assert result.exit_code == 0
        assert 'Message Bus: Disabled' in result.output or 'Disabled' in result.output

    def test_run_with_verbose(self, runner, hello_world_artifacts):
        """Test run with verbose output"""
        input_commands = "exit\n"

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--verbose',
            '--interactive'
        ], input=input_commands)

        assert result.exit_code == 0
        # Verbose mode shows more details
        assert 'Runtime started successfully' in result.output

    def test_run_interactive_invalid_command(self, runner, hello_world_artifacts):
        """Test handling of invalid commands in REPL"""
        input_commands = "invalid_command\nexit\n"

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--interactive'
        ], input=input_commands)

        assert result.exit_code == 0
        # Should show error but not crash
        assert 'Unknown command' in result.output or 'exit' in result.output

    def test_run_interactive_call_invalid_method(self, runner, hello_world_artifacts):
        """Test calling non-existent method"""
        input_commands = "call HelloService.nonexistent\nexit\n"

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--interactive'
        ], input=input_commands)

        assert result.exit_code == 0
        # Should show error but continue running
        assert 'Error' in result.output or 'exit' in result.output

    def test_run_shows_runtime_status(self, runner, hello_world_artifacts):
        """Test that run shows runtime status on startup"""
        input_commands = "exit\n"

        result = runner.invoke(cli, [
            'run',
            hello_world_artifacts,
            '--interactive'
        ], input=input_commands)

        assert result.exit_code == 0
        assert 'Runtime Status' in result.output
        assert 'Agents:' in result.output
        assert 'HelloService' in result.output

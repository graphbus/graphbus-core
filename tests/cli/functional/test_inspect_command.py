"""
Functional tests for inspect command
"""

import pytest
import json
from pathlib import Path
from click.testing import CliRunner

from graphbus_cli.main import cli


class TestInspectCommand:
    """Functional tests for graphbus inspect command"""

    @pytest.fixture
    def hello_world_artifacts(self):
        """Path to Hello World artifacts"""
        artifacts_dir = "examples/hello_graphbus/.graphbus"
        if not Path(artifacts_dir).exists():
            pytest.skip("Hello World artifacts not found")
        return artifacts_dir

    @pytest.fixture
    def runner(self):
        """CLI test runner"""
        return CliRunner()

    def test_inspect_help(self, runner):
        """Test inspect command help"""
        result = runner.invoke(cli, ['inspect', '--help'])

        assert result.exit_code == 0
        assert 'Inspect build artifacts' in result.output
        assert '--graph' in result.output
        assert '--agents' in result.output
        assert '--topics' in result.output
        assert '--format' in result.output

    def test_inspect_default_shows_graph(self, runner, hello_world_artifacts):
        """Test that inspect shows graph by default"""
        result = runner.invoke(cli, ['inspect', hello_world_artifacts])

        assert result.exit_code == 0
        assert 'Agent Graph' in result.output
        assert 'Nodes:' in result.output
        assert 'Edges:' in result.output

    def test_inspect_agents_list(self, runner, hello_world_artifacts):
        """Test inspect with --agents flag"""
        result = runner.invoke(cli, ['inspect', hello_world_artifacts, '--agents'])

        assert result.exit_code == 0
        assert 'Agents' in result.output
        assert 'HelloService' in result.output
        assert 'LoggerService' in result.output
        assert 'PrinterService' in result.output

    def test_inspect_topics_list(self, runner, hello_world_artifacts):
        """Test inspect with --topics flag"""
        result = runner.invoke(cli, ['inspect', hello_world_artifacts, '--topics'])

        assert result.exit_code == 0
        assert 'Topics' in result.output
        assert '/Hello/MessageGenerated' in result.output

    def test_inspect_subscriptions(self, runner, hello_world_artifacts):
        """Test inspect with --subscriptions flag"""
        result = runner.invoke(cli, ['inspect', hello_world_artifacts, '--subscriptions'])

        assert result.exit_code == 0
        assert 'Subscription Mappings' in result.output
        assert 'LoggerService' in result.output
        assert 'on_message_generated' in result.output

    def test_inspect_specific_agent(self, runner, hello_world_artifacts):
        """Test inspect with specific agent"""
        result = runner.invoke(cli, [
            'inspect',
            hello_world_artifacts,
            '--agent', 'HelloService'
        ])

        assert result.exit_code == 0
        assert 'Agent: HelloService' in result.output
        assert 'Module:' in result.output
        assert 'Class:' in result.output

    def test_inspect_json_format(self, runner, hello_world_artifacts):
        """Test inspect with JSON output"""
        result = runner.invoke(cli, [
            'inspect',
            hello_world_artifacts,
            '--agents',
            '--format', 'json'
        ])

        assert result.exit_code == 0
        # Parse JSON to verify it's valid
        # Skip the header lines
        lines = result.output.split('\n')
        json_start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('['):
                json_start = i
                break
        json_output = '\n'.join(lines[json_start:])
        data = json.loads(json_output)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_inspect_yaml_format(self, runner, hello_world_artifacts):
        """Test inspect with YAML output"""
        result = runner.invoke(cli, [
            'inspect',
            hello_world_artifacts,
            '--agents',
            '--format', 'yaml'
        ])

        assert result.exit_code == 0
        assert 'name:' in result.output

    def test_inspect_missing_directory(self, runner):
        """Test inspect with non-existent directory"""
        result = runner.invoke(cli, [
            'inspect',
            'nonexistent/path'
        ])

        assert result.exit_code != 0

    def test_inspect_invalid_agent_name(self, runner, hello_world_artifacts):
        """Test inspect with invalid agent name"""
        result = runner.invoke(cli, [
            'inspect',
            hello_world_artifacts,
            '--agent', 'NonExistentAgent'
        ])

        assert result.exit_code == 0  # Should not crash
        assert 'not found' in result.output

    def test_inspect_graph_shows_dependencies(self, runner, hello_world_artifacts):
        """Test that graph inspection shows dependencies"""
        result = runner.invoke(cli, ['inspect', hello_world_artifacts, '--graph'])

        assert result.exit_code == 0
        assert 'Agent Nodes:' in result.output

    def test_inspect_multiple_flags(self, runner, hello_world_artifacts):
        """Test inspect with multiple flags"""
        result = runner.invoke(cli, [
            'inspect',
            hello_world_artifacts,
            '--agents',
            '--topics'
        ])

        assert result.exit_code == 0
        assert 'Agents' in result.output
        assert 'Topics' in result.output

    def test_inspect_agent_details_shows_methods(self, runner, hello_world_artifacts):
        """Test that agent details show methods"""
        result = runner.invoke(cli, [
            'inspect',
            hello_world_artifacts,
            '--agent', 'HelloService'
        ])

        assert result.exit_code == 0
        assert 'Methods:' in result.output

    def test_inspect_agent_details_shows_subscriptions(self, runner, hello_world_artifacts):
        """Test that agent details show subscriptions"""
        result = runner.invoke(cli, [
            'inspect',
            hello_world_artifacts,
            '--agent', 'LoggerService'
        ])

        assert result.exit_code == 0
        assert 'Subscribes To:' in result.output

    def test_inspect_topics_json_format(self, runner, hello_world_artifacts):
        """Test topics in JSON format"""
        result = runner.invoke(cli, [
            'inspect',
            hello_world_artifacts,
            '--topics',
            '--format', 'json'
        ])

        assert result.exit_code == 0
        # Should contain valid JSON with topics
        assert '/Hello/MessageGenerated' in result.output

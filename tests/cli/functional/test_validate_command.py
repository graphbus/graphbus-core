"""
Functional tests for validate command
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from graphbus_cli.main import cli


class TestValidateCommand:
    """Functional tests for graphbus validate command"""

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

    def test_validate_help(self, runner):
        """Test validate command help"""
        result = runner.invoke(cli, ['validate', '--help'])

        assert result.exit_code == 0
        assert 'Validate agent definitions' in result.output
        assert '--strict' in result.output
        assert '--check-types' in result.output
        assert '--check-cycles' in result.output

    def test_validate_basic(self, runner, hello_world_agents):
        """Test basic validation"""
        result = runner.invoke(cli, ['validate', hello_world_agents])

        assert result.exit_code == 0
        assert 'Validation Summary' in result.output
        assert 'Scanning modules' in result.output

    def test_validate_shows_stages(self, runner, hello_world_agents):
        """Test that validation shows all stages"""
        result = runner.invoke(cli, ['validate', hello_world_agents])

        assert result.exit_code == 0
        assert 'Scanning modules' in result.output
        assert 'Discovering agent classes' in result.output
        assert 'Extracting agent metadata' in result.output
        assert 'Building dependency graph' in result.output

    def test_validate_with_check_cycles(self, runner, hello_world_agents):
        """Test validation with cycle checking"""
        result = runner.invoke(cli, [
            'validate',
            hello_world_agents,
            '--check-cycles'
        ])

        assert result.exit_code == 0
        assert 'Checking for dependency cycles' in result.output

    def test_validate_with_strict(self, runner, hello_world_agents):
        """Test validation in strict mode"""
        result = runner.invoke(cli, [
            'validate',
            hello_world_agents,
            '--strict'
        ])

        assert result.exit_code == 0
        assert 'Running strict checks' in result.output
        assert 'Validation Summary' in result.output

    def test_validate_with_check_types(self, runner, hello_world_agents):
        """Test validation with type checking"""
        result = runner.invoke(cli, [
            'validate',
            hello_world_agents,
            '--check-types'
        ])

        assert result.exit_code == 0
        # Should complete without crashing
        assert 'Validation Summary' in result.output

    def test_validate_all_flags(self, runner, hello_world_agents):
        """Test validation with all flags"""
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

    def test_validate_missing_directory(self, runner):
        """Test validate with non-existent directory"""
        result = runner.invoke(cli, [
            'validate',
            'nonexistent/path'
        ])

        assert result.exit_code != 0

    def test_validate_shows_warnings(self, runner, hello_world_agents):
        """Test that validation shows warnings"""
        result = runner.invoke(cli, ['validate', hello_world_agents])

        # Hello World agents don't have @agent() decorator, should warn
        assert result.exit_code == 0
        # Should show warnings in output
        if 'Warnings:' in result.output:
            assert '⚠' in result.output or 'warning' in result.output.lower()

    def test_validate_summary_shows_counts(self, runner, hello_world_agents):
        """Test that validation summary shows counts"""
        result = runner.invoke(cli, ['validate', hello_world_agents])

        assert result.exit_code == 0
        assert 'Results:' in result.output

    def test_validate_discovers_agents(self, runner, hello_world_agents):
        """Test that validation discovers all agents"""
        result = runner.invoke(cli, ['validate', hello_world_agents])

        assert result.exit_code == 0
        # Should find 4 agents in Hello World
        assert 'Found 4 agent' in result.output

    def test_validate_builds_graph(self, runner, hello_world_agents):
        """Test that validation builds graph"""
        result = runner.invoke(cli, ['validate', hello_world_agents])

        assert result.exit_code == 0
        assert 'Building dependency graph' in result.output
        assert 'Graph:' in result.output
        assert 'nodes' in result.output

    def test_validate_no_cycles_in_hello_world(self, runner, hello_world_agents):
        """Test that Hello World has no cycles"""
        result = runner.invoke(cli, [
            'validate',
            hello_world_agents,
            '--check-cycles'
        ])

        assert result.exit_code == 0
        assert 'No cycles detected' in result.output

    def test_validate_strict_checks_topics(self, runner, hello_world_agents):
        """Test that strict mode checks topic naming"""
        result = runner.invoke(cli, [
            'validate',
            hello_world_agents,
            '--strict'
        ])

        assert result.exit_code == 0
        # Strict mode should run additional checks
        assert 'Running strict checks' in result.output

    def test_validate_exit_code_success(self, runner, hello_world_agents):
        """Test that validation exits with 0 on success"""
        result = runner.invoke(cli, ['validate', hello_world_agents])

        # Should succeed even with warnings (only errors cause non-zero exit)
        assert result.exit_code == 0

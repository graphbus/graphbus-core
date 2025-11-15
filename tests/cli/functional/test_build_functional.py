"""
Functional tests for build command
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from graphbus_cli.main import cli


class TestBuildCommandFunctional:
    """Functional tests for graphbus build command"""

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

    def test_build_hello_world(self, runner, hello_world_agents, tmp_path):
        """Test building Hello World example"""
        output_dir = tmp_path / ".graphbus"

        result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])

        assert result.exit_code == 0
        assert 'Build completed successfully' in result.output
        assert (output_dir / "graph.json").exists()
        assert (output_dir / "agents.json").exists()

    def test_build_with_verbose(self, runner, hello_world_agents, tmp_path):
        """Test build with verbose output"""
        output_dir = tmp_path / ".graphbus"

        result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir),
            '-v'
        ])

        assert result.exit_code == 0
        assert 'Scanning modules' in result.output

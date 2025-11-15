"""
Integration test for build and run workflow
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from graphbus_cli.main import cli


class TestBuildRunWorkflow:
    """Integration test for complete build and run workflow"""

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

    def test_build_then_run(self, runner, hello_world_agents, tmp_path):
        """Test building then running artifacts"""
        output_dir = tmp_path / ".graphbus"

        # Build
        build_result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])
        assert build_result.exit_code == 0

        # Run
        run_result = runner.invoke(cli, [
            'run',
            str(output_dir),
            '--interactive'
        ], input="stats\nexit\n")

        assert run_result.exit_code == 0
        assert 'Runtime started successfully' in run_result.output

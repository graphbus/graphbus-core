"""
Functional tests for build command
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from graphbus_cli.main import cli


class TestBuildCommand:
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

    def test_build_help(self, runner):
        """Test build command help"""
        result = runner.invoke(cli, ['build', '--help'])

        assert result.exit_code == 0
        assert 'Build agent graphs' in result.output
        assert '--output-dir' in result.output
        assert '--validate' in result.output
        assert '--verbose' in result.output

    def test_build_hello_world(self, runner, hello_world_agents, tmp_path):
        """Test building Hello World example"""
        output_dir = tmp_path / ".graphbus"

        result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])

        # Check exit code
        assert result.exit_code == 0, f"Build failed: {result.output}"

        # Check output messages
        assert 'Build completed successfully' in result.output
        assert 'Agents:' in result.output

        # Check artifacts were created
        assert (output_dir / "graph.json").exists()
        assert (output_dir / "agents.json").exists()
        assert (output_dir / "topics.json").exists()
        assert (output_dir / "build_summary.json").exists()

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
        assert 'Discovering GraphBusNode classes' in result.output
        assert 'Extracting agent metadata' in result.output

    def test_build_missing_directory(self, runner):
        """Test build with non-existent directory"""
        result = runner.invoke(cli, [
            'build',
            'nonexistent/path'
        ])

        assert result.exit_code != 0
        # Click will show "does not exist" error

    def test_build_creates_default_output_dir(self, runner, hello_world_agents, tmp_path):
        """Test that build creates .graphbus by default"""
        # Convert to absolute path before entering isolated filesystem
        import shutil
        agents_abs_path = Path(hello_world_agents).resolve()

        # Run from temp directory
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Copy agents to temp location
            temp_agents = Path.cwd() / "agents"
            shutil.copytree(agents_abs_path, temp_agents)

            result = runner.invoke(cli, [
                'build',
                str(temp_agents)
            ])

            assert result.exit_code == 0
            assert Path(".graphbus").exists()

    def test_build_summary_contains_agents(self, runner, hello_world_agents, tmp_path):
        """Test that build summary lists agents"""
        output_dir = tmp_path / ".graphbus"

        result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])

        assert result.exit_code == 0
        assert 'HelloService' in result.output
        assert 'LoggerService' in result.output
        assert 'PrinterService' in result.output
        assert 'ArbiterService' in result.output

    def test_build_summary_shows_counts(self, runner, hello_world_agents, tmp_path):
        """Test that build summary shows component counts"""
        output_dir = tmp_path / ".graphbus"

        result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])

        assert result.exit_code == 0
        assert 'Agents' in result.output
        assert 'Topics' in result.output
        assert 'Subscriptions' in result.output
        assert 'Dependencies' in result.output

    def test_build_artifacts_content(self, runner, hello_world_agents, tmp_path):
        """Test that artifacts contain expected content"""
        import json

        output_dir = tmp_path / ".graphbus"

        result = runner.invoke(cli, [
            'build',
            hello_world_agents,
            '-o', str(output_dir)
        ])

        assert result.exit_code == 0

        # Check graph.json
        with open(output_dir / "graph.json") as f:
            graph_data = json.load(f)
            assert "nodes" in graph_data
            assert len(graph_data["nodes"]) >= 4

        # Check agents.json
        with open(output_dir / "agents.json") as f:
            agents_data = json.load(f)
            assert len(agents_data) >= 4
            agent_names = [a["name"] for a in agents_data]
            assert "HelloService" in agent_names

        # Check topics.json
        with open(output_dir / "topics.json") as f:
            topics_data = json.load(f)
            assert "topics" in topics_data
            assert "subscriptions" in topics_data

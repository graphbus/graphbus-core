"""
Tests for init and generate CLI commands
"""

import pytest
from pathlib import Path
from click.testing import CliRunner
from graphbus_cli.commands.init import init, list_templates_cmd
from graphbus_cli.commands.generate import generate


class TestInitCommand:
    """Test init command"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory"""
        return tmp_path

    def test_init_basic_template(self, runner, temp_dir):
        """Test initializing project with basic template"""
        project_name = "test-project"

        result = runner.invoke(init, [
            project_name,
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0
        assert "created successfully" in result.output

        # Check project structure
        project_path = temp_dir / project_name
        assert project_path.exists()
        assert (project_path / "agents").exists()
        assert (project_path / "tests").exists()
        assert (project_path / "README.md").exists()
        assert (project_path / "requirements.txt").exists()
        assert (project_path / ".gitignore").exists()

    def test_init_specific_template(self, runner, temp_dir):
        """Test initializing with specific template"""
        result = runner.invoke(init, [
            "test-project",
            '--template', 'basic',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0
        project_path = temp_dir / "test-project"
        assert project_path.exists()

    def test_init_existing_directory_fails(self, runner, temp_dir):
        """Test that init fails if directory exists"""
        project_name = "test-project"
        project_path = temp_dir / project_name
        project_path.mkdir()

        result = runner.invoke(init, [
            project_name,
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code != 0
        assert "already exists" in result.output.lower()

    def test_init_with_force_overwrites(self, runner, temp_dir):
        """Test that --force flag allows overwriting"""
        project_name = "test-project"
        project_path = temp_dir / project_name
        project_path.mkdir()

        result = runner.invoke(init, [
            project_name,
            '--output-dir', str(temp_dir),
            '--force'
        ])

        assert result.exit_code == 0
        assert "created successfully" in result.output

    def test_init_creates_agents(self, runner, temp_dir):
        """Test that init creates agent files"""
        result = runner.invoke(init, [
            "test-project",
            '--template', 'basic',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agents_dir = temp_dir / "test-project" / "agents"
        agent_files = list(agents_dir.glob("*.py"))

        # Basic template should have 3 agents + __init__.py
        assert len(agent_files) >= 3

    def test_init_creates_readme(self, runner, temp_dir):
        """Test that README.md is created"""
        result = runner.invoke(init, [
            "test-project",
            '--template', 'basic',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        readme = temp_dir / "test-project" / "README.md"
        assert readme.exists()

        content = readme.read_text()
        assert "test-project" in content
        assert "GraphBus" in content

    def test_init_creates_requirements(self, runner, temp_dir):
        """Test that requirements.txt is created"""
        result = runner.invoke(init, [
            "test-project",
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        requirements = temp_dir / "test-project" / "requirements.txt"
        assert requirements.exists()

        content = requirements.read_text()
        assert "graphbus-core" in content
        assert "graphbus-cli" in content

    def test_init_creates_gitignore(self, runner, temp_dir):
        """Test that .gitignore is created"""
        result = runner.invoke(init, [
            "test-project",
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        gitignore = temp_dir / "test-project" / ".gitignore"
        assert gitignore.exists()

        content = gitignore.read_text()
        assert "__pycache__" in content
        assert ".graphbus" in content

    def test_init_shows_next_steps(self, runner, temp_dir):
        """Test that next steps are shown"""
        result = runner.invoke(init, [
            "test-project",
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0
        assert "Next Steps" in result.output
        assert "graphbus build" in result.output
        assert "graphbus run" in result.output

    def test_list_templates_command(self, runner):
        """Test list-templates command"""
        result = runner.invoke(list_templates_cmd)

        assert result.exit_code == 0
        assert "Available Templates" in result.output
        assert "basic" in result.output.lower()
        assert "microservices" in result.output.lower()
        assert "etl" in result.output.lower()


class TestGenerateCommand:
    """Test generate command"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory"""
        output_dir = tmp_path / "agents"
        output_dir.mkdir()
        return output_dir

    def test_generate_simple_agent(self, runner, temp_dir):
        """Test generating a simple agent"""
        result = runner.invoke(generate, [
            'agent', 'TestAgent',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0
        assert "generated successfully" in result.output

        # Check file was created
        agent_file = temp_dir / "test_agent.py"
        assert agent_file.exists()

    def test_generate_agent_content(self, runner, temp_dir):
        """Test generated agent has correct content"""
        result = runner.invoke(generate, [
            'agent', 'OrderProcessor',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agent_file = temp_dir / "order_processor.py"
        content = agent_file.read_text()

        # Check for expected content
        assert "class OrderProcessor" in content
        assert "GraphBusNode" in content
        assert "from graphbus_core" in content
        assert "SYSTEM_PROMPT" in content

    def test_generate_agent_with_methods(self, runner, temp_dir):
        """Test generating agent with custom methods"""
        result = runner.invoke(generate, [
            'agent', 'DataProcessor',
            '--method', 'process_data',
            '--method', 'validate_data',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agent_file = temp_dir / "data_processor.py"
        content = agent_file.read_text()

        assert "def process_data" in content
        assert "def validate_data" in content
        assert "@method" in content

    def test_generate_agent_with_subscriptions(self, runner, temp_dir):
        """Test generating agent with subscriptions"""
        result = runner.invoke(generate, [
            'agent', 'EventHandler',
            '--subscribes', '/Order/Created',
            '--subscribes', '/Order/Updated',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agent_file = temp_dir / "event_handler.py"
        content = agent_file.read_text()

        assert "@subscribes" in content
        assert "/Order/Created" in content
        assert "/Order/Updated" in content
        assert "def on_order_created" in content
        assert "def on_order_updated" in content

    def test_generate_agent_with_publishes(self, runner, temp_dir):
        """Test generating agent with publish hints"""
        result = runner.invoke(generate, [
            'agent', 'Publisher',
            '--subscribes', '/Input/Event',
            '--publishes', '/Output/Event',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agent_file = temp_dir / "publisher.py"
        content = agent_file.read_text()

        # Should have comment hints about publishing
        assert "/Output/Event" in content

    def test_generate_agent_with_llm(self, runner, temp_dir):
        """Test generating agent with LLM integration"""
        result = runner.invoke(generate, [
            'agent', 'AIAgent',
            '--with-llm',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agent_file = temp_dir / "ai_agent.py"
        content = agent_file.read_text()

        assert "LLMClient" in content
        assert "self.llm" in content
        assert "from graphbus_core.agents.llm_client import LLMClient" in content

    def test_generate_agent_with_state(self, runner, temp_dir):
        """Test generating agent with state persistence"""
        result = runner.invoke(generate, [
            'agent', 'StatefulAgent',
            '--with-state',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agent_file = temp_dir / "stateful_agent.py"
        content = agent_file.read_text()

        assert "def get_state" in content
        assert "def set_state" in content
        assert "self.state_data" in content

    def test_generate_agent_with_all_features(self, runner, temp_dir):
        """Test generating agent with all features"""
        result = runner.invoke(generate, [
            'agent', 'CompleteAgent',
            '--method', 'process',
            '--subscribes', '/Input/Data',
            '--publishes', '/Output/Data',
            '--with-llm',
            '--with-state',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agent_file = temp_dir / "complete_agent.py"
        content = agent_file.read_text()

        # Check all features present
        assert "class CompleteAgent" in content
        assert "def process" in content
        assert "@subscribes" in content
        assert "/Input/Data" in content
        assert "/Output/Data" in content
        assert "LLMClient" in content
        assert "get_state" in content
        assert "set_state" in content

    def test_generate_agent_existing_file_fails(self, runner, temp_dir):
        """Test that generate fails if file exists"""
        # Create the file first
        agent_file = temp_dir / "existing_agent.py"
        agent_file.write_text("# existing content")

        result = runner.invoke(generate, [
            'agent', 'ExistingAgent',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_generate_snake_case_conversion(self, runner, temp_dir):
        """Test that agent names are converted to snake_case for filenames"""
        result = runner.invoke(generate, [
            'agent', 'MyComplexAgentName',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        # Should create my_complex_agent_name.py
        agent_file = temp_dir / "my_complex_agent_name.py"
        assert agent_file.exists()

    def test_generate_topic_to_handler_conversion(self, runner, temp_dir):
        """Test that topics are converted to handler names"""
        result = runner.invoke(generate, [
            'agent', 'Handler',
            '--subscribes', '/Order/Created',
            '--subscribes', '/Payment/Processed',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agent_file = temp_dir / "handler.py"
        content = agent_file.read_text()

        # /Order/Created -> on_order_created
        assert "def on_order_created" in content
        # /Payment/Processed -> on_payment_processed
        assert "def on_payment_processed" in content

    def test_generate_shows_next_steps(self, runner, temp_dir):
        """Test that next steps are shown"""
        result = runner.invoke(generate, [
            'agent', 'TestAgent',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0
        assert "Next Steps" in result.output
        assert "graphbus build" in result.output
        # When tests are generated (default), pytest instructions are shown
        assert "pytest" in result.output

    def test_generate_creates_todos(self, runner, temp_dir):
        """Test that generated code has TODO comments"""
        result = runner.invoke(generate, [
            'agent', 'TestAgent',
            '--method', 'process',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agent_file = temp_dir / "test_agent.py"
        content = agent_file.read_text()

        # Should have TODO comments
        assert "TODO" in content

    def test_generate_multiple_methods(self, runner, temp_dir):
        """Test generating agent with multiple methods"""
        result = runner.invoke(generate, [
            'agent', 'MultiMethod',
            '--method', 'method1',
            '--method', 'method2',
            '--method', 'method3',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agent_file = temp_dir / "multi_method.py"
        content = agent_file.read_text()

        assert "def method1" in content
        assert "def method2" in content
        assert "def method3" in content

    def test_generate_custom_output_dir(self, runner, tmp_path):
        """Test generating to custom output directory"""
        custom_dir = tmp_path / "custom" / "agents"

        result = runner.invoke(generate, [
            'agent', 'TestAgent',
            '--output-dir', str(custom_dir)
        ])

        assert result.exit_code == 0

        # Directory should be created
        assert custom_dir.exists()

        agent_file = custom_dir / "test_agent.py"
        assert agent_file.exists()

    def test_generate_default_output_dir(self, runner, tmp_path):
        """Test generating to default agents/ directory"""
        # Change to temp directory
        import os
        original_dir = os.getcwd()
        os.chdir(tmp_path)

        try:
            result = runner.invoke(generate, ['agent', 'TestAgent'])

            assert result.exit_code == 0

            # Should create in agents/ directory
            agent_file = tmp_path / "agents" / "test_agent.py"
            assert agent_file.exists()

        finally:
            os.chdir(original_dir)

    def test_generate_preserves_case_in_class_name(self, runner, temp_dir):
        """Test that class name preserves original case"""
        result = runner.invoke(generate, [
            'agent', 'MyAPIAgent',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agent_file = temp_dir / "my_api_agent.py"
        content = agent_file.read_text()

        # Class name should preserve case
        assert "class MyAPIAgent" in content

    def test_generate_agent_decorator_has_name(self, runner, temp_dir):
        """Test that @agent decorator includes agent name"""
        result = runner.invoke(generate, [
            'agent', 'TestAgent',
            '--output-dir', str(temp_dir)
        ])

        assert result.exit_code == 0

        agent_file = temp_dir / "test_agent.py"
        content = agent_file.read_text()

        assert '@agent(' in content
        assert 'name="TestAgent"' in content

"""
Generate command - Generate boilerplate code for agents
"""

import click
from pathlib import Path
from typing import List

from graphbus_cli.utils.output import (
    console, print_success, print_error, print_info,
    print_header
)


@click.group()
def generate():
    """
    Generate boilerplate code for agents and other components.

    \b
    Use subcommands to generate different types of code:
      agent    - Generate a new agent class with decorators
    """
    pass


@generate.command()
@click.argument('agent_name')
@click.option(
    '--subscribes',
    multiple=True,
    help='Topic to subscribe to (can be specified multiple times)'
)
@click.option(
    '--publishes',
    multiple=True,
    help='Topic to publish to (can be specified multiple times)'
)
@click.option(
    '--method',
    'methods',
    multiple=True,
    help='Method name to add (can be specified multiple times)'
)
@click.option(
    '--output-dir',
    type=click.Path(file_okay=False, dir_okay=True),
    default='agents',
    help='Output directory (default: agents/)'
)
@click.option(
    '--with-llm',
    is_flag=True,
    help='Include LLM integration boilerplate'
)
@click.option(
    '--with-state',
    is_flag=True,
    help='Include state persistence methods'
)
@click.option(
    '--with-tests',
    is_flag=True,
    default=True,
    help='Generate unit test file (default: True)'
)
@click.option(
    '--namespace',
    type=str,
    help='Namespace/module for the agent (e.g., "services.core", "agents.processing")'
)
@click.option(
    '--depends-on',
    'dependencies',
    multiple=True,
    help='Agent dependencies (can be specified multiple times, e.g., --depends-on DataValidator --depends-on Logger)'
)
def agent(agent_name: str, subscribes: tuple, publishes: tuple, methods: tuple,
          output_dir: str, with_llm: bool, with_state: bool, with_tests: bool,
          namespace: str, dependencies: tuple):
    """
    Generate a new agent class with decorators and method stubs.

    \b
    Creates a Python file with a complete agent class including:
    - Agent decorator with metadata
    - Method stubs with type hints
    - Subscription handlers
    - Publishing helpers
    - Optional LLM integration
    - Optional state persistence

    \b
    Examples:
      graphbus generate agent OrderProcessor
      graphbus generate agent DataValidator --method validate --method transform
      graphbus generate agent NotificationService \\
        --subscribes /Order/Created \\
        --publishes /Notification/Sent \\
        --method send_email
      graphbus generate agent AIAgent --with-llm --with-state
    """
    output_path = Path(output_dir).resolve()

    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate filename from agent name
    filename = _snake_case(agent_name) + ".py"
    file_path = output_path / filename

    # Check if file exists
    if file_path.exists():
        print_error(f"File '{file_path}' already exists. Choose a different name or remove the existing file.")
        raise click.Abort()

    print_header(f"Generating Agent: {agent_name}")
    print_info(f"Output: {file_path}")
    console.print()

    try:
        # Generate agent code
        code = _generate_agent_code(
            agent_name=agent_name,
            subscribes=list(subscribes),
            publishes=list(publishes),
            methods=list(methods),
            with_llm=with_llm,
            with_state=with_state,
            namespace=namespace,
            dependencies=list(dependencies)
        )

        # Write to file
        file_path.write_text(code)

        # Generate test file if requested
        test_file_path = None
        if with_tests:
            test_file_path = _generate_test_file(
                agent_name=agent_name,
                filename=filename,
                output_path=output_path,
                subscribes=list(subscribes),
                methods=list(methods)
            )

        console.print()
        print_success(f"Agent '{agent_name}' generated successfully!")
        if test_file_path:
            print_success(f"Test file generated: {test_file_path}")
        console.print()

        # Show next steps
        print_header("Next Steps")
        console.print(f"1. Edit [cyan]{file_path}[/cyan] to implement your agent logic")
        if test_file_path:
            console.print(f"2. Edit [cyan]{test_file_path}[/cyan] to add test cases")
            console.print(f"3. Run [cyan]pytest {test_file_path}[/cyan] to test your agent")
            console.print(f"4. Run [cyan]graphbus build {output_dir}/[/cyan] to build artifacts")
        else:
            console.print(f"2. Run [cyan]graphbus build {output_dir}/[/cyan] to build artifacts")
            console.print(f"3. Run [cyan]graphbus validate {output_dir}/[/cyan] to validate the agent")

    except Exception as e:
        print_error(f"Failed to generate agent: {str(e)}")
        raise click.Abort()


def _snake_case(name: str) -> str:
    """Convert CamelCase to snake_case"""
    import re
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return name.lower()


def _generate_agent_code(agent_name: str, subscribes: List[str], publishes: List[str],
                          methods: List[str], with_llm: bool, with_state: bool,
                          namespace: str = None, dependencies: List[str] = None) -> str:
    """Generate agent code"""
    lines = []

    # Docstring
    lines.append(f'"""')
    lines.append(f'{agent_name} - Generated agent')
    lines.append(f'"""')
    lines.append('')

    # Imports
    lines.append('from graphbus_core import GraphBusNode, schema_method')
    if subscribes:
        lines.append('from graphbus_core.decorators import agent, method, subscribes')
    else:
        lines.append('from graphbus_core.decorators import agent, method')

    if with_llm:
        lines.append('from graphbus_core.agents.llm_client import LLMClient')

    lines.append('')
    lines.append('')

    # Agent decorator
    lines.append(f'@agent(')
    lines.append(f'    name="{agent_name}",')
    if namespace:
        lines.append(f'    namespace="{namespace}",')
    lines.append(f'    description="TODO: Add agent description"{"," if dependencies else ""}')
    if dependencies:
        deps_str = ', '.join([f'"{dep}"' for dep in dependencies])
        lines.append(f'    dependencies=[{deps_str}]')
    lines.append(f')')

    # Class definition
    lines.append(f'class {agent_name}(GraphBusNode):')
    lines.append(f'    """TODO: Add class docstring"""')
    lines.append('')
    lines.append('    SYSTEM_PROMPT = """')
    lines.append(f'    You are a {agent_name} agent.')
    if namespace:
        lines.append(f'    Namespace: {namespace}')
    lines.append('    TODO: Describe your role and capabilities.')
    if dependencies:
        lines.append('')
        lines.append('    Dependencies:')
        for dep in dependencies:
            lines.append(f'    - {dep}: TODO: Describe relationship')
    lines.append('')
    lines.append('    In Build Mode, you can negotiate with other agents to improve')
    lines.append('    TODO: describe what aspects of the system you can improve.')
    lines.append('    """')
    lines.append('')

    # Init method
    lines.append('    def __init__(self):')
    lines.append('        super().__init__()')

    if with_state:
        lines.append('        # State variables')
        lines.append('        self.state_data = {}')

    if with_llm:
        lines.append('        # LLM client')
        lines.append('        self.llm = LLMClient()')

    lines.append('')

    # Generated methods
    if methods:
        for method_name in methods:
            lines.append('    @method(')
            lines.append(f'        description="TODO: Describe {method_name}",')
            lines.append('        parameters={},')
            lines.append('        return_type="Any"')
            lines.append('    )')
            lines.append(f'    def {method_name}(self):')
            lines.append(f'        """TODO: Implement {method_name}"""')
            lines.append('        pass')
            lines.append('')

    # Subscription handlers
    if subscribes:
        for topic in subscribes:
            handler_name = _topic_to_handler_name(topic)
            lines.append(f'    @subscribes("{topic}")')
            lines.append(f'    def {handler_name}(self, payload):')
            lines.append(f'        """Handle {topic} events"""')
            if publishes:
                lines.append(f'        # TODO: Process payload and publish results')
                for pub_topic in publishes:
                    lines.append(f'        # self.publish("{pub_topic}", {{"result": "..."}})')
            else:
                lines.append('        # TODO: Process payload')
            lines.append('        pass')
            lines.append('')

    # State persistence methods
    if with_state:
        lines.append('    def get_state(self):')
        lines.append('        """Get agent state for persistence"""')
        lines.append('        return {')
        lines.append('            "state_data": self.state_data,')
        lines.append('            # Add more state variables here')
        lines.append('        }')
        lines.append('')
        lines.append('    def set_state(self, state):')
        lines.append('        """Restore agent state from persistence"""')
        lines.append('        self.state_data = state.get("state_data", {})')
        lines.append('        # Restore more state variables here')
        lines.append('')

    return '\n'.join(lines)


def _topic_to_handler_name(topic: str) -> str:
    """Convert topic to handler method name"""
    # Remove leading slash
    topic = topic.lstrip('/')
    # Replace slashes with underscores
    topic = topic.replace('/', '_')
    # Convert to lowercase
    topic = topic.lower()
    # Add on_ prefix
    return f'on_{topic}'


def _generate_test_file(agent_name: str, filename: str, output_path: Path,
                        subscribes: List[str], methods: List[str]) -> Path:
    """
    Generate unit test file for the agent.

    Args:
        agent_name: Name of the agent class
        filename: Agent filename (snake_case)
        output_path: Output directory for agent
        subscribes: List of subscribed topics
        methods: List of method names

    Returns:
        Path to generated test file
    """
    # Create tests directory if it doesn't exist
    tests_dir = output_path.parent / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py in tests directory
    tests_init = tests_dir / "__init__.py"
    if not tests_init.exists():
        tests_init.write_text("")

    # Generate test filename
    test_filename = f"test_{filename}"
    test_file_path = tests_dir / test_filename

    # Generate test code
    test_code = _generate_test_code(agent_name, filename.replace('.py', ''), subscribes, methods)

    # Write test file
    test_file_path.write_text(test_code)

    return test_file_path


def _generate_test_code(agent_name: str, module_name: str,
                       subscribes: List[str], methods: List[str]) -> str:
    """Generate test code for agent"""
    lines = []

    # Docstring
    lines.append(f'"""')
    lines.append(f'Unit tests for {agent_name}')
    lines.append(f'"""')
    lines.append('')
    lines.append('import pytest')
    lines.append(f'from {module_name} import {agent_name}')
    lines.append('')
    lines.append('')

    # Test class
    lines.append(f'class Test{agent_name}:')
    lines.append(f'    """Test {agent_name} class"""')
    lines.append('')

    # Fixture
    lines.append('    @pytest.fixture')
    lines.append('    def agent(self):')
    lines.append(f'        """Create {agent_name} instance"""')
    lines.append(f'        return {agent_name}()')
    lines.append('')

    # Test initialization
    lines.append('    def test_initialization(self, agent):')
    lines.append('        """Test agent initializes correctly"""')
    lines.append(f'        assert agent is not None')
    lines.append(f'        assert isinstance(agent, {agent_name})')
    lines.append('')

    # Test methods
    if methods:
        for method in methods:
            lines.append(f'    def test_{method}(self, agent):')
            lines.append(f'        """Test {method} method"""')
            lines.append(f'        # TODO: Implement test for {method}')
            lines.append(f'        result = agent.{method}()')
            lines.append(f'        # Add assertions here')
            lines.append(f'        assert result is not None or result is None  # Replace with actual assertion')
            lines.append('')

    # Test subscription handlers
    if subscribes:
        for topic in subscribes:
            handler_name = _topic_to_handler_name(topic)
            lines.append(f'    def test_{handler_name}(self, agent):')
            lines.append(f'        """Test {handler_name} handler"""')
            lines.append(f'        # TODO: Implement test for {topic} handler')
            lines.append(f'        payload = {{"test": "data"}}')
            lines.append(f'        # Call handler')
            lines.append(f'        agent.{handler_name}(payload)')
            lines.append(f'        # Add assertions here')
            lines.append(f'        # assert agent.some_state == expected_value')
            lines.append('')

    # Test state persistence if applicable
    lines.append('    def test_get_state(self, agent):')
    lines.append('        """Test state retrieval"""')
    lines.append('        if hasattr(agent, "get_state"):')
    lines.append('            state = agent.get_state()')
    lines.append('            assert isinstance(state, dict)')
    lines.append('')

    lines.append('    def test_set_state(self, agent):')
    lines.append('        """Test state restoration"""')
    lines.append('        if hasattr(agent, "set_state"):')
    lines.append('            state = {"test_key": "test_value"}')
    lines.append('            agent.set_state(state)')
    lines.append('            # Add assertions to verify state was set')
    lines.append('')

    return '\n'.join(lines)

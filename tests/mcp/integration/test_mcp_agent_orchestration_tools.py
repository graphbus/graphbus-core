"""
Integration tests for MCP agent orchestration tools.

Tests the MCP tool definitions in graphbus-mcp-server/mcp_tools.json
to ensure all agent orchestration parameters are properly exposed.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def mcp_tools_json():
    """Load the MCP tools definition file."""
    mcp_tools_path = Path(__file__).parent.parent.parent.parent / "graphbus-mcp-server" / "mcp_tools.json"

    if not mcp_tools_path.exists():
        pytest.skip(f"MCP tools file not found: {mcp_tools_path}")

    with open(mcp_tools_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def graphbus_build_tool(mcp_tools_json):
    """Get the graphbus_build tool definition."""
    for tool in mcp_tools_json['tools']:
        if tool['name'] == 'graphbus_build':
            return tool
    pytest.fail("graphbus_build tool not found in mcp_tools.json")


@pytest.fixture
def graphbus_negotiate_tool(mcp_tools_json):
    """Get the graphbus_negotiate tool definition."""
    for tool in mcp_tools_json['tools']:
        if tool['name'] == 'graphbus_negotiate':
            return tool
    pytest.fail("graphbus_negotiate tool not found in mcp_tools.json")


@pytest.fixture
def graphbus_inspect_negotiation_tool(mcp_tools_json):
    """Get the graphbus_inspect_negotiation tool definition."""
    for tool in mcp_tools_json['tools']:
        if tool['name'] == 'graphbus_inspect_negotiation':
            return tool
    pytest.fail("graphbus_inspect_negotiation tool not found in mcp_tools.json")


class TestMCPBuildToolAgentOrchestration:
    """Test graphbus_build MCP tool has all agent orchestration parameters."""

    def test_build_tool_exists(self, graphbus_build_tool):
        """Verify graphbus_build tool exists."""
        assert graphbus_build_tool is not None
        assert graphbus_build_tool['name'] == 'graphbus_build'

    def test_build_has_enable_agents_parameter(self, graphbus_build_tool):
        """Verify enable_agents parameter exists."""
        schema = graphbus_build_tool['inputSchema']
        assert 'enable_agents' in schema['properties']

        enable_agents = schema['properties']['enable_agents']
        assert enable_agents['type'] == 'boolean'
        assert enable_agents['default'] is False
        assert 'LLM agent orchestration' in enable_agents['description']

    def test_build_has_llm_model_parameter(self, graphbus_build_tool):
        """Verify llm_model parameter exists."""
        schema = graphbus_build_tool['inputSchema']
        assert 'llm_model' in schema['properties']

        llm_model = schema['properties']['llm_model']
        assert llm_model['type'] == 'string'
        assert 'claude-sonnet-4-20250514' in str(llm_model.get('default', ''))
        assert 'LLM model' in llm_model['description']

    def test_build_has_llm_api_key_parameter(self, graphbus_build_tool):
        """Verify llm_api_key parameter exists."""
        schema = graphbus_build_tool['inputSchema']
        assert 'llm_api_key' in schema['properties']

        api_key = schema['properties']['llm_api_key']
        assert api_key['type'] == 'string'
        assert 'API key' in api_key['description']
        assert 'ANTHROPIC_API_KEY' in api_key['description'] or 'environment variable' in api_key['description']

    def test_build_has_max_negotiation_rounds_parameter(self, graphbus_build_tool):
        """Verify max_negotiation_rounds parameter exists."""
        schema = graphbus_build_tool['inputSchema']
        assert 'max_negotiation_rounds' in schema['properties']

        max_rounds = schema['properties']['max_negotiation_rounds']
        assert max_rounds['type'] == 'integer'
        assert max_rounds['default'] == 10
        assert 'negotiation' in max_rounds['description'].lower()

    def test_build_has_max_proposals_per_agent_parameter(self, graphbus_build_tool):
        """Verify max_proposals_per_agent parameter exists."""
        schema = graphbus_build_tool['inputSchema']
        assert 'max_proposals_per_agent' in schema['properties']

        max_proposals = schema['properties']['max_proposals_per_agent']
        assert max_proposals['type'] == 'integer'
        assert max_proposals['default'] == 5
        assert 'proposal' in max_proposals['description'].lower()

    def test_build_has_convergence_threshold_parameter(self, graphbus_build_tool):
        """Verify convergence_threshold parameter exists."""
        schema = graphbus_build_tool['inputSchema']
        assert 'convergence_threshold' in schema['properties']

        threshold = schema['properties']['convergence_threshold']
        assert threshold['type'] == 'integer'
        assert threshold['default'] == 2
        assert 'convergence' in threshold['description'].lower()

    def test_build_has_protected_files_parameter(self, graphbus_build_tool):
        """Verify protected_files parameter exists."""
        schema = graphbus_build_tool['inputSchema']
        assert 'protected_files' in schema['properties']

        protected = schema['properties']['protected_files']
        assert protected['type'] == 'array'
        assert protected['items']['type'] == 'string'
        assert 'protect' in protected['description'].lower() or 'cannot modify' in protected['description'].lower()

    def test_build_has_arbiter_agent_parameter(self, graphbus_build_tool):
        """Verify arbiter_agent parameter exists."""
        schema = graphbus_build_tool['inputSchema']
        assert 'arbiter_agent' in schema['properties']

        arbiter = schema['properties']['arbiter_agent']
        assert arbiter['type'] == 'string'
        assert 'arbiter' in arbiter['description'].lower() or 'conflict' in arbiter['description'].lower()

    def test_build_description_mentions_agent_orchestration(self, graphbus_build_tool):
        """Verify description mentions agent orchestration."""
        description = graphbus_build_tool['description']
        assert 'agent orchestration' in description.lower() or 'enable-agents' in description.lower()

    def test_build_detailed_usage_mentions_orchestration(self, graphbus_build_tool):
        """Verify detailed_usage mentions agent orchestration."""
        detailed_usage = graphbus_build_tool['detailed_usage']
        assert 'agent orchestration' in detailed_usage.lower() or 'enable_agents' in detailed_usage.lower()

    def test_build_artifacts_include_negotiations_json(self, graphbus_build_tool):
        """Verify artifacts_generated includes negotiations.json."""
        artifacts = graphbus_build_tool['artifacts_generated']

        # Check if negotiations.json is mentioned
        negotiations_mentioned = any('negotiations.json' in artifact for artifact in artifacts)
        assert negotiations_mentioned, "negotiations.json should be in artifacts_generated list"


class TestMCPNegotiateToolDefinition:
    """Test graphbus_negotiate MCP tool definition."""

    def test_negotiate_tool_exists(self, graphbus_negotiate_tool):
        """Verify graphbus_negotiate tool exists."""
        assert graphbus_negotiate_tool is not None
        assert graphbus_negotiate_tool['name'] == 'graphbus_negotiate'

    def test_negotiate_phase_is_build(self, graphbus_negotiate_tool):
        """Verify negotiate is BUILD phase."""
        assert graphbus_negotiate_tool['phase'] == 'BUILD'

    def test_negotiate_has_artifacts_dir_parameter(self, graphbus_negotiate_tool):
        """Verify artifacts_dir parameter exists and is required."""
        schema = graphbus_negotiate_tool['inputSchema']
        assert 'artifacts_dir' in schema['properties']
        assert 'artifacts_dir' in schema['required']

        artifacts_dir = schema['properties']['artifacts_dir']
        assert artifacts_dir['type'] == 'string'
        assert '.graphbus' in artifacts_dir['description']

    def test_negotiate_has_rounds_parameter(self, graphbus_negotiate_tool):
        """Verify rounds parameter exists."""
        schema = graphbus_negotiate_tool['inputSchema']
        assert 'rounds' in schema['properties']

        rounds = schema['properties']['rounds']
        assert rounds['type'] == 'integer'
        assert rounds['default'] == 5

    def test_negotiate_has_llm_model_parameter(self, graphbus_negotiate_tool):
        """Verify llm_model parameter exists."""
        schema = graphbus_negotiate_tool['inputSchema']
        assert 'llm_model' in schema['properties']

        llm_model = schema['properties']['llm_model']
        assert llm_model['type'] == 'string'
        assert 'claude' in llm_model.get('default', '').lower() or 'gpt' in llm_model['description'].lower()

    def test_negotiate_has_llm_api_key_parameter(self, graphbus_negotiate_tool):
        """Verify llm_api_key parameter exists."""
        schema = graphbus_negotiate_tool['inputSchema']
        assert 'llm_api_key' in schema['properties']

        api_key = schema['properties']['llm_api_key']
        assert api_key['type'] == 'string'
        assert 'API key' in api_key['description']

    def test_negotiate_has_max_proposals_per_agent_parameter(self, graphbus_negotiate_tool):
        """Verify max_proposals_per_agent parameter exists."""
        schema = graphbus_negotiate_tool['inputSchema']
        assert 'max_proposals_per_agent' in schema['properties']

        max_proposals = schema['properties']['max_proposals_per_agent']
        assert max_proposals['type'] == 'integer'
        assert max_proposals['default'] == 3

    def test_negotiate_has_convergence_threshold_parameter(self, graphbus_negotiate_tool):
        """Verify convergence_threshold parameter exists."""
        schema = graphbus_negotiate_tool['inputSchema']
        assert 'convergence_threshold' in schema['properties']

        threshold = schema['properties']['convergence_threshold']
        assert threshold['type'] == 'integer'
        assert threshold['default'] == 2

    def test_negotiate_has_protected_files_parameter(self, graphbus_negotiate_tool):
        """Verify protected_files parameter exists."""
        schema = graphbus_negotiate_tool['inputSchema']
        assert 'protected_files' in schema['properties']

        protected = schema['properties']['protected_files']
        assert protected['type'] == 'array'
        assert protected['items']['type'] == 'string'

    def test_negotiate_has_arbiter_agent_parameter(self, graphbus_negotiate_tool):
        """Verify arbiter_agent parameter exists."""
        schema = graphbus_negotiate_tool['inputSchema']
        assert 'arbiter_agent' in schema['properties']

        arbiter = schema['properties']['arbiter_agent']
        assert arbiter['type'] == 'string'

    def test_negotiate_has_temperature_parameter(self, graphbus_negotiate_tool):
        """Verify temperature parameter exists."""
        schema = graphbus_negotiate_tool['inputSchema']
        assert 'temperature' in schema['properties']

        temperature = schema['properties']['temperature']
        assert temperature['type'] == 'number'
        assert temperature['default'] == 0.7

    def test_negotiate_description_mentions_post_build(self, graphbus_negotiate_tool):
        """Verify description mentions post-build negotiation."""
        description = graphbus_negotiate_tool['description']
        assert 'post-build' in description.lower() or 'after' in description.lower()
        assert 'negotiation' in description.lower()

    def test_negotiate_has_when_to_use_guidance(self, graphbus_negotiate_tool):
        """Verify when_to_use guidance exists."""
        assert 'when_to_use' in graphbus_negotiate_tool
        assert len(graphbus_negotiate_tool['when_to_use']) > 0

    def test_negotiate_has_when_not_to_use_guidance(self, graphbus_negotiate_tool):
        """Verify when_not_to_use guidance exists."""
        assert 'when_not_to_use' in graphbus_negotiate_tool
        assert len(graphbus_negotiate_tool['when_not_to_use']) > 0

    def test_negotiate_precedes_inspect_negotiation(self, graphbus_negotiate_tool):
        """Verify negotiate precedes inspect_negotiation in workflow."""
        assert 'precedes_commands' in graphbus_negotiate_tool
        precedes = graphbus_negotiate_tool['precedes_commands']
        assert 'graphbus_inspect_negotiation' in precedes


class TestMCPInspectNegotiationToolDefinition:
    """Test graphbus_inspect_negotiation MCP tool definition."""

    def test_inspect_negotiation_tool_exists(self, graphbus_inspect_negotiation_tool):
        """Verify graphbus_inspect_negotiation tool exists."""
        assert graphbus_inspect_negotiation_tool is not None
        assert graphbus_inspect_negotiation_tool['name'] == 'graphbus_inspect_negotiation'

    def test_inspect_negotiation_phase_is_build(self, graphbus_inspect_negotiation_tool):
        """Verify inspect_negotiation is BUILD phase."""
        assert graphbus_inspect_negotiation_tool['phase'] == 'BUILD'

    def test_inspect_negotiation_has_artifacts_dir_parameter(self, graphbus_inspect_negotiation_tool):
        """Verify artifacts_dir parameter exists and is required."""
        schema = graphbus_inspect_negotiation_tool['inputSchema']
        assert 'artifacts_dir' in schema['properties']
        assert 'artifacts_dir' in schema['required']

        artifacts_dir = schema['properties']['artifacts_dir']
        assert artifacts_dir['type'] == 'string'

    def test_inspect_negotiation_has_format_parameter(self, graphbus_inspect_negotiation_tool):
        """Verify format parameter exists with correct options."""
        schema = graphbus_inspect_negotiation_tool['inputSchema']
        assert 'format' in schema['properties']

        format_param = schema['properties']['format']
        assert format_param['type'] == 'string'
        assert format_param['enum'] == ['table', 'json', 'timeline']
        assert format_param['default'] == 'table'

    def test_inspect_negotiation_has_round_filter(self, graphbus_inspect_negotiation_tool):
        """Verify round filter parameter exists."""
        schema = graphbus_inspect_negotiation_tool['inputSchema']
        assert 'round' in schema['properties']

        round_param = schema['properties']['round']
        assert round_param['type'] == 'integer'
        assert 'round' in round_param['description'].lower()

    def test_inspect_negotiation_has_agent_filter(self, graphbus_inspect_negotiation_tool):
        """Verify agent filter parameter exists."""
        schema = graphbus_inspect_negotiation_tool['inputSchema']
        assert 'agent' in schema['properties']

        agent_param = schema['properties']['agent']
        assert agent_param['type'] == 'string'
        assert 'agent' in agent_param['description'].lower()

    def test_inspect_negotiation_description_mentions_history(self, graphbus_inspect_negotiation_tool):
        """Verify description mentions negotiation history."""
        description = graphbus_inspect_negotiation_tool['description']
        assert 'history' in description.lower()
        assert 'negotiation' in description.lower()

    def test_inspect_negotiation_has_shows_metadata(self, graphbus_inspect_negotiation_tool):
        """Verify 'shows' metadata lists what the tool displays."""
        assert 'shows' in graphbus_inspect_negotiation_tool
        shows = graphbus_inspect_negotiation_tool['shows']

        # Should show proposals, evaluations, and other key data
        shows_text = ' '.join(shows).lower()
        assert 'proposal' in shows_text
        assert 'evaluation' in shows_text

    def test_inspect_negotiation_follows_negotiate(self, graphbus_inspect_negotiation_tool):
        """Verify inspect_negotiation follows negotiate in workflow."""
        assert 'follows_commands' in graphbus_inspect_negotiation_tool
        follows = graphbus_inspect_negotiation_tool['follows_commands']
        assert 'graphbus_negotiate' in follows or 'graphbus_build' in follows

    def test_inspect_negotiation_has_when_to_use_guidance(self, graphbus_inspect_negotiation_tool):
        """Verify when_to_use guidance exists."""
        assert 'when_to_use' in graphbus_inspect_negotiation_tool
        assert len(graphbus_inspect_negotiation_tool['when_to_use']) > 0

    def test_inspect_negotiation_has_when_not_to_use_guidance(self, graphbus_inspect_negotiation_tool):
        """Verify when_not_to_use guidance exists."""
        assert 'when_not_to_use' in graphbus_inspect_negotiation_tool
        assert len(graphbus_inspect_negotiation_tool['when_not_to_use']) > 0


class TestMCPToolsCompleteness:
    """Test overall completeness of MCP agent orchestration tools."""

    def test_all_three_tools_exist(self, mcp_tools_json):
        """Verify all three agent orchestration tools exist."""
        tool_names = [tool['name'] for tool in mcp_tools_json['tools']]

        assert 'graphbus_build' in tool_names
        assert 'graphbus_negotiate' in tool_names
        assert 'graphbus_inspect_negotiation' in tool_names

    def test_tools_have_required_metadata(self, mcp_tools_json):
        """Verify all tools have required metadata fields."""
        agent_orch_tools = [
            'graphbus_build',
            'graphbus_negotiate',
            'graphbus_inspect_negotiation'
        ]

        for tool in mcp_tools_json['tools']:
            if tool['name'] in agent_orch_tools:
                # Required fields
                assert 'name' in tool
                assert 'description' in tool
                assert 'detailed_usage' in tool
                assert 'phase' in tool
                assert 'inputSchema' in tool

                # Guidance fields
                assert 'when_to_use' in tool
                assert 'when_not_to_use' in tool

                # Workflow fields
                if tool['name'] != 'graphbus_build':  # build is the starting point
                    assert 'follows_commands' in tool

    def test_json_schema_is_valid(self, mcp_tools_json):
        """Verify mcp_tools.json has valid structure."""
        assert 'schema_version' in mcp_tools_json
        assert 'mcp_server' in mcp_tools_json
        assert 'tools' in mcp_tools_json
        assert isinstance(mcp_tools_json['tools'], list)
        assert len(mcp_tools_json['tools']) > 0

    def test_parameter_consistency_across_tools(self, graphbus_build_tool, graphbus_negotiate_tool):
        """Verify parameter consistency between build and negotiate."""
        build_schema = graphbus_build_tool['inputSchema']['properties']
        negotiate_schema = graphbus_negotiate_tool['inputSchema']['properties']

        # Common parameters should have same types
        common_params = ['llm_model', 'llm_api_key', 'max_proposals_per_agent',
                        'convergence_threshold', 'protected_files', 'arbiter_agent']

        for param in common_params:
            if param in build_schema and param in negotiate_schema:
                assert build_schema[param]['type'] == negotiate_schema[param]['type'], \
                    f"Type mismatch for {param}"

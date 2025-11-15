# GraphBus Hello World - MCP Integration

This example demonstrates how to use GraphBus with Claude Code via the Model Context Protocol (MCP).

## Prerequisites

1. **Install GraphBus**:
   ```bash
   cd /Users/ubuntu/workbench/graphbus
   pip install -e .
   ```

2. **Install MCP SDK**:
   ```bash
   pip install mcp
   ```

3. **Verify installation**:
   ```bash
   graphbus --version
   ```

## Configure Claude Code

Add the GraphBus MCP server to your Claude Code configuration:

**File**: `~/.config/claude-code/config.json` (or your Claude Code config location)

```json
{
  "mcpServers": {
    "graphbus": {
      "command": "python3",
      "args": [
        "/Users/ubuntu/workbench/graphbus/graphbus-mcp-server/server.py"
      ],
      "cwd": "/Users/ubuntu/workbench/graphbus"
    }
  }
}
```

**Alternative using uvx** (if you publish to PyPI):
```json
{
  "mcpServers": {
    "graphbus": {
      "command": "uvx",
      "args": ["graphbus-mcp"]
    }
  }
}
```

## Quick Test (Without Claude Code)

You can test the CLI directly before setting up MCP:

```bash
# 1. Build the hello world agents
cd /Users/ubuntu/workbench/graphbus/examples/hello_world_mcp
graphbus build agents/ --output-dir .graphbus

# 2. Inspect the build artifacts
graphbus inspect .graphbus --graph --agents --topics

# 3. Run the agent system
graphbus run .graphbus
```

## Using with Claude Code

Once configured, you can interact with GraphBus naturally through Claude Code:

### Example Conversations:

**User**: "Build the agents in examples/hello_world_mcp/agents/"

Claude will use the `graphbus_build` tool to build your agents.

---

**User**: "Show me the agent graph and topics"

Claude will use the `graphbus_inspect` tool with appropriate flags.

---

**User**: "Build the agents with AI-powered agent orchestration enabled"

Claude will use `graphbus_build` with `enable_agents: true` and prompt for your API key.

---

**User**: "Show me the negotiation history from the last build"

Claude will use `graphbus_inspect_negotiation` to display the negotiation results.

## Directory Structure

```
hello_world_mcp/
├── README.md           # This file
├── agents/            # Agent source code
│   └── hello_agent.py # Simple hello world agent
└── .graphbus/         # Build artifacts (created after build)
    ├── agents.json
    ├── graph.json
    ├── topics.json
    └── subscriptions.json
```

## Hello World Agent

The example includes a simple agent that demonstrates:
- Basic agent structure with `@agent` decorator
- Publishing events with `@publishes`
- Subscribing to events with `@subscribes`
- Method invocation

## Testing Agent Orchestration

To test the LLM agent orchestration feature:

```bash
# Build with agent orchestration enabled
export ANTHROPIC_API_KEY="your-api-key-here"
graphbus build agents/ --enable-agents --llm-model claude-sonnet-4-20250514

# Inspect what the agents negotiated
graphbus inspect-negotiation .graphbus --format timeline
```

Or via Claude Code:

**User**: "Build the agents with LLM orchestration enabled using Claude Sonnet 4. My API key is sk-ant-..."

**User**: "Show me the negotiation history in timeline format"

## Available MCP Tools

When using Claude Code, these tools are available:

1. **graphbus_build** - Build agents into executable artifacts
   - Optional: `enable_agents=true` for AI-powered collaboration
   - Supports all safety parameters (protected files, max rounds, etc.)

2. **graphbus_inspect** - Examine build artifacts
   - Show graph structure, agents, topics, subscriptions
   - Multiple output formats: table, json, yaml

3. **graphbus_negotiate** - Run post-build agent negotiation
   - Separate negotiation step after building
   - Useful for iterative improvement

4. **graphbus_inspect_negotiation** - View negotiation history
   - 3 formats: table, timeline, json
   - Filter by round or agent
   - Understand AI decision-making

## Troubleshooting

### MCP server not connecting

1. Check the path in your config is correct
2. Verify GraphBus is installed: `graphbus --version`
3. Check server.py is executable: `ls -l graphbus-mcp-server/server.py`
4. Test the server directly: `python3 graphbus-mcp-server/server.py`

### Build fails

1. Verify agent files exist in `agents/` directory
2. Check Python syntax in agent files
3. Run with `--verbose` flag for detailed output

### Agent orchestration fails

1. Verify API key is set: `echo $ANTHROPIC_API_KEY`
2. Check you have API credits available
3. Start with `--max-negotiation-rounds 1` for testing
4. Use `--protected-files "*.json"` to prevent modifying artifacts

## Next Steps

1. **Explore more examples**: Check `/examples/` for more complex agent systems
2. **Read the docs**: See `TRANCHE_4.5.md` for agent orchestration details
3. **Build your own agents**: Use `graphbus init my-project` to start
4. **Deploy**: Use `graphbus docker` or `graphbus k8s` for production

## Support

- Documentation: `/Users/ubuntu/workbench/graphbus/README.md`
- MCP Server Docs: `/Users/ubuntu/workbench/graphbus/graphbus-mcp-server/README.md`
- Issues: Report via GitHub or Claude Code feedback

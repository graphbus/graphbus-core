#!/bin/bash
# Test script to verify GraphBus MCP setup

echo "=== GraphBus MCP Setup Test ==="
echo ""

# 1. Check GraphBus CLI is installed
echo "1. Checking GraphBus CLI installation..."
if command -v graphbus &> /dev/null; then
    graphbus --version
    echo "✅ GraphBus CLI is installed"
else
    echo "❌ GraphBus CLI not found. Run: pip install -e /Users/ubuntu/workbench/graphbus"
    exit 1
fi
echo ""

# 2. Check MCP SDK is installed
echo "2. Checking MCP SDK installation..."
if python3 -c "import mcp" 2>/dev/null; then
    echo "✅ MCP SDK is installed"
else
    echo "❌ MCP SDK not found. Run: pip install mcp"
    exit 1
fi
echo ""

# 3. Check MCP server files exist
echo "3. Checking MCP server files..."
if [ -f "/Users/ubuntu/workbench/graphbus/graphbus-mcp-server/server.py" ]; then
    echo "✅ server.py exists"
else
    echo "❌ server.py not found"
    exit 1
fi

if [ -f "/Users/ubuntu/workbench/graphbus/graphbus-mcp-server/mcp_tools.json" ]; then
    echo "✅ mcp_tools.json exists"
    TOOL_COUNT=$(python3 -c "import json; print(len(json.load(open('/Users/ubuntu/workbench/graphbus/graphbus-mcp-server/mcp_tools.json'))['tools']))")
    echo "   Found $TOOL_COUNT tools defined"
else
    echo "❌ mcp_tools.json not found"
    exit 1
fi
echo ""

# 4. Check hello world example is built
echo "4. Checking hello world example..."
if [ -d "/Users/ubuntu/workbench/graphbus/examples/hello_world_mcp/.graphbus" ]; then
    echo "✅ Hello world example is built"
    AGENT_COUNT=$(python3 -c "import json; agents=json.load(open('/Users/ubuntu/workbench/graphbus/examples/hello_world_mcp/.graphbus/agents.json')); print(len(agents))")
    echo "   Found $AGENT_COUNT agent(s)"
else
    echo "⚠️  Hello world not built yet. Run: cd examples/hello_world_mcp && graphbus build agents/"
fi
echo ""

# 5. Show configuration for Claude Code
echo "5. Claude Code Configuration:"
echo ""
echo "Add this to your Claude Code config file:"
echo "(Usually: ~/.config/claude-code/config.json or similar)"
echo ""
cat << 'EOF'
{
  "mcpServers": {
    "graphbus": {
      "command": "python3",
      "args": ["/Users/ubuntu/workbench/graphbus/graphbus-mcp-server/server.py"],
      "cwd": "/Users/ubuntu/workbench/graphbus",
      "env": {
        "PYTHONPATH": "/Users/ubuntu/workbench/graphbus"
      }
    }
  }
}
EOF
echo ""

echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Add the configuration above to Claude Code"
echo "2. Restart Claude Code"
echo "3. Start chatting: 'Build the agents in examples/hello_world_mcp/agents/'"
echo ""
echo "Test GraphBus CLI directly:"
echo "  cd examples/hello_world_mcp"
echo "  graphbus build agents/"
echo "  graphbus inspect .graphbus --graph --agents"
echo "  graphbus run .graphbus --interactive"

#!/usr/bin/env python3
"""
GraphBus MCP Server - Thin wrapper around graphbus_cli commands.

This MCP server exposes all GraphBus CLI commands as tools for Claude Code.
It provides a natural language interface to the GraphBus framework.
"""

import json
import sys
import asyncio
from pathlib import Path
from typing import Any, Dict

# MCP SDK imports (will need to be installed)
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: MCP SDK not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# GraphBus CLI imports
from graphbus_cli.commands.build import build as cli_build
from graphbus_cli.commands.inspect import inspect as cli_inspect
from graphbus_cli.commands.negotiate import negotiate as cli_negotiate
from graphbus_cli.commands.inspect_negotiation import inspect_negotiation as cli_inspect_negotiation
from click.testing import CliRunner


# Load tool definitions
TOOLS_FILE = Path(__file__).parent / "mcp_tools.json"
with open(TOOLS_FILE) as f:
    TOOLS_DATA = json.load(f)


# Create MCP server
app = Server("graphbus-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available GraphBus tools."""
    tools = []

    for tool_def in TOOLS_DATA["tools"]:
        tools.append(Tool(
            name=tool_def["name"],
            description=tool_def["description"],
            inputSchema=tool_def["inputSchema"]
        ))

    return tools


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Execute a GraphBus CLI command."""

    runner = CliRunner()

    try:
        if name == "graphbus_build":
            # Map MCP parameters to CLI parameters
            args = [arguments.get("agents_dir")]

            if arguments.get("output_dir"):
                args.extend(["--output-dir", arguments["output_dir"]])
            if arguments.get("validate"):
                args.append("--validate")
            if arguments.get("verbose"):
                args.append("--verbose")

            # Agent orchestration parameters
            if arguments.get("enable_agents"):
                args.append("--enable-agents")
            if arguments.get("llm_model"):
                args.extend(["--llm-model", arguments["llm_model"]])
            if arguments.get("llm_api_key"):
                args.extend(["--llm-api-key", arguments["llm_api_key"]])
            if arguments.get("max_negotiation_rounds"):
                args.extend(["--max-negotiation-rounds", str(arguments["max_negotiation_rounds"])])
            if arguments.get("max_proposals_per_agent"):
                args.extend(["--max-proposals-per-agent", str(arguments["max_proposals_per_agent"])])
            if arguments.get("convergence_threshold"):
                args.extend(["--convergence-threshold", str(arguments["convergence_threshold"])])
            if arguments.get("protected_files"):
                for pattern in arguments["protected_files"]:
                    args.extend(["--protected-files", pattern])
            if arguments.get("arbiter_agent"):
                args.extend(["--arbiter-agent", arguments["arbiter_agent"]])

            result = runner.invoke(cli_build, args)

        elif name == "graphbus_inspect":
            args = [arguments.get("artifacts_dir")]

            if arguments.get("show_graph"):
                args.append("--graph")
            if arguments.get("show_agents"):
                args.append("--agents")
            if arguments.get("show_topics"):
                args.append("--topics")
            if arguments.get("show_subscriptions"):
                args.append("--subscriptions")
            if arguments.get("agent"):
                args.extend(["--agent", arguments["agent"]])
            if arguments.get("format"):
                args.extend(["--format", arguments["format"]])

            result = runner.invoke(cli_inspect, args)

        elif name == "graphbus_negotiate":
            args = [arguments.get("artifacts_dir")]

            if arguments.get("rounds"):
                args.extend(["--rounds", str(arguments["rounds"])])
            if arguments.get("llm_model"):
                args.extend(["--llm-model", arguments["llm_model"]])
            if arguments.get("llm_api_key"):
                args.extend(["--llm-api-key", arguments["llm_api_key"]])
            if arguments.get("max_proposals_per_agent"):
                args.extend(["--max-proposals-per-agent", str(arguments["max_proposals_per_agent"])])
            if arguments.get("convergence_threshold"):
                args.extend(["--convergence-threshold", str(arguments["convergence_threshold"])])
            if arguments.get("protected_files"):
                for pattern in arguments["protected_files"]:
                    args.extend(["--protected-files", pattern])
            if arguments.get("arbiter_agent"):
                args.extend(["--arbiter-agent", arguments["arbiter_agent"]])
            if arguments.get("temperature"):
                args.extend(["--temperature", str(arguments["temperature"])])

            result = runner.invoke(cli_negotiate, args)

        elif name == "graphbus_inspect_negotiation":
            args = [arguments.get("artifacts_dir")]

            if arguments.get("format"):
                args.extend(["--format", arguments["format"]])
            if arguments.get("round"):
                args.extend(["--round", str(arguments["round"])])
            if arguments.get("agent"):
                args.extend(["--agent", arguments["agent"]])

            result = runner.invoke(cli_inspect_negotiation, args)

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}\n\nAvailable tools: graphbus_build, graphbus_inspect, graphbus_negotiate, graphbus_inspect_negotiation"
            )]

        # Format output
        output = result.output
        if result.exit_code != 0:
            if result.exception:
                output += f"\n\nError: {str(result.exception)}"
            output = f"❌ Command failed (exit code {result.exit_code})\n\n{output}"
        else:
            output = f"✅ Command succeeded\n\n{output}"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Error executing {name}: {str(e)}"
        )]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

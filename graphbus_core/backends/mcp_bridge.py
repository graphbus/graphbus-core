"""MCP bridge — serves tool defs as a local HTTP MCP server for the SDK.

Adapted from the alpaca-trader pattern. Starts a lightweight streamable-HTTP
MCP server on a free localhost port. The SDK's CLI subprocess connects to it
like any other HTTP MCP server.
"""

import json
import logging
import socket
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def create_mcp_server_config(
    agent_name: str,
    tools: list[dict],
    handler: Callable[[str, dict], Any],
) -> dict:
    """Start an HTTP MCP server and return an SDK-compatible config dict.

    Args:
        agent_name: Used to name the MCP server.
        tools: Anthropic-format tool definitions with name, description, input_schema.
        handler: The agent's handle_tool_call(name, input) dispatcher.

    Returns:
        Dict with type/url that the SDK passes to the CLI via --mcp-config.
    """
    port = _find_free_port()

    thread = threading.Thread(
        target=_run_server,
        args=(agent_name, tools, handler, port),
        daemon=True,
        name=f"mcp-{agent_name}",
    )
    thread.start()
    logger.info("[mcp_bridge] %s MCP server listening on port %d", agent_name, port)

    return {
        "type": "http",
        "url": f"http://127.0.0.1:{port}/mcp",
    }


def _run_server(agent_name: str, tools: list[dict], handler: Callable, port: int):
    """Run the MCP HTTP server in a background thread with its own event loop."""
    import asyncio

    try:
        from mcp.server.lowlevel import Server
        from mcp.server.streamable_http import StreamableHTTPServerTransport
        from mcp.types import Tool, TextContent
        from starlette.applications import Starlette
        from starlette.routing import Mount
    except ImportError:
        logger.error(
            "MCP bridge requires: pip install mcp starlette uvicorn"
        )
        return

    server = Server(f"graphbus-{agent_name}-tools")

    mcp_tools = [
        Tool(
            name=t["name"],
            description=t.get("description", ""),
            inputSchema=t.get("input_schema", {"type": "object", "properties": {}}),
        )
        for t in tools
    ]

    @server.list_tools()
    async def list_tools():
        return mcp_tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        logger.info("[mcp_bridge] %s tool: %s(%s)", agent_name, name, arguments)
        try:
            result = handler(name, arguments)
        except Exception as e:
            logger.error("[mcp_bridge] tool error %s: %s", name, e)
            result = {"error": str(e)}

        content = (
            json.dumps(result) if isinstance(result, (dict, list)) else str(result)
        )
        if not content or content in ("", "null", "None", "{}", "[]"):
            content = "(no data returned)"

        return [TextContent(type="text", text=content)]

    transport = StreamableHTTPServerTransport(mcp_session_id=agent_name)
    app = Starlette(routes=[Mount("/mcp", app=transport.handle_request)])

    async def _serve():
        import uvicorn

        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        srv = uvicorn.Server(config)

        async with transport.connect() as streams:
            read_stream, write_stream = streams
            asyncio.create_task(server.run(read_stream, write_stream, server.create_initialization_options()))
            await srv.serve()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_serve())

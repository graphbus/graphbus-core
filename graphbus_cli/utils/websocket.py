"""
WebSocket utility functions for CLI commands

Provides helpers to start, manage, and use WebSocket server for UI communication.
"""

import asyncio
import threading
from typing import Optional, List, Dict, Any

from graphbus_cli.websocket_server import (
    GraphBusWebSocketServer,
    get_websocket_server,
    set_websocket_server,
    WEBSOCKETS_AVAILABLE
)


_server_thread: Optional[threading.Thread] = None
_server_loop: Optional[asyncio.AbstractEventLoop] = None
_server_started: bool = False


def is_websocket_available() -> bool:
    """Check if WebSocket support is available"""
    return WEBSOCKETS_AVAILABLE


def start_websocket_server(port: int = 8765, wait_for_client: bool = False, timeout: float = 5.0) -> Optional[GraphBusWebSocketServer]:
    """
    Start WebSocket server in background thread.

    Args:
        port: Port to listen on (default: 8765)
        wait_for_client: If True, wait for at least one client to connect
        timeout: Timeout for waiting for client (default: 5 seconds)

    Returns:
        GraphBusWebSocketServer instance or None if websockets not available
    """
    global _server_thread, _server_loop, _server_started

    if not WEBSOCKETS_AVAILABLE:
        return None

    if _server_started:
        return get_websocket_server()

    # Create server instance
    server = GraphBusWebSocketServer(port=port)
    set_websocket_server(server)

    # Start server in background thread with its own event loop
    def run_server():
        global _server_loop
        _server_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_server_loop)

        async def start():
            await server.start()
            # Keep server running
            while True:
                await asyncio.sleep(1)

        try:
            _server_loop.run_until_complete(start())
        except Exception as e:
            print(f"WebSocket server error: {e}")
        finally:
            _server_loop.close()

    _server_thread = threading.Thread(target=run_server, daemon=True)
    _server_thread.start()
    _server_started = True

    # Give server time to start
    import time
    time.sleep(0.5)

    # Wait for client if requested
    if wait_for_client:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if server.clients:
                break
            time.sleep(0.1)

    return server


def stop_websocket_server():
    """Stop the WebSocket server"""
    global _server_started, _server_loop

    if not _server_started:
        return

    server = get_websocket_server()

    if _server_loop and server:
        # Schedule server stop in the server's event loop
        asyncio.run_coroutine_threadsafe(server.stop(), _server_loop)

    _server_started = False


def send_message_sync(message_type: str, data: Dict[str, Any]) -> bool:
    """
    Send a message via WebSocket (synchronous wrapper).

    Args:
        message_type: Type of message ("agent_message", "progress", etc.)
        data: Message data

    Returns:
        True if message sent successfully, False otherwise
    """
    if not _server_started or not _server_loop:
        return False

    server = get_websocket_server()
    if not server:
        return False

    try:
        # Schedule the broadcast in the server's event loop
        future = asyncio.run_coroutine_threadsafe(
            server.broadcast({"type": message_type, "data": data}),
            _server_loop
        )
        future.result(timeout=1.0)
        return True
    except Exception:
        return False


def ask_question_sync(
    question: str,
    options: List[str] = None,
    context: str = None,
    timeout: float = 300
) -> Optional[str]:
    """
    Ask a question via WebSocket and wait for answer (synchronous wrapper).

    Args:
        question: Question text
        options: List of possible answers
        context: Additional context
        timeout: Timeout in seconds (default: 5 minutes)

    Returns:
        User's answer or None if timeout/error
    """
    if not _server_started or not _server_loop:
        return None

    server = get_websocket_server()
    if not server or not server.clients:
        return None

    try:
        # Schedule the question in the server's event loop
        future = asyncio.run_coroutine_threadsafe(
            server.ask_question(question, options, context, timeout),
            _server_loop
        )
        answer = future.result(timeout=timeout + 1)
        return answer
    except TimeoutError:
        return None
    except Exception:
        return None


def has_connected_clients() -> bool:
    """Check if any clients are connected to the WebSocket server"""
    if not _server_started:
        return False

    server = get_websocket_server()
    if not server:
        return False

    return len(server.clients) > 0

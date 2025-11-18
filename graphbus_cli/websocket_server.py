"""
WebSocket Server for GraphBus CLI <-> UI Communication

Provides bidirectional, async communication between the GraphBus CLI
and external UIs (Electron, web browsers, etc.).
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, asdict

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = None

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """WebSocket message"""
    type: str  # "agent_message", "progress", "question", "answer", "error", "result"
    data: Dict[str, Any]
    id: Optional[str] = None  # For request/response correlation

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        data = json.loads(json_str)
        return cls(**data)


class GraphBusWebSocketServer:
    """
    WebSocket server for GraphBus CLI communication.

    Usage:
        server = GraphBusWebSocketServer(port=8765)
        await server.start()

        # Send message to UI
        await server.broadcast({
            "type": "agent_message",
            "data": {"agent": "OrderProcessor", "text": "Processing order..."}
        })

        # Wait for user input
        answer = await server.wait_for_answer(question_id)
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets library required. Install with: pip install websockets"
            )

        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        self.message_handlers: Dict[str, Callable] = {}
        self.pending_answers: Dict[str, asyncio.Future] = {}

        logger.info(f"GraphBus WebSocket Server initialized on {host}:{port}")

    async def start(self):
        """Start the WebSocket server"""
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port
        )
        logger.info(f"WebSocket server listening on ws://{self.host}:{self.port}")

    async def stop(self):
        """Stop the WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a new client connection"""
        self.clients.add(websocket)
        logger.info(f"Client connected from {websocket.remote_address}")

        try:
            async for message_str in websocket:
                await self._handle_message(websocket, message_str)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {websocket.remote_address} disconnected")
        finally:
            self.clients.remove(websocket)

    async def _handle_message(self, websocket: WebSocketServerProtocol, message_str: str):
        """Handle incoming message from client"""
        try:
            message = Message.from_json(message_str)
            logger.debug(f"Received: {message.type}")

            # Handle answers to questions
            if message.type == "answer":
                question_id = message.data.get("question_id")
                answer = message.data.get("answer")

                if question_id in self.pending_answers:
                    future = self.pending_answers[question_id]
                    if not future.done():
                        future.set_result(answer)
                    del self.pending_answers[question_id]

            # Call registered handlers
            handler = self.message_handlers.get(message.type)
            if handler:
                await handler(message, websocket)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            await self.send_to_client(websocket, {
                "type": "error",
                "data": {"message": f"Invalid JSON: {str(e)}"}
            })
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type"""
        self.message_handlers[message_type] = handler

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.clients:
            logger.warning("No clients connected to broadcast to")
            return

        message_obj = Message(
            type=message.get("type", "message"),
            data=message.get("data", {}),
            id=message.get("id")
        )

        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message_obj.to_json())
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(client)

        # Remove disconnected clients
        self.clients -= disconnected

    async def send_to_client(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]):
        """Send message to specific client"""
        message_obj = Message(
            type=message.get("type", "message"),
            data=message.get("data", {}),
            id=message.get("id")
        )

        try:
            await websocket.send(message_obj.to_json())
        except websockets.exceptions.ConnectionClosed:
            self.clients.discard(websocket)
        except Exception as e:
            logger.error(f"Error sending to client: {e}")

    async def ask_question(self, question: str, options: list = None, context: str = None, timeout: float = 300) -> str:
        """
        Ask a question and wait for answer from UI.

        Args:
            question: Question text
            options: List of possible answers
            context: Additional context
            timeout: Timeout in seconds (default: 5 minutes)

        Returns:
            User's answer

        Raises:
            TimeoutError: If no answer received within timeout
        """
        import uuid
        question_id = str(uuid.uuid4())

        # Create future for answer
        future = asyncio.Future()
        self.pending_answers[question_id] = future

        # Send question to UI
        await self.broadcast({
            "type": "question",
            "data": {
                "question_id": question_id,
                "question": question,
                "options": options or [],
                "context": context
            },
            "id": question_id
        })

        try:
            # Wait for answer with timeout
            answer = await asyncio.wait_for(future, timeout=timeout)
            return answer
        except asyncio.TimeoutError:
            if question_id in self.pending_answers:
                del self.pending_answers[question_id]
            raise TimeoutError(f"No answer received for question within {timeout}s")

    async def send_agent_message(self, agent: str, text: str, metadata: Dict = None):
        """Send an agent message to UI"""
        await self.broadcast({
            "type": "agent_message",
            "data": {
                "agent": agent,
                "text": text,
                "metadata": metadata or {},
                "timestamp": asyncio.get_event_loop().time()
            }
        })

    async def send_progress(self, current: int, total: int, message: str = ""):
        """Send progress update to UI"""
        await self.broadcast({
            "type": "progress",
            "data": {
                "current": current,
                "total": total,
                "message": message,
                "percent": int((current / total) * 100) if total > 0 else 0
            }
        })

    async def send_error(self, message: str, exception: Exception = None):
        """Send error to UI"""
        await self.broadcast({
            "type": "error",
            "data": {
                "message": message,
                "exception": str(exception) if exception else None,
                "type": type(exception).__name__ if exception else None
            }
        })

    async def send_result(self, data: Dict[str, Any]):
        """Send result to UI"""
        await self.broadcast({
            "type": "result",
            "data": data
        })


# Global server instance
_global_server: Optional[GraphBusWebSocketServer] = None


def get_websocket_server(port: int = 8765) -> GraphBusWebSocketServer:
    """Get or create the global WebSocket server"""
    global _global_server
    if _global_server is None:
        _global_server = GraphBusWebSocketServer(port=port)
    return _global_server


def set_websocket_server(server: GraphBusWebSocketServer):
    """Set the global WebSocket server"""
    global _global_server
    _global_server = server

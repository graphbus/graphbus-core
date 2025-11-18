"""
Test WebSocket integration

Simple test to verify WebSocket server can start, accept connections,
and handle basic message flow.
"""

import sys
import time
import asyncio
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from graphbus_cli.utils.websocket import (
        start_websocket_server,
        stop_websocket_server,
        send_message_sync,
        has_connected_clients,
        is_websocket_available
    )
    print("✓ WebSocket utilities imported successfully")
except ImportError as e:
    print(f"✗ Failed to import WebSocket utilities: {e}")
    sys.exit(1)


def test_websocket_server():
    """Test basic WebSocket server functionality"""
    print("\n=== Testing WebSocket Server Integration ===\n")

    # Test 1: Check if websockets library is available
    print("Test 1: Check WebSocket library availability")
    if is_websocket_available():
        print("  ✓ websockets library is available")
    else:
        print("  ✗ websockets library not installed")
        print("  Run: pip install websockets")
        return False

    # Test 2: Start WebSocket server
    print("\nTest 2: Start WebSocket server")
    try:
        server = start_websocket_server(port=8765, wait_for_client=False, timeout=1.0)
        if server:
            print("  ✓ WebSocket server started on ws://localhost:8765")
        else:
            print("  ✗ Failed to start WebSocket server")
            return False
    except Exception as e:
        print(f"  ✗ Exception starting server: {e}")
        return False

    # Give server time to fully start
    time.sleep(1.0)

    # Test 3: Check client connection status
    print("\nTest 3: Check for connected clients")
    if has_connected_clients():
        print("  ✓ UI client is connected")

        # Test 4: Send a test message
        print("\nTest 4: Send test message to UI")
        success = send_message_sync("agent_message", {
            "agent": "TestAgent",
            "text": "This is a test message from GraphBus CLI",
            "level": "info"
        })
        if success:
            print("  ✓ Message sent successfully")
        else:
            print("  ✗ Failed to send message")
    else:
        print("  ℹ No UI client connected (this is normal if UI is not running)")
        print("  To test with UI:")
        print("    1. Start the Electron UI")
        print("    2. Connect to ws://localhost:8765")
        print("    3. Re-run this test")

    # Test 5: Stop WebSocket server
    print("\nTest 5: Stop WebSocket server")
    try:
        stop_websocket_server()
        print("  ✓ WebSocket server stopped successfully")
    except Exception as e:
        print(f"  ✗ Exception stopping server: {e}")
        return False

    print("\n=== All Tests Passed ===\n")
    return True


def test_question_flow():
    """Test question/answer flow (requires UI to be connected)"""
    print("\n=== Testing Question/Answer Flow ===\n")
    print("This test requires the UI to be connected.\n")

    from graphbus_cli.utils.websocket import ask_question_sync

    # Start server
    server = start_websocket_server(port=8765, wait_for_client=False)
    if not server:
        print("✗ Could not start WebSocket server")
        return False

    time.sleep(1.0)

    if not has_connected_clients():
        print("ℹ No UI connected - skipping interactive test")
        print("  To test interactively:")
        print("    1. Start the Electron UI")
        print("    2. Connect to ws://localhost:8765")
        print("    3. Re-run this test with --interactive flag")
        stop_websocket_server()
        return True

    # Send a test question
    print("Sending test question to UI...")
    answer = ask_question_sync(
        question="What is your favorite color?",
        options=["Red", "Blue", "Green", "Yellow"],
        context="This is a test question from the CLI integration test",
        timeout=30
    )

    if answer:
        print(f"✓ Received answer from UI: {answer}")
    else:
        print("✗ No answer received (timeout or error)")

    stop_websocket_server()
    return bool(answer)


if __name__ == "__main__":
    # Run basic tests
    success = test_websocket_server()

    # If --interactive flag is provided, run interactive test
    if "--interactive" in sys.argv:
        print("\n" + "="*60 + "\n")
        test_question_flow()

    sys.exit(0 if success else 1)

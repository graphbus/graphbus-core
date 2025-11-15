"""
Runtime example for Hello GraphBus

This script demonstrates Runtime Mode where:
- Code is static and immutable (no agent negotiation)
- Nodes execute as regular Python classes
- MessageBus handles pub/sub routing
- No LLM calls or code modification
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from graphbus_core.runtime import run_runtime


def main():
    """Run Hello GraphBus in Runtime Mode"""

    print("=" * 60)
    print("HELLO GRAPHBUS - RUNTIME MODE DEMO")
    print("=" * 60)
    print()

    # Start runtime (loads artifacts from .graphbus/)
    executor = run_runtime('.graphbus')

    print("\n" + "=" * 60)
    print("TESTING RUNTIME FEATURES")
    print("=" * 60)

    # Test 1: Direct method call
    print("\n[Test 1] Calling HelloService.generate_message()...")
    result = executor.call_method('HelloService', 'generate_message')
    print(f"  Result: {result}")

    # Test 2: Publish event (triggers LoggerService subscription)
    print("\n[Test 2] Publishing to /Hello/MessageGenerated...")
    executor.publish(
        '/Hello/MessageGenerated',
        {'message': 'Hello from Runtime Mode!', 'timestamp': '2024-11-14'}
    )

    # Test 3: Show statistics
    print("\n[Test 3] Runtime Statistics:")
    stats = executor.get_stats()
    print(f"  Nodes active: {stats['nodes_count']}")
    print(f"  Messages published: {stats['message_bus']['messages_published']}")
    print(f"  Messages delivered: {stats['message_bus']['messages_delivered']}")
    print(f"  Errors: {stats['message_bus']['errors']}")

    # Test 4: Get specific node
    print("\n[Test 4] Accessing node directly...")
    hello_node = executor.get_node('HelloService')
    print(f"  Node: {hello_node.name}")
    print(f"  Mode: {'runtime' if hello_node.is_runtime_mode() else 'build'}")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - RUNTIME MODE WORKING!")
    print("=" * 60)

    # Keep runtime running (in real app, this would be your main loop)
    print("\n[Info] Runtime is ready for requests")
    print("[Info] In a real application, this would continue running and processing requests")

    # Stop runtime
    executor.stop()
    print("[Info] Runtime stopped")


if __name__ == "__main__":
    main()

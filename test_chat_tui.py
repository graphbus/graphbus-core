#!/usr/bin/env python3
"""
Test script for the Chat TUI
Runs the app for 2 seconds then exits to verify it works
"""

import asyncio
from graphbus_cli.tui.chat_app import ChatTUI

async def test_run():
    """Test that the app can start and run."""
    app = ChatTUI()

    # Schedule exit after 2 seconds
    async def auto_exit():
        await asyncio.sleep(2)
        app.exit()

    # Start the auto-exit task
    asyncio.create_task(auto_exit())

    # Run the app
    await app.run_async()

if __name__ == "__main__":
    print("Testing ChatTUI...")
    print("App will run for 2 seconds then exit automatically")
    print()

    try:
        asyncio.run(test_run())
        print()
        print("✅ ChatTUI test passed! The app runs correctly.")
        print()
        print("To use it interactively, run:")
        print("  graphbus tui")
    except KeyboardInterrupt:
        print("\n✅ Test interrupted (that's okay)")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

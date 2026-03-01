"""
Build script for Hello GraphBus example
"""

import sys
import os

# Add parent directory to path so we can import graphbus_core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from graphbus_core.config import BuildConfig
from graphbus_core.build.builder import build_project


def main():
    """Run the build process for Hello GraphBus."""
    # Get API key from environment
    api_key = os.environ.get('GRAPHBUS_API_KEY')

    config = BuildConfig(
        root_package="examples.hello_graphbus.agents",
        output_dir="examples/hello_graphbus/.graphbus"
    )

    # Add LLM config for agent orchestration
    config.llm_config = {
        'model': 'claude-sonnet-4-20250514',
        'api_key': api_key
    }

    try:
        # Enable agent mode to activate LLM agents
        enable_agents = api_key is not None
        if enable_agents:
            print("Agent mode enabled - agents will propose code improvements")
        else:
            print("Agent mode disabled - set GRAPHBUS_API_KEY to enable (get yours at graphbus.com)")

        artifacts = build_project(config, enable_agents=enable_agents)
        print("\nBuild successful!")
        print(f"Artifacts saved to: {artifacts.output_dir}")

        if enable_agents and artifacts.modified_files:
            print(f"\nAgents modified {len(artifacts.modified_files)} files:")
            for file in artifacts.modified_files:
                print(f"  - {file}")
    except Exception as e:
        print(f"\nBuild failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

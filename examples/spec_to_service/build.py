"""
Build script for the spec_to_service GraphBus example.

Scans agents, runs negotiation if GRAPHBUS_API_KEY is set,
and saves build artifacts to .graphbus/.
"""

import sys
import os

# Add project root to path so graphbus_core is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from graphbus_core.config import BuildConfig
from graphbus_core.build.builder import build_project


def main():
    api_key = os.environ.get('GRAPHBUS_API_KEY')

    config = BuildConfig(
        root_package="examples.spec_to_service.agents",
        output_dir="examples/spec_to_service/.graphbus"
    )

    config.llm_config = {
        'model': 'claude-sonnet-4-20250514',
        'api_key': api_key
    }

    try:
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

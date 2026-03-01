"""
python3 -m graphbus_agent [options]
"""

import argparse
import contextlib
import io
import json
import sys

from graphbus_agent.runner import run_agents


def main():
    parser = argparse.ArgumentParser(
        prog="graphbus-agent",
        description="GraphBus headless agent runner — powered by Claude OAuth token",
    )
    parser.add_argument(
        "--package", "-p", required=True,
        help="Dotted Python package containing GraphBusNode subclasses "
             "(e.g. examples.hello_graphbus.agents)",
    )
    parser.add_argument(
        "--intent", "-i", default=None,
        help="Natural-language goal for the agents",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output directory for .graphbus/ artifacts (default: ./.graphbus)",
    )
    parser.add_argument(
        "--token", "-t", default=None,
        help="Anthropic/Claude OAuth token. Auto-resolved from OpenClaw or env if omitted.",
    )
    parser.add_argument(
        "--model", default="sonnet",
        help="Claude model alias (default: sonnet)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run pipeline without LLM calls (useful for testing graph structure)",
    )
    parser.add_argument(
        "--json", action="store_true", dest="output_json",
        help="Print result as JSON on stdout; verbose build output goes to stderr",
    )

    args = parser.parse_args()

    if args.output_json:
        # Capture verbose pipeline output → stderr; emit clean JSON → stdout
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = run_agents(
                root_package=args.package,
                intent=args.intent,
                output_dir=args.output,
                token=args.token,
                model=args.model,
                dry_run=args.dry_run,
            )
        sys.stderr.write(buf.getvalue())
        print(json.dumps(result.__dict__, indent=2))
    else:
        result = run_agents(
            root_package=args.package,
            intent=args.intent,
            output_dir=args.output,
            token=args.token,
            model=args.model,
            dry_run=args.dry_run,
        )
        print()
        status = "✅ SUCCESS" if result.success else "❌ FAILED"
        print(f"[graphbus-agent] {status} in {result.duration_s}s")
        if result.error:
            print(f"[graphbus-agent] Error: {result.error}")

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()

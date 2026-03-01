"""
Runtime demo for the spec_to_service GraphBus example.

Loads .graphbus/ artifacts, runs the full spec-to-service pipeline,
and writes a working FastAPI microservice to the output/ directory.
"""

import sys
import os

# Add project root to path so graphbus_core is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from graphbus_core.runtime import run_runtime

# The spec that we'll turn into a working FastAPI service
TASK_SPEC = """A task management API with:
- CRUD operations for tasks (id, title, description, status, priority, due_date)
- User assignment (assign tasks to users by user_id)
- Filter tasks by status and priority
- Mark tasks complete
No auth required for MVP."""

SERVICE_NAME = "TaskManagerAPI"


def main():
    print("=" * 60)
    print("SPEC-TO-SERVICE — GRAPHBUS RUNTIME DEMO")
    print("=" * 60)
    print()

    # ------------------------------------------------------------------
    # 1. Start runtime (loads build artifacts from .graphbus/)
    # ------------------------------------------------------------------
    artifacts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.graphbus')
    executor = run_runtime(artifacts_dir)

    print()
    print("=" * 60)
    print("RUNNING SPEC-TO-SERVICE PIPELINE")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 2. Call OrchestratorAgent.build_service()
    # ------------------------------------------------------------------
    print(f"\n[Pipeline] Input spec:\n{TASK_SPEC}\n")
    print(f"[Pipeline] Service name: {SERVICE_NAME}\n")

    result = executor.call_method(
        'OrchestratorAgent',
        'build_service',
        spec=TASK_SPEC,
        service_name=SERVICE_NAME,
    )

    output_dir = result['output_dir']
    files_written = result['files_written']

    # ------------------------------------------------------------------
    # 3. Print the generated code
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("GENERATED OUTPUT")
    print("=" * 60)

    for filepath in files_written:
        filename = os.path.basename(filepath)
        with open(filepath) as f:
            content = f.read()
        print(f"\n{'—' * 40}")
        print(f"  {filename}")
        print(f"{'—' * 40}")
        print(content)

    # ------------------------------------------------------------------
    # 4. Summary
    # ------------------------------------------------------------------
    print("=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"\n  Output directory : {output_dir}")
    print(f"  Files written    : {len(files_written)}")
    for fp in files_written:
        print(f"    - {os.path.basename(fp)}")

    # ------------------------------------------------------------------
    # 5. Runtime statistics
    # ------------------------------------------------------------------
    stats = executor.get_stats()
    print(f"\n  Nodes active     : {stats['nodes_count']}")
    if 'message_bus' in stats:
        print(f"  Messages sent    : {stats['message_bus']['messages_published']}")

    executor.stop()
    print("\n[Info] Runtime stopped")


if __name__ == "__main__":
    main()

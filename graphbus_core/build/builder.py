"""
Main build entry point
"""

from graphbus_core.config import BuildConfig
from graphbus_core.build.scanner import scan_modules, discover_node_classes
from graphbus_core.build.extractor import extract_agent_definitions, extract_contract_from_agent
from graphbus_core.build.graph_builder import build_agent_graph, validate_graph_for_build
from graphbus_core.build.artifacts import BuildArtifacts
from graphbus_core.model.topic import Topic
from graphbus_core.agents.llm_client import LLMClient
from graphbus_core.build.orchestrator import AgentOrchestrator
from graphbus_core.runtime.contracts import ContractManager
from graphbus_core.node_base import GraphBusNode


def build_project(config: BuildConfig, enable_agents: bool = False) -> BuildArtifacts:
    """
    Main entry point for Build Mode.

    Executes the build pipeline:
    1. Scan modules
    2. Discover GraphBusNode classes
    3. Extract agent definitions
    4. Build agent graph
    5. Validate graph
    6. [Optional] Activate agents and run negotiation
    7. Emit artifacts

    Args:
        config: BuildConfig with root_package and options
        enable_agents: If True, activate LLM agents and run negotiation

    Returns:
        BuildArtifacts with graph and metadata
    """
    print(f"=== GraphBus Build Mode ===")

    # Stage 1: Scan modules
    print("[1/5] Scanning modules...")

    if config.agent_dirs:
        # Scan from directory paths
        print(f"Agent directories: {config.agent_dirs}")
        modules = []
        discovered_classes = []
        for agent_dir in config.agent_dirs:
            # Scan Python files in directory
            from pathlib import Path
            import importlib.util
            import sys

            agent_path = Path(agent_dir)
            for py_file in agent_path.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                # Load module dynamically
                module_name = f"_temp_agent_{py_file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, str(py_file))
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    # Add to sys.modules so imports work
                    sys.modules[module_name] = module
                    try:
                        spec.loader.exec_module(module)
                        modules.append(module)

                        # Discover classes in this module
                        for name, obj in vars(module).items():
                            if isinstance(obj, type) and issubclass(obj, GraphBusNode) and obj != GraphBusNode:
                                # Format: (class_obj, module_name, source_file)
                                discovered_classes.append((obj, module_name, str(py_file)))
                    except Exception as e:
                        print(f"Warning: Failed to load {py_file}: {e}")
                        import traceback
                        traceback.print_exc()

        print(f"Found {len(modules)} modules")
    elif config.root_package:
        # Scan from Python package
        print(f"Root package: {config.root_package}")
        modules = scan_modules(config.root_package)
        print(f"Found {len(modules)} modules")
        discovered_classes = None  # Will be discovered in stage 2
    else:
        raise ValueError("Either root_package or agent_dirs must be specified")

    # Stage 2: Discover node classes
    print("[2/5] Discovering GraphBusNode classes...")
    if discovered_classes is None:
        discovered_classes = discover_node_classes(modules)
    print(f"Found {len(discovered_classes)} GraphBusNode classes")
    for cls, mod, _ in discovered_classes:
        mod_name = mod if isinstance(mod, str) else mod.__name__
        print(f"  - {cls.__name__} ({mod_name})")
    print()

    # Stage 3: Extract agent definitions
    print("[3/5] Extracting agent metadata...")
    agent_definitions = extract_agent_definitions(discovered_classes)
    print(f"Extracted {len(agent_definitions)} agent definitions")
    for agent_def in agent_definitions:
        print(f"  - {agent_def.name}: {len(agent_def.methods)} methods, {len(agent_def.subscriptions)} subscriptions")
    print()

    # Stage 3.5: Extract and register contracts
    print("[3.5/5] Extracting API contracts...")
    contract_manager = ContractManager(storage_path=f"{config.output_dir}/contracts")
    contracts_extracted = 0
    for (class_obj, _, _), agent_def in zip(discovered_classes, agent_definitions):
        contract_info = extract_contract_from_agent(class_obj, agent_def)
        if contract_info:
            try:
                contract_manager.register_contract(
                    agent_def.name,
                    contract_info['version'],
                    contract_info['schema']
                )
                contracts_extracted += 1
                print(f"  - {agent_def.name} v{contract_info['version']}")
            except Exception as e:
                print(f"  Warning: Failed to register contract for {agent_def.name}: {e}")
    print(f"Extracted {contracts_extracted} contracts")
    print()

    # Stage 4: Build agent graph
    print("[4/5] Building agent graph...")
    agent_graph = build_agent_graph(agent_definitions)
    print(f"Graph: {len(agent_graph)} nodes, {len(agent_graph.graph.edges())} edges")

    # Get activation order
    try:
        activation_order = agent_graph.get_agent_activation_order()
        print(f"Agent activation order: {' -> '.join(activation_order)}")
    except Exception as e:
        print(f"Warning: Could not compute activation order: {e}")
    print()

    # Stage 5: Validate graph
    print("[5/5] Validating graph...")
    errors = validate_graph_for_build(agent_graph)
    if errors:
        print(f"Validation errors:")
        for error in errors:
            print(f"  - {error}")
        raise ValueError(f"Graph validation failed with {len(errors)} errors")
    else:
        print("Graph validation passed!")
    print()

    # Stage 6: Agent orchestration (optional)
    modified_files = []
    negotiations = []
    if enable_agents:
        if not hasattr(config, 'llm_config') or config.llm_config is None:
            print("Warning: enable_agents=True but no llm_config provided, skipping agent orchestration")
        else:
            # Allow a pre-built client to be injected (e.g. ClaudeCLIClient for OAuth)
            if hasattr(config, '_cli_llm_client') and config._cli_llm_client is not None:
                llm_client = config._cli_llm_client
            else:
                llm_client = LLMClient(
                    model=config.llm_config.model,
                    api_key=config.llm_config.api_key,
                    base_url=config.llm_config.base_url
                )
            orchestrator = AgentOrchestrator(
                agent_definitions=agent_definitions,
                agent_graph=agent_graph,
                llm_client=llm_client,
                safety_config=config.safety_config,
                user_intent=config.user_intent
            )
            modified_files = orchestrator.run()
            negotiations = orchestrator.negotiation_engine.get_all_commits()

    # Collect topics and subscriptions
    topics = set()
    subscriptions = []
    for agent_def in agent_definitions:
        for subscription in agent_def.subscriptions:
            topics.add(subscription.topic)
            subscriptions.append(subscription)

    # Create artifacts
    artifacts = BuildArtifacts(
        graph=agent_graph,
        agents=agent_definitions,
        topics=list(topics),
        subscriptions=subscriptions,
        negotiations=negotiations,
        modified_files=modified_files,
        output_dir=config.output_dir
    )

    # Save artifacts
    print(f"Saving artifacts to {config.output_dir}...")
    try:
        artifacts.save()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise
    print()

    print("=== Build Complete ===")
    print(f"Agents: {len(agent_definitions)}")
    print(f"Topics: {len(topics)}")
    print(f"Subscriptions: {len(subscriptions)}")
    print()

    return artifacts

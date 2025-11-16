"""
Agent graph construction using networkx
"""

from typing import List

from graphbus_core.model.agent_def import AgentDefinition
from graphbus_core.model.graph import AgentGraph
from graphbus_core.build.extractor import infer_dependencies_from_schemas


def build_agent_graph(agent_definitions: List[AgentDefinition]) -> AgentGraph:
    """
    Build the agent dependency graph from agent definitions.

    This graph is used in Build Mode to:
    - Determine agent activation order (topological sort)
    - Route proposals and negotiations
    - Visualize agent relationships

    Args:
        agent_definitions: List of AgentDefinition objects

    Returns:
        AgentGraph with nodes and edges
    """
    graph = AgentGraph()

    # Add all agents as nodes
    for agent_def in agent_definitions:
        graph.add_agent(agent_def)

    # Add explicit dependency edges
    for agent_def in agent_definitions:
        for dependency in agent_def.dependencies:
            if dependency in graph:
                graph.add_dependency(
                    consumer=agent_def.name,
                    provider=dependency,
                    reason="explicit @depends_on"
                )

    # Add topic-based edges (pub/sub relationships)
    _add_topic_edges(graph, agent_definitions)

    # Infer schema dependencies
    inferred_deps = infer_dependencies_from_schemas(agent_definitions)
    for consumer, providers in inferred_deps.items():
        for provider in providers:
            if provider in graph and consumer in graph:
                # Only add if not already explicitly declared
                if not graph.graph.has_edge(consumer, provider):
                    graph.add_schema_dependency(
                        consumer=consumer,
                        provider=provider,
                        schema_info={"inferred": True}
                    )

    # Validate graph (check for cycles)
    if graph.has_cycle():
        cycles = list(_find_cycles(graph))
        raise ValueError(
            f"Agent graph contains cycles, cannot determine activation order. "
            f"Cycles found: {cycles}"
        )

    return graph


def _add_topic_edges(graph: AgentGraph, agent_definitions: List[AgentDefinition]) -> None:
    """
    Add edges for pub/sub topic relationships.

    For each subscription, we create:
    - publisher -> topic -> subscriber edges

    Args:
        graph: AgentGraph to add edges to
        agent_definitions: List of agent definitions
    """
    # Build a map of topics to subscribers
    topic_subscribers = {}  # topic_name -> [agent_names]
    for agent_def in agent_definitions:
        for subscription in agent_def.subscriptions:
            topic_name = subscription.topic.name
            if topic_name not in topic_subscribers:
                topic_subscribers[topic_name] = []
            topic_subscribers[topic_name].append(agent_def.name)

    # For each topic, we need to identify potential publishers
    # Simple heuristic: if an agent's name or methods suggest it might publish to a topic
    # For now, we'll just create the topic -> subscriber edges
    # Publishers can be inferred or explicitly declared later

    for topic_name, subscribers in topic_subscribers.items():
        # Add topic as a node
        if topic_name not in graph:
            graph.add_node(topic_name, node_type="topic")

        # Add edges: topic -> subscriber
        for subscriber in subscribers:
            graph.add_edge(topic_name, subscriber, edge_type="subscribes")

        # Try to infer publishers
        # Heuristic: if agent name or methods match topic pattern, it might be a publisher
        # e.g., "/Order/Created" might be published by "OrderService"
        potential_publishers = _infer_publishers_for_topic(topic_name, agent_definitions)
        for publisher in potential_publishers:
            if publisher in graph:
                graph.add_edge(publisher, topic_name, edge_type="publishes")


def _infer_publishers_for_topic(topic_name: str, agent_definitions: List[AgentDefinition]) -> List[str]:
    """
    Infer which agents might publish to a topic based on naming patterns.

    Args:
        topic_name: Topic name (e.g. "/Order/Created")
        agent_definitions: List of all agents

    Returns:
        List of agent names that might publish to this topic
    """
    publishers = []

    # Extract topic category (e.g., "Order" from "/Order/Created")
    parts = topic_name.strip('/').split('/')
    if not parts:
        return publishers

    topic_category = parts[0].lower()

    for agent_def in agent_definitions:
        agent_name_lower = agent_def.name.lower()

        # If agent name contains topic category, it might publish
        if topic_category in agent_name_lower:
            publishers.append(agent_def.name)

    return publishers


def _find_cycles(graph: AgentGraph) -> List[List[str]]:
    """
    Find all cycles in the graph.

    Args:
        graph: AgentGraph to check

    Returns:
        List of cycles (each cycle is a list of node names)
    """
    import networkx as nx

    try:
        cycles = list(nx.simple_cycles(graph.graph))
        return cycles
    except Exception:
        return []


def validate_graph_for_build(graph: AgentGraph) -> List[str]:
    """
    Validate that the graph is suitable for Build Mode execution.

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check for cycles
    if graph.has_cycle():
        cycles = _find_cycles(graph)
        errors.append(f"Graph contains cycles: {cycles}")

    # Check for isolated nodes (nodes with no connections)
    # This is a warning, not an error
    for node in graph.graph.nodes():
        if graph.graph.degree(node) == 0:
            node_data = graph.get_node_data(node)
            if node_data.get("node_type") != "topic":
                # It's okay for topics to be isolated, but agents should be connected
                print(f"Warning: Agent '{node}' has no dependencies or dependents")

    # Check that all nodes can be reached in topological order
    try:
        order = graph.topological_sort()
        if len(order) != len(graph):
            errors.append(f"Topological sort produced {len(order)} nodes, but graph has {len(graph)}")
    except Exception as e:
        errors.append(f"Could not compute topological sort: {e}")

    return errors

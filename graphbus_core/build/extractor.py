"""
Metadata extraction from GraphBusNode classes
"""

from typing import List, Tuple, Type, Optional, Dict, Any
import inspect
import ast

from graphbus_core.node_base import GraphBusNode
from graphbus_core.model.agent_def import AgentDefinition
from graphbus_core.model.prompt import SystemPrompt
from graphbus_core.model.schema import Schema, SchemaMethod
from graphbus_core.model.topic import Topic, Subscription
from graphbus_core.build.scanner import read_source_code, extract_class_source


def extract_agent_definitions(
    discovered_classes: List[Tuple[Type, str, str]]
) -> List[AgentDefinition]:
    """
    Extract AgentDefinition objects from discovered GraphBusNode classes.

    Args:
        discovered_classes: List of (class_obj, module_name, source_file_path)

    Returns:
        List of AgentDefinition objects
    """
    agent_definitions = []

    for class_obj, module_name, source_file in discovered_classes:
        agent_def = extract_single_agent(class_obj, module_name, source_file)
        agent_definitions.append(agent_def)

    return agent_definitions


def _extract_publish_topics(source_code: str) -> Dict[str, str]:
    """
    Extract topics that an agent publishes to from source code.

    Parses the AST to find self.publish(topic, payload) calls and
    extracts the topic string literals.

    Args:
        source_code: Python source code

    Returns:
        Dict mapping topic names to empty descriptions (for now)
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return {}

    publishes = {}

    for node in ast.walk(tree):
        # Look for self.publish(topic, payload) calls
        if isinstance(node, ast.Call):
            # Check if it's a method call
            if isinstance(node.func, ast.Attribute):
                # Check if it's self.publish
                if (isinstance(node.func.value, ast.Name) and
                    node.func.value.id == 'self' and
                    node.func.attr == 'publish'):

                    # Extract topic (first argument)
                    if node.args and isinstance(node.args[0], ast.Constant):
                        topic = node.args[0].value
                        if isinstance(topic, str):
                            publishes[topic] = ""  # TODO: Extract description from comments

    return publishes


def extract_single_agent(
    class_obj: Type[GraphBusNode],
    module_name: str,
    source_file: str
) -> AgentDefinition:
    """
    Extract AgentDefinition for a single class.

    Args:
        class_obj: The GraphBusNode subclass
        module_name: Module where class is defined
        source_file: Path to source file

    Returns:
        AgentDefinition object
    """
    # Read full source code
    full_source = read_source_code(source_file)

    # Use FULL source code instead of just the class
    # This allows agents to see and reason about their entire file,
    # including imports, helper functions, and any code added by negotiation
    class_source = full_source  # Changed: agents now see full file context

    # Extract system prompt
    system_prompt_text = class_obj.get_system_prompt()
    system_prompt = SystemPrompt(
        text=system_prompt_text,
        role=getattr(class_obj, '_graphbus_role', None),
        capabilities=class_obj.get_capabilities()
    )

    # Extract schema methods
    methods = []
    schema_methods_dict = class_obj.get_schema_methods()
    for method_name, schema_info in schema_methods_dict.items():
        input_schema = Schema(fields=schema_info['input'])
        output_schema = Schema(fields=schema_info['output'])

        # Get method docstring if available
        method_obj = getattr(class_obj, method_name, None)
        description = inspect.getdoc(method_obj) if method_obj else None

        schema_method = SchemaMethod(
            name=method_name,
            input_schema=input_schema,
            output_schema=output_schema,
            description=description
        )
        methods.append(schema_method)

    # Extract subscriptions
    subscriptions = []
    subscription_topics = class_obj.get_subscriptions()
    for topic_name in subscription_topics:
        # Find the handler method
        handler_name = find_subscription_handler(class_obj, topic_name)
        subscription = Subscription(
            node_name=class_obj.__name__,
            topic=Topic(topic_name),
            handler_name=handler_name
        )
        subscriptions.append(subscription)

    # Extract dependencies
    dependencies = class_obj.get_dependencies()

    # Check if this is an arbiter agent
    is_arbiter = getattr(class_obj, 'IS_ARBITER', False)

    # Create AgentDefinition
    agent_def = AgentDefinition(
        name=class_obj.__name__,
        module=module_name,
        class_name=class_obj.__name__,
        source_file=source_file,
        source_code=class_source or full_source,  # Fallback to full source if extraction fails
        system_prompt=system_prompt,
        methods=methods,
        subscriptions=subscriptions,
        dependencies=dependencies,
        is_arbiter=is_arbiter,
        metadata={}
    )

    return agent_def


def find_subscription_handler(class_obj: Type[GraphBusNode], topic_name: str) -> str:
    """
    Find the method that handles a specific topic subscription.

    Args:
        class_obj: The GraphBusNode subclass
        topic_name: Topic to find handler for

    Returns:
        Name of the handler method
    """
    # Check for @subscribe decorated methods
    for attr_name in dir(class_obj):
        if attr_name.startswith('_'):
            continue
        attr = getattr(class_obj, attr_name)
        if callable(attr) and hasattr(attr, '_graphbus_subscribe_topic'):
            if attr._graphbus_subscribe_topic == topic_name:
                return attr_name

    # Fallback: generic handle_event
    return "handle_event"


def infer_dependencies_from_schemas(
    agent_definitions: List[AgentDefinition]
) -> dict[str, list[str]]:
    """
    Infer dependencies between agents based on schema compatibility.

    If AgentA has a method that outputs a schema, and AgentB has a method
    that takes compatible input, infer that B might depend on A.

    Args:
        agent_definitions: List of all agent definitions

    Returns:
        Dict mapping agent name to list of inferred dependencies
    """
    inferred_deps = {}

    # Build a map of output schemas
    outputs = {}  # agent_name -> list of output schema fields
    for agent in agent_definitions:
        outputs[agent.name] = []
        for method in agent.methods:
            outputs[agent.name].append(set(method.output_schema.fields.keys()))

    # Check each agent's input schemas against all output schemas
    for agent in agent_definitions:
        deps = []
        for method in agent.methods:
            input_fields = set(method.input_schema.fields.keys())
            if not input_fields:
                continue

            # Check if any other agent produces compatible output
            for other_agent_name, output_field_sets in outputs.items():
                if other_agent_name == agent.name:
                    continue

                for output_fields in output_field_sets:
                    # If input is a subset of output, there's potential compatibility
                    if input_fields.issubset(output_fields):
                        if other_agent_name not in deps:
                            deps.append(other_agent_name)

        if deps:
            inferred_deps[agent.name] = deps

    return inferred_deps


def extract_contract_from_agent(class_obj: Type[GraphBusNode],
                                agent_def: AgentDefinition) -> Optional[Dict[str, Any]]:
    """
    Extract contract definition from agent during build.

    This extracts contract information either from:
    1. @contract() decorator if present
    2. Automatic generation from @schema_method decorators

    Args:
        class_obj: The GraphBusNode subclass
        agent_def: AgentDefinition with extracted metadata

    Returns:
        Contract schema dict or None
    """
    # Check if agent has explicit @contract() decorator
    if hasattr(class_obj, '_graphbus_has_contract'):
        version = getattr(class_obj, '_graphbus_contract_version', '1.0.0')
        schema = getattr(class_obj, '_graphbus_contract_schema', {})

        # Merge with extracted schema methods if not fully specified
        if 'methods' not in schema and agent_def.methods:
            schema['methods'] = _generate_methods_schema(agent_def.methods)

        if 'subscribes' not in schema and agent_def.subscriptions:
            schema['subscribes'] = [sub.topic.name for sub in agent_def.subscriptions]

        return {
            'version': version,
            'schema': schema
        }

    # Auto-generate contract from schema methods
    if agent_def.methods or agent_def.subscriptions:
        # Extract publish topics from source code
        publishes = _extract_publish_topics(agent_def.source_code)

        return {
            'version': '1.0.0',  # Default version
            'schema': {
                'methods': _generate_methods_schema(agent_def.methods),
                'publishes': publishes,  # Extracted from AST
                'subscribes': [sub.topic.name for sub in agent_def.subscriptions],
                'description': f'Auto-generated contract for {agent_def.name}'
            }
        }

    return None


def _generate_methods_schema(methods: List[SchemaMethod]) -> Dict[str, Any]:
    """Generate methods schema from SchemaMethod list"""
    schema = {}

    for method in methods:
        schema[method.name] = {
            'input': {name: str(type_) for name, type_ in method.input_schema.fields.items()},
            'output': {name: str(type_) for name, type_ in method.output_schema.fields.items()},
            'description': method.description or ''
        }

    return schema

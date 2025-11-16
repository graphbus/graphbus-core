"""
Module and class discovery for Build Mode
"""

import importlib
import pkgutil
import inspect
import os
from typing import List, Tuple, Type
from pathlib import Path


def scan_modules(root_package: str) -> List[str]:
    """
    Scan a Python package and return list of all module names.

    Args:
        root_package: Package to scan (e.g. "my_project.agents")

    Returns:
        List of module names (e.g. ["my_project.agents.hello", "my_project.agents.printer"])
    """
    try:
        package = importlib.import_module(root_package)
    except ImportError as e:
        raise ImportError(f"Cannot import root package '{root_package}': {e}")

    if not hasattr(package, '__path__'):
        # Single module, not a package
        return [root_package]

    modules = []
    package_path = package.__path__

    for importer, modname, ispkg in pkgutil.walk_packages(path=package_path, prefix=f"{root_package}."):
        modules.append(modname)

    # Also include the root package itself
    modules.insert(0, root_package)

    return modules


def discover_node_classes(modules: List[str]) -> List[Tuple[Type, str, str]]:
    """
    Discover all GraphBusNode subclasses in the given modules.

    Args:
        modules: List of module names to search

    Returns:
        List of tuples: (class_obj, module_name, source_file_path)
    """
    from graphbus_core.node_base import GraphBusNode

    discovered = []

    for module_name in modules:
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            print(f"Warning: Could not import module '{module_name}': {e}")
            continue

        # Get source file path
        source_file = None
        if hasattr(module, '__file__') and module.__file__:
            source_file = os.path.abspath(module.__file__)

        # Find all classes in the module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Check if it's a GraphBusNode subclass (but not GraphBusNode itself)
            if issubclass(obj, GraphBusNode) and obj is not GraphBusNode:
                # Make sure the class is defined in this module (not imported)
                if obj.__module__ == module_name:
                    discovered.append((obj, module_name, source_file or ""))

    return discovered


def read_source_code(source_file: str) -> str:
    """
    Read the source code from a file.

    Args:
        source_file: Path to Python source file

    Returns:
        Source code as string
    """
    if not source_file or not os.path.exists(source_file):
        return ""

    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not read source file '{source_file}': {e}")
        return ""


def extract_class_source(source_code: str, class_name: str) -> str:
    """
    Extract just the source code for a specific class from a file.

    Args:
        source_code: Full source code of the file
        class_name: Name of the class to extract

    Returns:
        Source code of just that class
    """
    # Simple implementation: find the class definition and extract until next class or EOF
    lines = source_code.split('\n')
    class_lines = []
    in_class = False
    indent_level = 0

    for line in lines:
        if line.strip().startswith(f'class {class_name}'):
            in_class = True
            indent_level = len(line) - len(line.lstrip())
            class_lines.append(line)
        elif in_class:
            current_indent = len(line) - len(line.lstrip())
            # If we hit a line with same or less indentation and it's not empty, we've left the class
            if line.strip() and current_indent <= indent_level:
                break
            class_lines.append(line)

    return '\n'.join(class_lines) if class_lines else source_code

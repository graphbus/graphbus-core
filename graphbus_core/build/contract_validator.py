"""
API Contract validation for Build Mode

Ensures that code changes respect schema_method contracts and maintain backward compatibility.
"""

import ast
from typing import Dict, List, Set, Optional
from graphbus_core.model.agent_def import AgentDefinition


class ContractValidator:
    """
    Validates that code changes honor API contracts.

    Checks:
    - Schema method signatures are preserved
    - Input/output schemas remain compatible
    - Breaking changes are flagged
    - New methods follow schema conventions
    """

    def __init__(self):
        self.violations = []
        self.warnings = []

    def validate_change(
        self,
        agent_def: AgentDefinition,
        old_code: str,
        new_code: str
    ) -> Dict:
        """
        Validate that a code change respects the agent's API contracts.

        Args:
            agent_def: Agent definition with schema contracts
            old_code: Original code
            new_code: Proposed code

        Returns:
            Validation result
        """
        self.violations = []
        self.warnings = []

        # Parse both versions
        try:
            old_tree = ast.parse(old_code)
            new_tree = ast.parse(new_code)
        except SyntaxError as e:
            return {
                "valid": False,
                "violations": [f"Syntax error: {e}"],
                "warnings": []
            }

        # Extract method signatures
        old_methods = self._extract_method_signatures(old_tree)
        new_methods = self._extract_method_signatures(new_tree)

        # Check for breaking changes
        self._check_removed_methods(old_methods, new_methods)
        self._check_signature_changes(old_methods, new_methods)
        self._check_schema_consistency(agent_def, new_methods)

        return {
            "valid": len(self.violations) == 0,
            "violations": self.violations,
            "warnings": self.warnings,
            "old_methods": list(old_methods.keys()),
            "new_methods": list(new_methods.keys())
        }

    def validate_schema_method(
        self,
        method_name: str,
        method_node: ast.FunctionDef,
        expected_schema: Optional[Dict] = None
    ) -> Dict:
        """
        Validate a single schema method.

        Args:
            method_name: Name of the method
            method_node: AST node of the method
            expected_schema: Expected schema (if any)

        Returns:
            Validation result
        """
        # Check if method has @schema_method decorator
        has_schema_decorator = False
        schema_info = None

        for decorator in method_node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == 'schema_method':
                    has_schema_decorator = True
                    # Try to extract schema from decorator
                    schema_info = self._extract_schema_from_decorator(decorator)

        if not has_schema_decorator and expected_schema:
            return {
                "valid": False,
                "reason": f"Method {method_name} is missing @schema_method decorator"
            }

        # Validate schema against expected
        if expected_schema and schema_info:
            if not self._schemas_compatible(expected_schema, schema_info):
                return {
                    "valid": False,
                    "reason": f"Method {method_name} schema doesn't match expected contract"
                }

        return {"valid": True}

    def check_backward_compatibility(
        self,
        old_agent_def: AgentDefinition,
        new_source_code: str
    ) -> Dict:
        """
        Check if new code maintains backward compatibility.

        Args:
            old_agent_def: Original agent definition
            new_source_code: New source code

        Returns:
            Compatibility report
        """
        breaking_changes = []
        compatible_changes = []

        try:
            new_tree = ast.parse(new_source_code)
        except SyntaxError as e:
            return {
                "compatible": False,
                "breaking_changes": [f"Syntax error: {e}"],
                "compatible_changes": []
            }

        new_methods = self._extract_method_signatures(new_tree)

        # Check each schema method from old definition
        for schema_method in old_agent_def.methods:
            method_name = schema_method.name

            if method_name not in new_methods:
                breaking_changes.append(
                    f"Method '{method_name}' was removed (BREAKING)"
                )
            else:
                # Check signature compatibility
                old_sig = self._method_to_signature(schema_method)
                new_sig = new_methods[method_name]

                if not self._signatures_compatible(old_sig, new_sig):
                    breaking_changes.append(
                        f"Method '{method_name}' signature changed (BREAKING)"
                    )
                else:
                    compatible_changes.append(
                        f"Method '{method_name}' signature preserved"
                    )

        # Check for new methods (not breaking, just informational)
        old_method_names = {m.name for m in old_agent_def.methods}
        for method_name in new_methods:
            if method_name not in old_method_names and not method_name.startswith('_'):
                compatible_changes.append(
                    f"New method '{method_name}' added"
                )

        return {
            "compatible": len(breaking_changes) == 0,
            "breaking_changes": breaking_changes,
            "compatible_changes": compatible_changes
        }

    # Private helper methods

    def _extract_method_signatures(self, tree: ast.AST) -> Dict[str, Dict]:
        """Extract method signatures from AST."""
        signatures = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Get parameters
                params = []
                for arg in node.args.args:
                    param_name = arg.arg
                    # Try to get type annotation
                    param_type = None
                    if arg.annotation:
                        param_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                    params.append({
                        'name': param_name,
                        'type': param_type
                    })

                # Get return type
                return_type = None
                if node.returns:
                    return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)

                signatures[node.name] = {
                    'params': params,
                    'return_type': return_type,
                    'decorators': [self._decorator_name(d) for d in node.decorator_list]
                }

        return signatures

    def _decorator_name(self, decorator: ast.expr) -> str:
        """Get decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id
        return "unknown"

    def _extract_schema_from_decorator(self, decorator: ast.Call) -> Optional[Dict]:
        """Extract schema info from @schema_method decorator."""
        schema = {}

        for keyword in decorator.keywords:
            if keyword.arg in ('input_schema', 'output_schema'):
                # Try to evaluate the schema dict
                try:
                    # This is a simplified extraction - full evaluation would need more context
                    schema[keyword.arg] = ast.unparse(keyword.value) if hasattr(ast, 'unparse') else str(keyword.value)
                except:
                    schema[keyword.arg] = "unknown"

        return schema if schema else None

    def _check_removed_methods(
        self,
        old_methods: Dict[str, Dict],
        new_methods: Dict[str, Dict]
    ) -> None:
        """Check for removed methods."""
        for method_name in old_methods:
            # Only check public methods (not starting with _)
            if not method_name.startswith('_') and method_name not in new_methods:
                self.violations.append(
                    f"PUBLIC METHOD REMOVED: '{method_name}' - this is a BREAKING CHANGE"
                )

    def _check_signature_changes(
        self,
        old_methods: Dict[str, Dict],
        new_methods: Dict[str, Dict]
    ) -> None:
        """Check for signature changes in existing methods."""
        for method_name in old_methods:
            if method_name in new_methods:
                old_sig = old_methods[method_name]
                new_sig = new_methods[method_name]

                # Check parameter count
                old_params = [p for p in old_sig['params'] if p['name'] != 'self']
                new_params = [p for p in new_sig['params'] if p['name'] != 'self']

                if len(new_params) < len(old_params):
                    self.violations.append(
                        f"Method '{method_name}' has fewer parameters - BREAKING CHANGE"
                    )
                elif len(new_params) > len(old_params):
                    self.warnings.append(
                        f"Method '{method_name}' has new parameters - ensure they have defaults for compatibility"
                    )

                # Check parameter names (order matters!)
                for i, old_param in enumerate(old_params):
                    if i < len(new_params):
                        new_param = new_params[i]
                        if old_param['name'] != new_param['name']:
                            self.violations.append(
                                f"Method '{method_name}' parameter name changed: {old_param['name']} → {new_param['name']} - BREAKING CHANGE"
                            )

    def _check_schema_consistency(
        self,
        agent_def: AgentDefinition,
        new_methods: Dict[str, Dict]
    ) -> None:
        """Check that schema methods are consistent."""
        # Build map of schema methods
        schema_method_names = {m.name for m in agent_def.methods}

        for method_name in new_methods:
            if method_name in schema_method_names:
                # This is a schema method - check it has the decorator
                decorators = new_methods[method_name]['decorators']
                if 'schema_method' not in decorators:
                    self.violations.append(
                        f"Schema method '{method_name}' is missing @schema_method decorator"
                    )

    def _method_to_signature(self, schema_method) -> Dict:
        """Convert SchemaMethod to signature dict for comparison."""
        params = []
        if hasattr(schema_method, 'input_schema'):
            for field_name, field_type in schema_method.input_schema.items():
                params.append({
                    'name': field_name,
                    'type': field_type.__name__ if hasattr(field_type, '__name__') else str(field_type)
                })

        return {
            'params': params,
            'return_type': 'dict',  # Schema methods return dicts
            'decorators': ['schema_method']
        }

    def _signatures_compatible(self, old_sig: Dict, new_sig: Dict) -> bool:
        """Check if two signatures are compatible."""
        # Check parameter count (new can have more with defaults, but not fewer)
        old_param_count = len([p for p in old_sig['params'] if p['name'] != 'self'])
        new_param_count = len([p for p in new_sig['params'] if p['name'] != 'self'])

        if new_param_count < old_param_count:
            return False

        # Check parameter names for common parameters
        old_params = [p for p in old_sig['params'] if p['name'] != 'self']
        new_params = [p for p in new_sig['params'] if p['name'] != 'self']

        for i, old_param in enumerate(old_params):
            if i < len(new_params):
                if old_param['name'] != new_params[i]['name']:
                    return False

        return True

    def _schemas_compatible(self, expected: Dict, actual: Dict) -> bool:
        """Check if schemas are compatible."""
        # Simplified check - just ensure keys match
        return set(expected.keys()) == set(actual.keys())

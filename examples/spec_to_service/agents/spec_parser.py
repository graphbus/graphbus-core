"""
SpecParserAgent - Extracts structured API requirements from plain-English specs.
"""

import re

from graphbus_core import GraphBusNode, schema_method, subscribe


class SpecParserAgent(GraphBusNode):
    SYSTEM_PROMPT = "You extract structured API requirements from plain-English specs."

    @schema_method(
        input_schema={"spec": str},
        output_schema={"endpoints": list, "models": list, "auth_required": bool}
    )
    def parse_spec(self, spec: str) -> dict:
        """Parse a plain-English spec string into structured API requirements."""
        if not isinstance(spec, str) or not spec.strip():
            raise ValueError("'spec' must be a non-empty string")

        spec_lower = spec.lower()
        endpoints = []
        models = []

        # --- Extract resource name and fields from CRUD pattern ---
        # Matches: "CRUD operations for <resource> (<field1>, <field2>, ...)"
        crud_match = re.search(
            r'crud\s+operations?\s+for\s+(\w+)\s*\(([^)]+)\)',
            spec_lower
        )

        resource_name = None
        resource_fields = []

        if crud_match:
            resource_name = crud_match.group(1).rstrip('s')  # singularise
            raw_fields = [f.strip() for f in crud_match.group(2).split(',')]
            resource_fields = self._parse_fields(raw_fields)

            # Standard CRUD endpoints
            plural = resource_name + 's'
            endpoints.extend([
                {"method": "GET", "path": f"/{plural}", "description": f"List all {plural}",
                 "query_params": [], "request_body": None, "response_model": f"{resource_name.title()}"},
                {"method": "POST", "path": f"/{plural}", "description": f"Create a {resource_name}",
                 "query_params": [], "request_body": f"{resource_name.title()}Create", "response_model": f"{resource_name.title()}"},
                {"method": "GET", "path": f"/{plural}/{{{resource_name}_id}}", "description": f"Get a {resource_name} by ID",
                 "query_params": [], "request_body": None, "response_model": f"{resource_name.title()}"},
                {"method": "PUT", "path": f"/{plural}/{{{resource_name}_id}}", "description": f"Update a {resource_name}",
                 "query_params": [], "request_body": f"{resource_name.title()}Update", "response_model": f"{resource_name.title()}"},
                {"method": "DELETE", "path": f"/{plural}/{{{resource_name}_id}}", "description": f"Delete a {resource_name}",
                 "query_params": [], "request_body": None, "response_model": None},
            ])

        # --- Detect additional operations ---
        # User assignment
        if re.search(r'assign.*user|user.*assign', spec_lower) and resource_name:
            plural = resource_name + 's'
            endpoints.append({
                "method": "PUT",
                "path": f"/{plural}/{{{resource_name}_id}}/assign",
                "description": f"Assign {resource_name} to a user",
                "query_params": [],
                "request_body": "AssignRequest",
                "response_model": f"{resource_name.title()}",
            })
            # Ensure user_id field exists on the resource model
            if not any(f['name'] == 'user_id' for f in resource_fields):
                resource_fields.append(
                    {"name": "user_id", "type": "int", "optional": True}
                )

        # Filtering
        filter_match = re.search(r'filter\s+\w+\s+by\s+([\w\s,]+?)(?:\n|$|\.)', spec_lower)
        if filter_match and resource_name:
            filter_fields = [f.strip() for f in filter_match.group(1).split(' and ')]
            # flatten comma-separated too
            expanded = []
            for f in filter_fields:
                expanded.extend([x.strip() for x in f.split(',')])
            plural = resource_name + 's'
            endpoints.append({
                "method": "GET",
                "path": f"/{plural}/filter",
                "description": f"Filter {plural} by {', '.join(expanded)}",
                "query_params": expanded,
                "request_body": None,
                "response_model": f"{resource_name.title()}",
            })

        # Mark complete
        if re.search(r'mark\s+\w+\s+complete', spec_lower) and resource_name:
            plural = resource_name + 's'
            endpoints.append({
                "method": "PUT",
                "path": f"/{plural}/{{{resource_name}_id}}/complete",
                "description": f"Mark {resource_name} as complete",
                "query_params": [],
                "request_body": None,
                "response_model": f"{resource_name.title()}",
            })

        # --- Build model definitions ---
        if resource_name and resource_fields:
            models.append({
                "name": resource_name.title(),
                "fields": resource_fields,
            })

        # --- Detect auth requirement ---
        auth_required = not bool(re.search(r'no\s+auth', spec_lower))

        return {
            "endpoints": endpoints,
            "models": models,
            "auth_required": auth_required,
        }

    @subscribe("/Pipeline/SpecSubmitted")
    def on_spec_submitted(self, event):
        """Handle spec submission events — triggers parsing automatically."""
        spec = event.get('spec', '')
        result = self.parse_spec(spec)
        print(f"[SpecParserAgent] Parsed spec: {len(result['endpoints'])} endpoints, "
              f"{len(result['models'])} models, auth={result['auth_required']}")
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_fields(raw_fields: list) -> list:
        """Infer field types from raw field name strings."""
        type_hints = {
            'id': ('int', False),
            'name': ('str', False),
            'title': ('str', False),
            'description': ('str', True),
            'status': ('str', False),
            'priority': ('str', False),
            'due_date': ('str', True),
            'created_at': ('str', True),
            'updated_at': ('str', True),
            'user_id': ('int', True),
            'email': ('str', False),
            'price': ('float', False),
            'amount': ('float', False),
            'count': ('int', False),
            'is_active': ('bool', False),
            'completed': ('bool', False),
        }
        fields = []
        for raw in raw_fields:
            name = raw.strip().replace(' ', '_')
            inferred_type, optional = type_hints.get(name, ('str', True))
            field = {"name": name, "type": inferred_type, "optional": optional}
            # Provide sensible defaults for status/priority
            if name == 'status':
                field['default'] = 'pending'
            elif name == 'priority':
                field['default'] = 'medium'
            fields.append(field)
        return fields

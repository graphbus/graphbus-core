"""
ModelAgent - Generates Pydantic models from data model specifications.
"""

from graphbus_core import GraphBusNode, schema_method, depends_on


@depends_on("SpecParserAgent")
class ModelAgent(GraphBusNode):
    SYSTEM_PROMPT = "You generate Pydantic models from data model specifications."

    # Mapping from spec type names to Python type annotations
    TYPE_MAP = {
        'str': 'str',
        'int': 'int',
        'float': 'float',
        'bool': 'bool',
        'list': 'list',
        'dict': 'dict',
    }

    @schema_method(
        input_schema={"models": list},
        output_schema={"models_code": str}
    )
    def generate_models(self, models: list) -> dict:
        """Generate Pydantic model code from a list of model definitions."""
        if not models:
            raise ValueError("'models' must be a non-empty list")

        lines = [
            '"""',
            'Pydantic models for the service',
            '"""',
            '',
            'from typing import Optional',
            '',
            'from pydantic import BaseModel',
            '',
        ]

        for model_def in models:
            name = model_def['name']
            fields = model_def.get('fields', [])

            # --- Main response model (all fields, id is required) ---
            lines.append(f'class {name}(BaseModel):')
            lines.append(f'    """Schema for {name}."""')
            for field in fields:
                lines.append(self._render_field(field))
            lines.append('')
            lines.append('')

            # --- Create model (no id, required fields only) ---
            create_fields = [f for f in fields if f['name'] != 'id']
            lines.append(f'class {name}Create(BaseModel):')
            lines.append(f'    """Schema for creating a {name}."""')
            for field in create_fields:
                lines.append(self._render_field(field))
            lines.append('')
            lines.append('')

            # --- Update model (all fields optional) ---
            update_fields = [f for f in fields if f['name'] != 'id']
            lines.append(f'class {name}Update(BaseModel):')
            lines.append(f'    """Schema for updating a {name}."""')
            for field in update_fields:
                lines.append(self._render_field(field, force_optional=True))
            lines.append('')
            lines.append('')

            # --- Assign request model (if user_id field exists) ---
            if any(f['name'] == 'user_id' for f in fields):
                lines.append(f'class AssignRequest(BaseModel):')
                lines.append(f'    """Schema for assigning a resource to a user."""')
                lines.append(f'    user_id: int')
                lines.append('')
                lines.append('')

        return {"models_code": '\n'.join(lines)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _render_field(self, field: dict, force_optional: bool = False) -> str:
        """Render a single Pydantic field line."""
        name = field['name']
        py_type = self.TYPE_MAP.get(field.get('type', 'str'), 'str')
        optional = force_optional or field.get('optional', False)
        default = field.get('default')

        if force_optional:
            # Update models: everything is Optional with None default
            return f'    {name}: Optional[{py_type}] = None'
        elif optional:
            if default is not None:
                return f'    {name}: Optional[{py_type}] = "{default}"' if isinstance(default, str) else f'    {name}: Optional[{py_type}] = {default}'
            return f'    {name}: Optional[{py_type}] = None'
        else:
            if default is not None:
                return f'    {name}: {py_type} = "{default}"' if isinstance(default, str) else f'    {name}: {py_type} = {default}'
            return f'    {name}: {py_type}'

"""
RouterAgent - Generates FastAPI router code from endpoint specifications.
"""

from graphbus_core import GraphBusNode, schema_method, depends_on


@depends_on("SpecParserAgent")
class RouterAgent(GraphBusNode):
    SYSTEM_PROMPT = "You generate FastAPI router code from endpoint specifications."

    @schema_method(
        input_schema={"endpoints": list, "service_name": str},
        output_schema={"router_code": str}
    )
    def generate_router(self, endpoints: list, service_name: str) -> dict:
        """Generate a FastAPI router module from a list of endpoint definitions."""
        if not endpoints:
            raise ValueError("'endpoints' must be a non-empty list")
        if not isinstance(service_name, str) or not service_name.strip():
            raise ValueError("'service_name' must be a non-empty string")

        lines = [
            '"""',
            f'FastAPI router for {service_name}',
            '"""',
            '',
            'from typing import List, Optional',
            '',
            'from fastapi import APIRouter, HTTPException, Query',
            '',
            'from models import (',
        ]

        # Collect model names referenced by endpoints
        model_names = set()
        for ep in endpoints:
            if ep.get('response_model'):
                model_names.add(ep['response_model'])
            if ep.get('request_body'):
                model_names.add(ep['request_body'])
        for m in sorted(model_names):
            lines.append(f'    {m},')
        lines.append(')')
        lines.append('')
        lines.append(f'router = APIRouter(prefix="", tags=["{service_name}"])')
        lines.append('')

        # In-memory store
        resource = self._detect_resource(endpoints)
        lines.append(f'# In-memory store for demo purposes')
        lines.append(f'{resource}_db: dict[int, dict] = {{}}')
        lines.append(f'_next_id: int = 1')
        lines.append('')

        # Sort endpoints: static paths before parameterised paths so
        # FastAPI matches /tasks/filter before /tasks/{task_id}
        sorted_eps = sorted(endpoints, key=lambda e: ('{' in e['path'], e['path']))

        for ep in sorted_eps:
            lines.extend(self._render_endpoint(ep, resource))
            lines.append('')

        return {"router_code": '\n'.join(lines)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_resource(endpoints: list) -> str:
        """Detect the main resource name from endpoint paths."""
        for ep in endpoints:
            parts = ep['path'].strip('/').split('/')
            if parts:
                return parts[0]
        return 'items'

    def _render_endpoint(self, ep: dict, resource: str) -> list:
        """Render a single endpoint as FastAPI route code lines."""
        method = ep['method'].lower()
        path = ep['path']
        desc = ep.get('description', '')
        request_body = ep.get('request_body')
        response_model = ep.get('response_model')
        query_params = ep.get('query_params', [])

        singular = resource.rstrip('s')
        id_param = f'{singular}_id'

        lines = []

        # --- LIST all ---
        if method == 'get' and path == f'/{resource}':
            resp = f', response_model=List[{response_model}]' if response_model else ''
            lines.append(f'@router.get("/{resource}"{resp})')
            lines.append(f'def list_{resource}():')
            lines.append(f'    """List all {resource}."""')
            lines.append(f'    return [{{**v, "id": k}} for k, v in {resource}_db.items()]')

        # --- FILTER ---
        elif method == 'get' and '/filter' in path:
            resp = f', response_model=List[{response_model}]' if response_model else ''
            params_sig = ', '.join(
                f'{p}: Optional[str] = Query(None)' for p in query_params
            )
            lines.append(f'@router.get("/{resource}/filter"{resp})')
            lines.append(f'def filter_{resource}({params_sig}):')
            lines.append(f'    """Filter {resource} by query parameters."""')
            lines.append(f'    results = list({resource}_db.values())')
            for p in query_params:
                lines.append(f'    if {p} is not None:')
                lines.append(f'        results = [r for r in results if r.get("{p}") == {p}]')
            lines.append(f'    return results')

        # --- GET by id ---
        elif method == 'get' and f'{{{id_param}}}' in path:
            resp = f', response_model={response_model}' if response_model else ''
            lines.append(f'@router.get("/{resource}/{{{id_param}}}"{resp})')
            lines.append(f'def get_{singular}({id_param}: int):')
            lines.append(f'    """Get a {singular} by ID."""')
            lines.append(f'    if {id_param} not in {resource}_db:')
            lines.append(f'        raise HTTPException(status_code=404, detail="{singular.title()} not found")')
            lines.append(f'    return {{**{resource}_db[{id_param}], "id": {id_param}}}')

        # --- CREATE ---
        elif method == 'post' and path == f'/{resource}':
            resp = f', response_model={response_model}' if response_model else ''
            body = f'payload: {request_body}' if request_body else ''
            lines.append(f'@router.post("/{resource}"{resp}, status_code=201)')
            lines.append(f'def create_{singular}({body}):')
            lines.append(f'    """Create a new {singular}."""')
            lines.append(f'    global _next_id')
            lines.append(f'    data = payload.model_dump()')
            lines.append(f'    {resource}_db[_next_id] = data')
            lines.append(f'    result = {{**data, "id": _next_id}}')
            lines.append(f'    _next_id += 1')
            lines.append(f'    return result')

        # --- UPDATE ---
        elif method == 'put' and path == f'/{resource}/{{{id_param}}}':
            resp = f', response_model={response_model}' if response_model else ''
            body = f'{id_param}: int, payload: {request_body}' if request_body else f'{id_param}: int'
            lines.append(f'@router.put("/{resource}/{{{id_param}}}"{resp})')
            lines.append(f'def update_{singular}({body}):')
            lines.append(f'    """Update an existing {singular}."""')
            lines.append(f'    if {id_param} not in {resource}_db:')
            lines.append(f'        raise HTTPException(status_code=404, detail="{singular.title()} not found")')
            lines.append(f'    updates = payload.model_dump(exclude_unset=True)')
            lines.append(f'    {resource}_db[{id_param}].update(updates)')
            lines.append(f'    return {{**{resource}_db[{id_param}], "id": {id_param}}}')

        # --- DELETE ---
        elif method == 'delete':
            lines.append(f'@router.delete("/{resource}/{{{id_param}}}", status_code=204)')
            lines.append(f'def delete_{singular}({id_param}: int):')
            lines.append(f'    """Delete a {singular}."""')
            lines.append(f'    if {id_param} not in {resource}_db:')
            lines.append(f'        raise HTTPException(status_code=404, detail="{singular.title()} not found")')
            lines.append(f'    del {resource}_db[{id_param}]')
            lines.append(f'    return None')

        # --- ASSIGN ---
        elif method == 'put' and '/assign' in path:
            resp = f', response_model={response_model}' if response_model else ''
            body = f'{id_param}: int, payload: {request_body}' if request_body else f'{id_param}: int'
            lines.append(f'@router.put("/{resource}/{{{id_param}}}/assign"{resp})')
            lines.append(f'def assign_{singular}({body}):')
            lines.append(f'    """Assign {singular} to a user."""')
            lines.append(f'    if {id_param} not in {resource}_db:')
            lines.append(f'        raise HTTPException(status_code=404, detail="{singular.title()} not found")')
            lines.append(f'    {resource}_db[{id_param}]["user_id"] = payload.user_id')
            lines.append(f'    return {{**{resource}_db[{id_param}], "id": {id_param}}}')

        # --- MARK COMPLETE ---
        elif method == 'put' and '/complete' in path:
            resp = f', response_model={response_model}' if response_model else ''
            lines.append(f'@router.put("/{resource}/{{{id_param}}}/complete"{resp})')
            lines.append(f'def complete_{singular}({id_param}: int):')
            lines.append(f'    """Mark {singular} as complete."""')
            lines.append(f'    if {id_param} not in {resource}_db:')
            lines.append(f'        raise HTTPException(status_code=404, detail="{singular.title()} not found")')
            lines.append(f'    {resource}_db[{id_param}]["status"] = "completed"')
            lines.append(f'    return {{**{resource}_db[{id_param}], "id": {id_param}}}')

        else:
            # Fallback for unrecognised patterns
            lines.append(f'# TODO: implement {method.upper()} {path} — {desc}')

        return lines

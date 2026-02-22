"""
TestAgent - Writes pytest test stubs for FastAPI endpoints.
"""

from graphbus_core import GraphBusNode, schema_method, subscribe, depends_on


@depends_on("RouterAgent")
class TestAgent(GraphBusNode):
    SYSTEM_PROMPT = "You write pytest test stubs for FastAPI endpoints."

    @schema_method(
        input_schema={"endpoints": list, "service_name": str},
        output_schema={"test_code": str}
    )
    def generate_tests(self, endpoints: list, service_name: str) -> dict:
        """Generate pytest test stubs covering all endpoints."""
        if not endpoints:
            raise ValueError("'endpoints' must be a non-empty list")

        lines = [
            '"""',
            f'Tests for {service_name}',
            '"""',
            '',
            'import pytest',
            'from fastapi.testclient import TestClient',
            '',
            'from main import app',
            '',
            '',
            '@pytest.fixture',
            'def client():',
            '    """Create a test client."""',
            '    return TestClient(app)',
            '',
        ]

        resource = self._detect_resource(endpoints)
        singular = resource.rstrip('s')

        # Helper: create a sample resource for tests that need one
        lines.extend([
            '',
            f'@pytest.fixture',
            f'def sample_{singular}(client):',
            f'    """Create a sample {singular} for testing."""',
            f'    payload = {self._sample_create_payload(singular)}',
            f'    response = client.post("/{resource}", json=payload)',
            f'    assert response.status_code == 201',
            f'    return response.json()',
            '',
            '',
        ])

        for ep in endpoints:
            lines.extend(self._render_test(ep, resource, singular))
            lines.append('')

        return {"test_code": '\n'.join(lines)}

    @subscribe("/Service/Generated")
    def on_service_generated(self, event):
        """Auto-generate tests when a service is generated."""
        endpoints = event.get('endpoints', [])
        service_name = event.get('service_name', 'service')
        result = self.generate_tests(endpoints, service_name)
        print(f"[TestAgent] Generated test stubs for {len(endpoints)} endpoints")
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_resource(endpoints: list) -> str:
        for ep in endpoints:
            parts = ep['path'].strip('/').split('/')
            if parts:
                return parts[0]
        return 'items'

    @staticmethod
    def _sample_create_payload(singular: str) -> str:
        """Return a representative JSON payload for creating a resource."""
        if singular == 'task':
            return '{"title": "Test task", "description": "A task for testing", "status": "pending", "priority": "medium"}'
        return '{"name": "Test item"}'

    def _render_test(self, ep: dict, resource: str, singular: str) -> list:
        """Render a single test function."""
        method = ep['method'].lower()
        path = ep['path']
        desc = ep.get('description', f'{method.upper()} {path}')
        func_name = self._test_name(method, path, resource, singular)

        lines = []

        # --- LIST ---
        if method == 'get' and path == f'/{resource}':
            lines.extend([
                f'def test_{func_name}(client):',
                f'    """Test: {desc}."""',
                f'    response = client.get("/{resource}")',
                f'    assert response.status_code == 200',
                f'    assert isinstance(response.json(), list)',
            ])

        # --- FILTER ---
        elif method == 'get' and '/filter' in path:
            qparams = ep.get('query_params', [])
            qs = '&'.join(f'{p}=test' for p in qparams) if qparams else ''
            url = f'/{resource}/filter?{qs}' if qs else f'/{resource}/filter'
            lines.extend([
                f'def test_{func_name}(client, sample_{singular}):',
                f'    """Test: {desc}."""',
                f'    response = client.get("{url}")',
                f'    assert response.status_code == 200',
                f'    assert isinstance(response.json(), list)',
            ])

        # --- GET by id ---
        elif method == 'get' and f'{{{singular}_id}}' in path:
            lines.extend([
                f'def test_{func_name}(client, sample_{singular}):',
                f'    """Test: {desc}."""',
                f'    {singular}_id = sample_{singular}["id"]',
                f'    response = client.get(f"/{resource}/{{{singular}_id}}")',
                f'    assert response.status_code == 200',
                f'    assert response.json()["id"] == {singular}_id',
            ])
            lines.append('')
            lines.extend([
                f'def test_{func_name}_not_found(client):',
                f'    """Test: {desc} with invalid ID."""',
                f'    response = client.get("/{resource}/99999")',
                f'    assert response.status_code == 404',
            ])

        # --- CREATE ---
        elif method == 'post':
            lines.extend([
                f'def test_{func_name}(client):',
                f'    """Test: {desc}."""',
                f'    payload = {self._sample_create_payload(singular)}',
                f'    response = client.post("/{resource}", json=payload)',
                f'    assert response.status_code == 201',
                f'    data = response.json()',
                f'    assert "id" in data',
            ])

        # --- UPDATE ---
        elif method == 'put' and path == f'/{resource}/{{{singular}_id}}':
            lines.extend([
                f'def test_{func_name}(client, sample_{singular}):',
                f'    """Test: {desc}."""',
                f'    {singular}_id = sample_{singular}["id"]',
                f'    response = client.put(',
                f'        f"/{resource}/{{{singular}_id}}",',
                f'        json={{"title": "Updated title"}}',
                f'    )',
                f'    assert response.status_code == 200',
                f'    assert response.json()["title"] == "Updated title"',
            ])

        # --- DELETE ---
        elif method == 'delete':
            lines.extend([
                f'def test_{func_name}(client, sample_{singular}):',
                f'    """Test: {desc}."""',
                f'    {singular}_id = sample_{singular}["id"]',
                f'    response = client.delete(f"/{resource}/{{{singular}_id}}")',
                f'    assert response.status_code == 204',
                f'    # Verify deletion',
                f'    response = client.get(f"/{resource}/{{{singular}_id}}")',
                f'    assert response.status_code == 404',
            ])

        # --- ASSIGN ---
        elif method == 'put' and '/assign' in path:
            lines.extend([
                f'def test_{func_name}(client, sample_{singular}):',
                f'    """Test: {desc}."""',
                f'    {singular}_id = sample_{singular}["id"]',
                f'    response = client.put(',
                f'        f"/{resource}/{{{singular}_id}}/assign",',
                f'        json={{"user_id": 42}}',
                f'    )',
                f'    assert response.status_code == 200',
                f'    assert response.json()["user_id"] == 42',
            ])

        # --- MARK COMPLETE ---
        elif method == 'put' and '/complete' in path:
            lines.extend([
                f'def test_{func_name}(client, sample_{singular}):',
                f'    """Test: {desc}."""',
                f'    {singular}_id = sample_{singular}["id"]',
                f'    response = client.put(f"/{resource}/{{{singular}_id}}/complete")',
                f'    assert response.status_code == 200',
                f'    assert response.json()["status"] == "completed"',
            ])

        else:
            lines.extend([
                f'def test_{func_name}(client):',
                f'    """Test: {desc} (stub)."""',
                f'    pytest.skip("Not yet implemented")',
            ])

        return lines

    @staticmethod
    def _test_name(method: str, path: str, resource: str, singular: str) -> str:
        """Generate a descriptive test function name from an endpoint."""
        if method == 'get' and path == f'/{resource}':
            return f'list_{resource}'
        if method == 'get' and '/filter' in path:
            return f'filter_{resource}'
        if method == 'get':
            return f'get_{singular}'
        if method == 'post':
            return f'create_{singular}'
        if method == 'put' and '/assign' in path:
            return f'assign_{singular}'
        if method == 'put' and '/complete' in path:
            return f'complete_{singular}'
        if method == 'put':
            return f'update_{singular}'
        if method == 'delete':
            return f'delete_{singular}'
        safe = path.replace('/', '_').replace('{', '').replace('}', '').strip('_')
        return f'{method}_{safe}'

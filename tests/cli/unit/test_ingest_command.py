"""
Tests for `graphbus ingest` command — TDD-first.

Tests the full ingest pipeline:
1. Static code analysis (no imports needed)
2. Agent boundary detection (grouping files into agents)
3. YAML agent definition generation
4. graph.yaml generation
5. ~/.graphbus/ project memory structure
"""

import json
import os
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_python_project(tmp_path):
    """Create a minimal Python project to ingest."""
    # API module
    api_dir = tmp_path / "myapp" / "api"
    api_dir.mkdir(parents=True)
    (tmp_path / "myapp" / "__init__.py").write_text("")
    (api_dir / "__init__.py").write_text("")

    (api_dir / "routes.py").write_text(textwrap.dedent("""\
        from fastapi import FastAPI, APIRouter

        router = APIRouter()

        @router.get("/users")
        def list_users():
            \"\"\"List all users.\"\"\"
            return []

        @router.post("/users")
        def create_user(name: str, email: str):
            \"\"\"Create a new user.\"\"\"
            return {"name": name, "email": email}

        @router.get("/users/{user_id}")
        def get_user(user_id: int):
            \"\"\"Get a user by ID.\"\"\"
            return {"id": user_id}
    """))

    (api_dir / "auth.py").write_text(textwrap.dedent("""\
        import jwt

        def verify_token(token: str) -> dict:
            \"\"\"Verify a JWT token and return claims.\"\"\"
            return jwt.decode(token, "secret", algorithms=["HS256"])

        def create_token(user_id: int) -> str:
            \"\"\"Create a JWT token for a user.\"\"\"
            return jwt.encode({"user_id": user_id}, "secret", algorithm="HS256")
    """))

    # Frontend / pages module
    pages_dir = tmp_path / "myapp" / "pages"
    pages_dir.mkdir()
    (pages_dir / "__init__.py").write_text("")

    (pages_dir / "dashboard.py").write_text(textwrap.dedent("""\
        def render_dashboard(user):
            \"\"\"Render the dashboard page.\"\"\"
            return f"<h1>Welcome {user['name']}</h1>"
    """))

    # Models
    models_dir = tmp_path / "myapp" / "models"
    models_dir.mkdir()
    (models_dir / "__init__.py").write_text("")

    (models_dir / "user.py").write_text(textwrap.dedent("""\
        from dataclasses import dataclass

        @dataclass
        class User:
            id: int
            name: str
            email: str
    """))

    return tmp_path


@pytest.fixture
def sample_js_project(tmp_path):
    """Create a minimal JS/TS project to ingest."""
    src = tmp_path / "src"
    src.mkdir()

    (src / "server.ts").write_text(textwrap.dedent("""\
        import express from 'express';
        import { authRouter } from './routes/auth';
        import { userRouter } from './routes/users';

        const app = express();
        app.use('/auth', authRouter);
        app.use('/users', userRouter);
        export default app;
    """))

    routes = src / "routes"
    routes.mkdir()

    (routes / "auth.ts").write_text(textwrap.dedent("""\
        import { Router } from 'express';
        export const authRouter = Router();

        authRouter.post('/login', (req, res) => {
            res.json({ token: 'abc' });
        });
    """))

    (routes / "users.ts").write_text(textwrap.dedent("""\
        import { Router } from 'express';
        export const userRouter = Router();

        userRouter.get('/', (req, res) => {
            res.json([]);
        });

        userRouter.post('/', (req, res) => {
            const { name, email } = req.body;
            res.json({ name, email });
        });
    """))

    (tmp_path / "package.json").write_text(json.dumps({
        "name": "myapp",
        "version": "1.0.0",
        "dependencies": {"express": "^4.18.0"}
    }))

    return tmp_path


@pytest.fixture
def graphbus_output_dir(tmp_path):
    """Temp dir for .graphbus output."""
    return tmp_path / ".graphbus"


@pytest.fixture
def home_graphbus_dir(tmp_path):
    """Temp dir simulating ~/.graphbus/."""
    return tmp_path / "home_graphbus"


# ─── Module: Static Analyzer ─────────────────────────────────────────────────

class TestStaticAnalyzer:
    """Tests for the static code analyzer that works without imports."""

    def test_detect_python_project(self, sample_python_project):
        from graphbus_core.ingest.analyzer import detect_language
        result = detect_language(sample_python_project)
        assert result == "python"

    def test_detect_js_project(self, sample_js_project):
        from graphbus_core.ingest.analyzer import detect_language
        result = detect_language(sample_js_project)
        assert result in ("javascript", "typescript")

    def test_scan_python_files(self, sample_python_project):
        from graphbus_core.ingest.analyzer import scan_source_files
        files = scan_source_files(sample_python_project)
        # Should find all .py files (excluding __init__.py)
        filenames = [f.name for f in files]
        assert "routes.py" in filenames
        assert "auth.py" in filenames
        assert "dashboard.py" in filenames
        assert "user.py" in filenames

    def test_scan_respects_gitignore(self, sample_python_project):
        from graphbus_core.ingest.analyzer import scan_source_files
        # Add a .gitignore
        (sample_python_project / ".gitignore").write_text("myapp/models/\n")
        # Add a venv dir that should be auto-excluded
        venv = sample_python_project / "venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "something.py").write_text("x = 1")

        files = scan_source_files(sample_python_project)
        filenames = [f.name for f in files]
        assert "user.py" not in filenames
        assert "something.py" not in filenames

    def test_extract_python_functions(self, sample_python_project):
        from graphbus_core.ingest.analyzer import extract_symbols
        routes_file = sample_python_project / "myapp" / "api" / "routes.py"
        symbols = extract_symbols(routes_file)
        func_names = [s["name"] for s in symbols if s["type"] == "function"]
        assert "list_users" in func_names
        assert "create_user" in func_names
        assert "get_user" in func_names

    def test_extract_python_classes(self, sample_python_project):
        from graphbus_core.ingest.analyzer import extract_symbols
        user_file = sample_python_project / "myapp" / "models" / "user.py"
        symbols = extract_symbols(user_file)
        class_names = [s["name"] for s in symbols if s["type"] == "class"]
        assert "User" in class_names

    def test_extract_python_imports(self, sample_python_project):
        from graphbus_core.ingest.analyzer import extract_imports
        routes_file = sample_python_project / "myapp" / "api" / "routes.py"
        imports = extract_imports(routes_file)
        assert any("fastapi" in imp for imp in imports)

    def test_extract_function_signatures(self, sample_python_project):
        from graphbus_core.ingest.analyzer import extract_symbols
        routes_file = sample_python_project / "myapp" / "api" / "routes.py"
        symbols = extract_symbols(routes_file)
        create_user = next(s for s in symbols if s["name"] == "create_user")
        assert "name" in create_user["params"]
        assert "email" in create_user["params"]

    def test_extract_docstrings(self, sample_python_project):
        from graphbus_core.ingest.analyzer import extract_symbols
        routes_file = sample_python_project / "myapp" / "api" / "routes.py"
        symbols = extract_symbols(routes_file)
        create_user = next(s for s in symbols if s["name"] == "create_user")
        assert create_user["docstring"] == "Create a new user."


# ─── Module: Agent Boundary Detection ────────────────────────────────────────

class TestAgentBoundaryDetector:
    """Tests for grouping files into logical agent boundaries."""

    def test_group_by_directory(self, sample_python_project):
        from graphbus_core.ingest.boundary import detect_boundaries
        from graphbus_core.ingest.analyzer import scan_source_files, extract_symbols

        files = scan_source_files(sample_python_project)
        file_data = []
        for f in files:
            symbols = extract_symbols(f)
            file_data.append({"path": f, "symbols": symbols})

        boundaries = detect_boundaries(file_data, strategy="directory")

        # Should create agents per directory: api, pages, models
        agent_names = [b["name"] for b in boundaries]
        assert any("api" in name.lower() for name in agent_names)
        assert any("pages" in name.lower() or "dashboard" in name.lower() for name in agent_names)
        assert any("models" in name.lower() or "user" in name.lower() for name in agent_names)

    def test_each_boundary_has_files(self, sample_python_project):
        from graphbus_core.ingest.boundary import detect_boundaries
        from graphbus_core.ingest.analyzer import scan_source_files, extract_symbols

        files = scan_source_files(sample_python_project)
        file_data = [{"path": f, "symbols": extract_symbols(f)} for f in files]

        boundaries = detect_boundaries(file_data, strategy="directory")

        for boundary in boundaries:
            assert len(boundary["files"]) > 0, f"Agent {boundary['name']} has no files"

    def test_no_file_in_multiple_agents(self, sample_python_project):
        from graphbus_core.ingest.boundary import detect_boundaries
        from graphbus_core.ingest.analyzer import scan_source_files, extract_symbols

        files = scan_source_files(sample_python_project)
        file_data = [{"path": f, "symbols": extract_symbols(f)} for f in files]

        boundaries = detect_boundaries(file_data, strategy="directory")

        all_files = []
        for boundary in boundaries:
            all_files.extend([str(f) for f in boundary["files"]])
        assert len(all_files) == len(set(all_files)), "A file appears in multiple agents"

    def test_boundary_has_description(self, sample_python_project):
        from graphbus_core.ingest.boundary import detect_boundaries
        from graphbus_core.ingest.analyzer import scan_source_files, extract_symbols

        files = scan_source_files(sample_python_project)
        file_data = [{"path": f, "symbols": extract_symbols(f)} for f in files]

        boundaries = detect_boundaries(file_data, strategy="directory")

        for boundary in boundaries:
            assert "description" in boundary
            assert len(boundary["description"]) > 0


# ─── Module: YAML Generator ──────────────────────────────────────────────────

class TestYAMLGenerator:
    """Tests for generating .graphbus/ YAML files."""

    def test_generate_agent_yaml(self, sample_python_project, graphbus_output_dir):
        from graphbus_core.ingest.generator import generate_agent_yaml

        boundary = {
            "name": "APIAgent",
            "description": "Handles REST API routes and authentication",
            "files": [
                sample_python_project / "myapp" / "api" / "routes.py",
                sample_python_project / "myapp" / "api" / "auth.py",
            ],
            "symbols": [
                {"name": "list_users", "type": "function", "params": {},
                 "docstring": "List all users.", "file": "myapp/api/routes.py"},
                {"name": "create_user", "type": "function",
                 "params": {"name": "str", "email": "str"},
                 "docstring": "Create a new user.", "file": "myapp/api/routes.py"},
            ]
        }

        yaml_path = generate_agent_yaml(boundary, graphbus_output_dir, sample_python_project)

        assert yaml_path.exists()
        assert yaml_path.name == "APIAgent.yaml"

        content = yaml.safe_load(yaml_path.read_text())
        assert content["name"] == "APIAgent"
        assert "source_files" in content
        assert "system_prompt" in content
        assert len(content["system_prompt"]) > 0
        assert "methods" in content

    def test_generate_graph_yaml(self, graphbus_output_dir):
        from graphbus_core.ingest.generator import generate_graph_yaml

        boundaries = [
            {
                "name": "APIAgent",
                "description": "REST API",
                "files": [Path("myapp/api/routes.py")],
                "imports_from": ["models"],
            },
            {
                "name": "ModelsAgent",
                "description": "Data models",
                "files": [Path("myapp/models/user.py")],
                "imports_from": [],
            },
        ]

        graph_path = generate_graph_yaml(boundaries, graphbus_output_dir)

        assert graph_path.exists()
        content = yaml.safe_load(graph_path.read_text())
        assert "agents" in content
        assert "edges" in content
        assert len(content["agents"]) == 2

        # Check dependency edge exists
        edge_targets = [(e["from"], e["to"]) for e in content["edges"]]
        assert ("APIAgent", "ModelsAgent") in edge_targets

    def test_generated_yaml_is_valid(self, sample_python_project, graphbus_output_dir):
        from graphbus_core.ingest.generator import generate_agent_yaml

        boundary = {
            "name": "TestAgent",
            "description": "Test",
            "files": [sample_python_project / "myapp" / "api" / "routes.py"],
            "symbols": []
        }

        yaml_path = generate_agent_yaml(boundary, graphbus_output_dir, sample_python_project)

        # Should be valid YAML
        content = yaml.safe_load(yaml_path.read_text())
        assert isinstance(content, dict)

        # Required fields
        for field in ("name", "source_files", "system_prompt"):
            assert field in content, f"Missing required field: {field}"


# ─── Module: Project Memory (~/. graphbus/) ──────────────────────────────────

class TestProjectMemory:
    """Tests for ~/.graphbus/ project memory structure."""

    def test_init_project_memory(self, sample_python_project, home_graphbus_dir):
        from graphbus_core.ingest.memory import init_project_memory

        project_id = init_project_memory(
            project_path=sample_python_project,
            home_dir=home_graphbus_dir,
        )

        project_dir = home_graphbus_dir / "projects" / project_id
        assert project_dir.exists()
        assert (project_dir / "context.json").exists()

        context = json.loads((project_dir / "context.json").read_text())
        assert context["project_path"] == str(sample_python_project)
        assert "created_at" in context

    def test_project_memory_preserves_existing(self, sample_python_project, home_graphbus_dir):
        from graphbus_core.ingest.memory import init_project_memory

        # First init
        project_id = init_project_memory(sample_python_project, home_graphbus_dir)
        project_dir = home_graphbus_dir / "projects" / project_id

        # Write some negotiation history
        neg_dir = project_dir / "negotiations"
        neg_dir.mkdir(exist_ok=True)
        (neg_dir / "neg_001.json").write_text('{"result": "accepted"}')

        # Re-init should preserve negotiations
        init_project_memory(sample_python_project, home_graphbus_dir)
        assert (neg_dir / "neg_001.json").exists()

    def test_project_id_deterministic(self, sample_python_project, home_graphbus_dir):
        from graphbus_core.ingest.memory import get_project_id

        id1 = get_project_id(sample_python_project)
        id2 = get_project_id(sample_python_project)
        assert id1 == id2

    def test_project_id_uses_dirname(self, sample_python_project, home_graphbus_dir):
        from graphbus_core.ingest.memory import get_project_id

        project_id = get_project_id(sample_python_project)
        # Should include the directory name for human readability
        assert sample_python_project.name in project_id


# ─── Module: Dependency Inference ─────────────────────────────────────────────

class TestDependencyInference:
    """Tests for inferring edges between agents from import analysis."""

    def test_infer_deps_from_imports(self, sample_python_project):
        from graphbus_core.ingest.deps import infer_dependencies

        boundaries = [
            {
                "name": "APIAgent",
                "files": [
                    sample_python_project / "myapp" / "api" / "routes.py",
                    sample_python_project / "myapp" / "api" / "auth.py",
                ],
                "module_prefix": "myapp.api",
            },
            {
                "name": "ModelsAgent",
                "files": [
                    sample_python_project / "myapp" / "models" / "user.py",
                ],
                "module_prefix": "myapp.models",
            },
        ]

        # Add an import from api -> models
        routes = sample_python_project / "myapp" / "api" / "routes.py"
        content = routes.read_text()
        routes.write_text("from myapp.models.user import User\n" + content)

        edges = infer_dependencies(boundaries, sample_python_project)
        assert ("APIAgent", "ModelsAgent") in edges

    def test_no_self_dependency(self, sample_python_project):
        from graphbus_core.ingest.deps import infer_dependencies

        boundaries = [
            {
                "name": "APIAgent",
                "files": [
                    sample_python_project / "myapp" / "api" / "routes.py",
                    sample_python_project / "myapp" / "api" / "auth.py",
                ],
                "module_prefix": "myapp.api",
            },
        ]

        edges = infer_dependencies(boundaries, sample_python_project)
        assert ("APIAgent", "APIAgent") not in edges


# ─── Integration: Full Ingest Pipeline ────────────────────────────────────────

class TestIngestPipeline:
    """End-to-end tests for the full ingest command."""

    def test_full_ingest_creates_graphbus_dir(self, sample_python_project, home_graphbus_dir):
        from graphbus_core.ingest.pipeline import run_ingest

        result = run_ingest(
            project_path=sample_python_project,
            home_dir=home_graphbus_dir,
        )

        graphbus_dir = sample_python_project / ".graphbus"
        assert graphbus_dir.exists()
        assert (graphbus_dir / "graph.yaml").exists()
        assert (graphbus_dir / "agents").is_dir()

        # Should have at least one agent YAML
        agent_files = list((graphbus_dir / "agents").glob("*.yaml"))
        assert len(agent_files) > 0

    def test_full_ingest_creates_home_memory(self, sample_python_project, home_graphbus_dir):
        from graphbus_core.ingest.pipeline import run_ingest

        run_ingest(
            project_path=sample_python_project,
            home_dir=home_graphbus_dir,
        )

        # Should create project entry in ~/.graphbus/
        projects = list((home_graphbus_dir / "projects").iterdir())
        assert len(projects) == 1

    def test_ingest_is_idempotent(self, sample_python_project, home_graphbus_dir):
        from graphbus_core.ingest.pipeline import run_ingest

        run_ingest(project_path=sample_python_project, home_dir=home_graphbus_dir)
        first_agents = sorted([
            f.name for f in (sample_python_project / ".graphbus" / "agents").glob("*.yaml")
        ])

        run_ingest(project_path=sample_python_project, home_dir=home_graphbus_dir)
        second_agents = sorted([
            f.name for f in (sample_python_project / ".graphbus" / "agents").glob("*.yaml")
        ])

        assert first_agents == second_agents

    def test_ingest_result_summary(self, sample_python_project, home_graphbus_dir):
        from graphbus_core.ingest.pipeline import run_ingest

        result = run_ingest(
            project_path=sample_python_project,
            home_dir=home_graphbus_dir,
        )

        assert "agents" in result
        assert "edges" in result
        assert "files_analyzed" in result
        assert result["files_analyzed"] > 0
        assert len(result["agents"]) > 0


# ─── CLI Command ──────────────────────────────────────────────────────────────

class TestIngestCLICommand:
    """Tests for the `graphbus ingest` CLI entry point."""

    def test_cli_registers_ingest_command(self):
        from graphbus_cli.commands.ingest import register
        # Should be importable and have a register function
        assert callable(register)

    def test_cli_ingest_runs(self, sample_python_project, home_graphbus_dir):
        from click.testing import CliRunner
        from graphbus_cli.commands.ingest import ingest

        runner = CliRunner()
        result = runner.invoke(ingest, [
            str(sample_python_project),
            "--home-dir", str(home_graphbus_dir),
        ])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "agents" in result.output.lower() or "ingested" in result.output.lower()

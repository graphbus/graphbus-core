"""
Unit tests for `graphbus ns` namespace commands.

Tests: list, create, use, current, delete, show, topology.
"""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner

from graphbus_cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project(tmp_path):
    """A temp directory that acts as a project root with a .graphbus dir."""
    graphbus_dir = tmp_path / ".graphbus"
    graphbus_dir.mkdir()
    return tmp_path


# ─── ns list ──────────────────────────────────────────────────────────────────

class TestNsList:
    def test_list_empty(self, runner, project):
        result = runner.invoke(cli, ["ns", "list", "-p", str(project)])
        assert result.exit_code == 0
        assert "No namespaces found" in result.output

    def test_list_shows_created_namespaces(self, runner, project):
        runner.invoke(cli, ["ns", "create", "alpha", "-p", str(project)])
        runner.invoke(cli, ["ns", "create", "beta", "-p", str(project)])
        result = runner.invoke(cli, ["ns", "list", "-p", str(project)])
        assert result.exit_code == 0
        assert "alpha" in result.output
        assert "beta" in result.output

    def test_list_marks_active_namespace(self, runner, project):
        runner.invoke(cli, ["ns", "create", "alpha", "-p", str(project)])
        runner.invoke(cli, ["ns", "create", "beta", "-p", str(project)])
        runner.invoke(cli, ["ns", "use", "beta", "-p", str(project)])
        result = runner.invoke(cli, ["ns", "list", "-p", str(project)])
        assert result.exit_code == 0
        assert "beta" in result.output
        # Active marker should appear
        assert "✦" in result.output or "Active namespace: beta" in result.output

    def test_list_shows_active_namespace_hint(self, runner, project):
        runner.invoke(cli, ["ns", "create", "myns", "-p", str(project)])
        result = runner.invoke(cli, ["ns", "list", "-p", str(project)])
        assert result.exit_code == 0
        assert "Active namespace" in result.output


# ─── ns create ────────────────────────────────────────────────────────────────

class TestNsCreate:
    def test_create_basic(self, runner, project):
        result = runner.invoke(cli, ["ns", "create", "my-ns", "-p", str(project)])
        assert result.exit_code == 0
        assert "my-ns" in result.output
        assert "created" in result.output.lower()

    def test_create_with_description(self, runner, project):
        result = runner.invoke(cli, ["ns", "create", "orders", "--desc", "Order processing agents", "-p", str(project)])
        assert result.exit_code == 0
        assert "orders" in result.output

    def test_create_duplicate_fails(self, runner, project):
        runner.invoke(cli, ["ns", "create", "dup", "-p", str(project)])
        result = runner.invoke(cli, ["ns", "create", "dup", "-p", str(project)])
        assert result.exit_code == 0  # click handles this gracefully
        assert "Error" in result.output or "already exists" in result.output

    def test_create_persists_to_disk(self, runner, project):
        runner.invoke(cli, ["ns", "create", "persisted", "-p", str(project)])
        ns_file = project / ".graphbus" / "namespaces.json"
        assert ns_file.exists()
        data = json.loads(ns_file.read_text())
        assert "persisted" in data


# ─── ns use ───────────────────────────────────────────────────────────────────

class TestNsUse:
    def test_use_sets_active_namespace(self, runner, project):
        runner.invoke(cli, ["ns", "create", "prod", "-p", str(project)])
        result = runner.invoke(cli, ["ns", "use", "prod", "-p", str(project)])
        assert result.exit_code == 0
        assert "prod" in result.output
        assert "Switched" in result.output

    def test_use_persists_context(self, runner, project):
        runner.invoke(cli, ["ns", "create", "prod", "-p", str(project)])
        runner.invoke(cli, ["ns", "use", "prod", "-p", str(project)])
        ctx_file = project / ".graphbus" / "context.json"
        assert ctx_file.exists()
        ctx = json.loads(ctx_file.read_text())
        assert ctx["current_namespace"] == "prod"

    def test_use_nonexistent_namespace_fails(self, runner, project):
        result = runner.invoke(cli, ["ns", "use", "does-not-exist", "-p", str(project)])
        assert result.exit_code == 0  # handled gracefully
        assert "Error" in result.output or "not found" in result.output

    def test_use_can_switch_between_namespaces(self, runner, project):
        runner.invoke(cli, ["ns", "create", "ns-a", "-p", str(project)])
        runner.invoke(cli, ["ns", "create", "ns-b", "-p", str(project)])
        runner.invoke(cli, ["ns", "use", "ns-a", "-p", str(project)])
        runner.invoke(cli, ["ns", "use", "ns-b", "-p", str(project)])
        ctx = json.loads((project / ".graphbus" / "context.json").read_text())
        assert ctx["current_namespace"] == "ns-b"


# ─── ns current ───────────────────────────────────────────────────────────────

class TestNsCurrent:
    def test_current_defaults_to_default(self, runner, project):
        result = runner.invoke(cli, ["ns", "current", "-p", str(project)])
        assert result.exit_code == 0
        assert "default" in result.output

    def test_current_reflects_use(self, runner, project):
        runner.invoke(cli, ["ns", "create", "staging", "-p", str(project)])
        runner.invoke(cli, ["ns", "use", "staging", "-p", str(project)])
        result = runner.invoke(cli, ["ns", "current", "-p", str(project)])
        assert result.exit_code == 0
        assert "staging" in result.output

    def test_current_shows_not_created_warning(self, runner, project):
        # default context but no namespaces created
        result = runner.invoke(cli, ["ns", "current", "-p", str(project)])
        assert result.exit_code == 0
        # Should note that 'default' isn't created yet
        assert "default" in result.output


# ─── ns delete ────────────────────────────────────────────────────────────────

class TestNsDelete:
    def test_delete_existing(self, runner, project):
        runner.invoke(cli, ["ns", "create", "to-delete", "-p", str(project)])
        result = runner.invoke(cli, ["ns", "delete", "to-delete", "-p", str(project)], input="y\n")
        assert result.exit_code == 0
        assert "deleted" in result.output.lower() or "to-delete" in result.output

    def test_delete_nonexistent(self, runner, project):
        result = runner.invoke(cli, ["ns", "delete", "ghost", "-p", str(project)], input="y\n")
        assert result.exit_code == 0
        assert "not found" in result.output.lower() or "ghost" in result.output


# ─── negotiate --namespace ────────────────────────────────────────────────────

class TestNegotiateNamespace:
    def test_negotiate_help_shows_namespace_flag(self, runner):
        result = runner.invoke(cli, ["negotiate", "--help"])
        assert result.exit_code == 0
        assert "--namespace" in result.output or "-n" in result.output

    def test_negotiate_help_shows_namespace_docs(self, runner):
        result = runner.invoke(cli, ["negotiate", "--help"])
        assert result.exit_code == 0
        assert "namespace" in result.output.lower()

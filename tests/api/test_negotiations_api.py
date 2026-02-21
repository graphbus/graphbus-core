"""
Tests for the /api/negotiations REST API.

Covers: auth, session CRUD, proposals, commits, feedback, health.
"""
import pytest
from fastapi.testclient import TestClient


# ── Helpers ──────────────────────────────────────────────────────────────────

def create_session(client, auth_headers, intent="Refactor auth module"):
    resp = client.post("/api/negotiations", json={"intent": intent}, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


# ── Health / root ─────────────────────────────────────────────────────────────

class TestHealthEndpoints:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_root(self, client):
        resp = client.get("/")
        body = resp.json()
        assert resp.status_code == 200
        assert "negotiations" in body["endpoints"]
        assert "build" in body["endpoints"]


# ── Authentication ────────────────────────────────────────────────────────────

class TestAuth:
    def test_missing_key_rejected(self, client):
        resp = client.post("/api/negotiations", json={"intent": "test"})
        assert resp.status_code == 422  # missing header = unprocessable

    def test_wrong_key_rejected(self, client, bad_headers):
        resp = client.post("/api/negotiations", json={"intent": "test"}, headers=bad_headers)
        assert resp.status_code == 401

    def test_correct_key_accepted(self, client, auth_headers):
        resp = client.post("/api/negotiations", json={"intent": "test"}, headers=auth_headers)
        assert resp.status_code == 201

    def test_all_endpoints_require_auth(self, client, bad_headers):
        """Every negotiations endpoint rejects a bad key."""
        endpoints = [
            ("GET",   "/api/negotiations"),
            ("POST",  "/api/negotiations"),
            ("GET",   "/api/negotiations/fake-id"),
            ("PATCH", "/api/negotiations/fake-id"),
            ("POST",  "/api/negotiations/fake-id/proposals"),
            ("GET",   "/api/negotiations/fake-id/proposals"),
            ("POST",  "/api/negotiations/fake-id/commits"),
            ("GET",   "/api/negotiations/fake-id/commits"),
            ("POST",  "/api/negotiations/fake-id/feedback"),
        ]
        for method, url in endpoints:
            resp = client.request(method, url, headers=bad_headers, json={})
            assert resp.status_code == 401, f"{method} {url} should require auth"


# ── Session CRUD ──────────────────────────────────────────────────────────────

class TestSessionCRUD:
    def test_create_returns_session(self, client, auth_headers):
        data = create_session(client, auth_headers, "Extract payment logic")
        assert data["intent"] == "Extract payment logic"
        assert data["status"] == "in_progress"
        assert data["session_id"].startswith("negotiate_")
        assert data["branch_name"].startswith("graphbus/negotiate-")
        assert data["commit_count"] == 0
        assert data["developer_feedback"] == []

    def test_get_session(self, client, auth_headers):
        session = create_session(client, auth_headers)
        sid = session["session_id"]
        resp = client.get(f"/api/negotiations/{sid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["session_id"] == sid

    def test_get_unknown_session_404(self, client, auth_headers):
        resp = client.get("/api/negotiations/does-not-exist", headers=auth_headers)
        assert resp.status_code == 404

    def test_list_sessions_empty(self, client, auth_headers):
        resp = client.get("/api/negotiations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_sessions_multiple(self, client, auth_headers):
        create_session(client, auth_headers, "Task A")
        create_session(client, auth_headers, "Task B")
        resp = client.get("/api/negotiations", headers=auth_headers)
        assert len(resp.json()) == 2

    def test_list_sessions_filter_by_status(self, client, auth_headers):
        s1 = create_session(client, auth_headers, "Task A")
        s2 = create_session(client, auth_headers, "Task B")

        # Mark one as completed
        client.patch(
            f"/api/negotiations/{s1['session_id']}",
            json={"status": "completed"},
            headers=auth_headers,
        )

        resp = client.get("/api/negotiations?status=completed", headers=auth_headers)
        sessions = resp.json()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == s1["session_id"]

        resp = client.get("/api/negotiations?status=in_progress", headers=auth_headers)
        assert len(resp.json()) == 1

    def test_update_session_status(self, client, auth_headers):
        session = create_session(client, auth_headers)
        sid = session["session_id"]

        resp = client.patch(
            f"/api/negotiations/{sid}",
            json={"status": "completed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_update_session_pr_info(self, client, auth_headers):
        session = create_session(client, auth_headers)
        sid = session["session_id"]

        resp = client.patch(
            f"/api/negotiations/{sid}",
            json={"pr_number": 42, "pr_url": "https://github.com/org/repo/pull/42"},
            headers=auth_headers,
        )
        body = resp.json()
        assert body["pr_number"] == 42
        assert body["pr_url"] == "https://github.com/org/repo/pull/42"

    def test_update_session_modified_files(self, client, auth_headers):
        session = create_session(client, auth_headers)
        sid = session["session_id"]

        resp = client.patch(
            f"/api/negotiations/{sid}",
            json={"modified_files": ["auth.py", "models.py"]},
            headers=auth_headers,
        )
        assert resp.json()["modified_files"] == ["auth.py", "models.py"]

    def test_update_unknown_session_404(self, client, auth_headers):
        resp = client.patch(
            "/api/negotiations/ghost-id",
            json={"status": "completed"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_update_with_no_fields_400(self, client, auth_headers):
        session = create_session(client, auth_headers)
        sid = session["session_id"]
        resp = client.patch(f"/api/negotiations/{sid}", json={}, headers=auth_headers)
        assert resp.status_code == 400


# ── Proposals ─────────────────────────────────────────────────────────────────

class TestProposals:
    def test_add_and_get_proposal(self, client, auth_headers):
        session = create_session(client, auth_headers)
        sid = session["session_id"]

        proposal = {
            "agent": "AuthServiceAgent",
            "type": "code_change",
            "file": "auth.py",
            "description": "Extract token validation into a helper",
            "diff": "--- a/auth.py\n+++ b/auth.py\n...",
        }

        resp = client.post(
            f"/api/negotiations/{sid}/proposals",
            json=proposal,
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "ok"

        resp = client.get(f"/api/negotiations/{sid}/proposals", headers=auth_headers)
        proposals = resp.json()
        assert len(proposals) == 1
        assert proposals[0]["agent"] == "AuthServiceAgent"

    def test_multiple_proposals(self, client, auth_headers):
        session = create_session(client, auth_headers)
        sid = session["session_id"]

        for i in range(3):
            client.post(
                f"/api/negotiations/{sid}/proposals",
                json={"agent": f"Agent{i}", "description": f"Proposal {i}"},
                headers=auth_headers,
            )

        proposals = client.get(f"/api/negotiations/{sid}/proposals", headers=auth_headers).json()
        assert len(proposals) == 3

    def test_proposal_unknown_session_404(self, client, auth_headers):
        resp = client.post(
            "/api/negotiations/no-such-session/proposals",
            json={"agent": "X"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get_proposals_unknown_session_404(self, client, auth_headers):
        resp = client.get("/api/negotiations/no-such-session/proposals", headers=auth_headers)
        assert resp.status_code == 404


# ── Commits ───────────────────────────────────────────────────────────────────

class TestCommits:
    def test_add_and_get_commit(self, client, auth_headers):
        session = create_session(client, auth_headers)
        sid = session["session_id"]

        commit = {
            "sha": "abc123def456",
            "message": "refactor: extract token validation helper",
            "author": "AuthServiceAgent",
            "files_changed": ["auth.py"],
        }

        resp = client.post(
            f"/api/negotiations/{sid}/commits",
            json=commit,
            headers=auth_headers,
        )
        assert resp.status_code == 201

        commits = client.get(f"/api/negotiations/{sid}/commits", headers=auth_headers).json()
        assert len(commits) == 1
        assert commits[0]["sha"] == "abc123def456"

    def test_commit_increments_count(self, client, auth_headers):
        session = create_session(client, auth_headers)
        sid = session["session_id"]

        assert client.get(f"/api/negotiations/{sid}", headers=auth_headers).json()["commit_count"] == 0

        client.post(f"/api/negotiations/{sid}/commits", json={"sha": "aaa"}, headers=auth_headers)
        assert client.get(f"/api/negotiations/{sid}", headers=auth_headers).json()["commit_count"] == 1

        client.post(f"/api/negotiations/{sid}/commits", json={"sha": "bbb"}, headers=auth_headers)
        assert client.get(f"/api/negotiations/{sid}", headers=auth_headers).json()["commit_count"] == 2

    def test_commit_unknown_session_404(self, client, auth_headers):
        resp = client.post(
            "/api/negotiations/ghost/commits",
            json={"sha": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get_commits_unknown_session_404(self, client, auth_headers):
        resp = client.get("/api/negotiations/ghost/commits", headers=auth_headers)
        assert resp.status_code == 404


# ── Feedback ──────────────────────────────────────────────────────────────────

class TestFeedback:
    def test_add_feedback(self, client, auth_headers):
        session = create_session(client, auth_headers)
        sid = session["session_id"]

        resp = client.post(
            f"/api/negotiations/{sid}/feedback",
            json={"author": "sravan", "body": "Looks good, but watch the edge case in validate()"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

        # Feedback shows up on the session
        session_data = client.get(f"/api/negotiations/{sid}", headers=auth_headers).json()
        feedback = session_data["developer_feedback"]
        assert len(feedback) == 1
        assert feedback[0]["author"] == "sravan"
        assert "validate" in feedback[0]["body"]

    def test_multiple_feedback_entries(self, client, auth_headers):
        session = create_session(client, auth_headers)
        sid = session["session_id"]

        for i in range(3):
            client.post(
                f"/api/negotiations/{sid}/feedback",
                json={"author": f"reviewer{i}", "body": f"Comment {i}"},
                headers=auth_headers,
            )

        session_data = client.get(f"/api/negotiations/{sid}", headers=auth_headers).json()
        assert len(session_data["developer_feedback"]) == 3

    def test_feedback_unknown_session_404(self, client, auth_headers):
        resp = client.post(
            "/api/negotiations/ghost/feedback",
            json={"author": "x", "body": "y"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ── Session isolation ─────────────────────────────────────────────────────────

class TestIsolation:
    """Proposals/commits/feedback on one session don't leak to another."""

    def test_proposals_isolated_between_sessions(self, client, auth_headers):
        s1 = create_session(client, auth_headers, "Session 1")
        s2 = create_session(client, auth_headers, "Session 2")

        client.post(
            f"/api/negotiations/{s1['session_id']}/proposals",
            json={"agent": "A", "note": "only for s1"},
            headers=auth_headers,
        )

        assert len(client.get(f"/api/negotiations/{s1['session_id']}/proposals", headers=auth_headers).json()) == 1
        assert len(client.get(f"/api/negotiations/{s2['session_id']}/proposals", headers=auth_headers).json()) == 0

    def test_commits_isolated_between_sessions(self, client, auth_headers):
        s1 = create_session(client, auth_headers)
        s2 = create_session(client, auth_headers)

        client.post(
            f"/api/negotiations/{s1['session_id']}/commits",
            json={"sha": "only-s1"},
            headers=auth_headers,
        )

        assert client.get(f"/api/negotiations/{s1['session_id']}", headers=auth_headers).json()["commit_count"] == 1
        assert client.get(f"/api/negotiations/{s2['session_id']}", headers=auth_headers).json()["commit_count"] == 0

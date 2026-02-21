"""
Tests for NegotiationClient — the HTTP wrapper around /api/negotiations.

Uses respx to mock httpx calls. The actual API behaviour is covered
end-to-end in test_negotiations_api.py via FastAPI TestClient.
These tests verify:
  - correct HTTP method + URL + headers on every call
  - correct JSON parsing of responses
  - NegotiationClientError raised on 4xx / 5xx
"""
import pytest
import httpx
import respx

from graphbus_core.agents.negotiation_client import NegotiationClient, NegotiationClientError

BASE = "http://api.graphbus.test"
KEY  = "test-key-xyz"
HEADERS = {"X-Api-Key": KEY}


@pytest.fixture()
def nc():
    return NegotiationClient(base_url=BASE, api_key=KEY)


SESSION_PAYLOAD = {
    "session_id": "negotiate_abc12345",
    "intent": "Refactor auth module",
    "status": "in_progress",
    "timestamp": 1_700_000_000.0,
    "branch_name": "graphbus/negotiate-refactor-auth",
    "pr_number": None,
    "pr_url": None,
    "modified_files": [],
    "commit_count": 0,
    "developer_feedback": [],
    "created_at": 1_700_000_000.0,
}


# ── create_session ────────────────────────────────────────────────────────────

class TestCreateSession:
    @respx.mock
    def test_posts_to_correct_url(self, nc):
        route = respx.post(f"{BASE}/api/negotiations").mock(
            return_value=httpx.Response(201, json=SESSION_PAYLOAD)
        )
        result = nc.create_session("Refactor auth module")
        assert route.called
        assert result["session_id"] == "negotiate_abc12345"
        assert result["intent"] == "Refactor auth module"

    @respx.mock
    def test_sends_api_key_header(self, nc):
        route = respx.post(f"{BASE}/api/negotiations").mock(
            return_value=httpx.Response(201, json=SESSION_PAYLOAD)
        )
        nc.create_session("test")
        request = route.calls.last.request
        assert request.headers.get("x-api-key") == KEY

    @respx.mock
    def test_raises_on_401(self, nc):
        respx.post(f"{BASE}/api/negotiations").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid API key"})
        )
        with pytest.raises(NegotiationClientError, match="401"):
            nc.create_session("test")


# ── get_session ───────────────────────────────────────────────────────────────

class TestGetSession:
    @respx.mock
    def test_gets_from_correct_url(self, nc):
        sid = "negotiate_abc12345"
        respx.get(f"{BASE}/api/negotiations/{sid}").mock(
            return_value=httpx.Response(200, json=SESSION_PAYLOAD)
        )
        result = nc.get_session(sid)
        assert result["session_id"] == sid

    @respx.mock
    def test_returns_none_on_404(self, nc):
        respx.get(f"{BASE}/api/negotiations/ghost").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )
        assert nc.get_session("ghost") is None

    @respx.mock
    def test_raises_on_500(self, nc):
        respx.get(f"{BASE}/api/negotiations/sid").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(NegotiationClientError, match="500"):
            nc.get_session("sid")


# ── list_sessions ─────────────────────────────────────────────────────────────

class TestListSessions:
    @respx.mock
    def test_lists_without_filter(self, nc):
        respx.get(f"{BASE}/api/negotiations").mock(
            return_value=httpx.Response(200, json=[SESSION_PAYLOAD])
        )
        results = nc.list_sessions()
        assert len(results) == 1

    @respx.mock
    def test_passes_status_query_param(self, nc):
        route = respx.get(f"{BASE}/api/negotiations").mock(
            return_value=httpx.Response(200, json=[SESSION_PAYLOAD])
        )
        nc.list_sessions(status="completed")
        assert "status=completed" in str(route.calls.last.request.url)

    @respx.mock
    def test_no_param_when_status_none(self, nc):
        route = respx.get(f"{BASE}/api/negotiations").mock(
            return_value=httpx.Response(200, json=[])
        )
        nc.list_sessions()
        assert "status" not in str(route.calls.last.request.url)


# ── update_session ────────────────────────────────────────────────────────────

class TestUpdateSession:
    @respx.mock
    def test_patches_correct_url(self, nc):
        sid = "negotiate_abc12345"
        updated = {**SESSION_PAYLOAD, "status": "completed"}
        route = respx.patch(f"{BASE}/api/negotiations/{sid}").mock(
            return_value=httpx.Response(200, json=updated)
        )
        result = nc.update_session(sid, status="completed")
        assert route.called
        assert result["status"] == "completed"

    @respx.mock
    def test_raises_on_404(self, nc):
        respx.patch(f"{BASE}/api/negotiations/ghost").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )
        with pytest.raises(NegotiationClientError, match="404"):
            nc.update_session("ghost", status="completed")


# ── record_proposal ───────────────────────────────────────────────────────────

class TestRecordProposal:
    @respx.mock
    def test_posts_proposal(self, nc):
        sid = "negotiate_abc12345"
        route = respx.post(f"{BASE}/api/negotiations/{sid}/proposals").mock(
            return_value=httpx.Response(201, json={"status": "ok"})
        )
        nc.record_proposal(sid, {"agent": "AuthAgent", "description": "Extract helper"})
        assert route.called

    @respx.mock
    def test_raises_on_404(self, nc):
        respx.post(f"{BASE}/api/negotiations/ghost/proposals").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )
        with pytest.raises(NegotiationClientError, match="404"):
            nc.record_proposal("ghost", {"agent": "X"})


# ── get_proposals ─────────────────────────────────────────────────────────────

class TestGetProposals:
    @respx.mock
    def test_returns_proposal_list(self, nc):
        sid = "negotiate_abc12345"
        proposals = [{"agent": "A"}, {"agent": "B"}]
        respx.get(f"{BASE}/api/negotiations/{sid}/proposals").mock(
            return_value=httpx.Response(200, json=proposals)
        )
        result = nc.get_proposals(sid)
        assert result == proposals

    @respx.mock
    def test_raises_on_404(self, nc):
        respx.get(f"{BASE}/api/negotiations/ghost/proposals").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )
        with pytest.raises(NegotiationClientError, match="404"):
            nc.get_proposals("ghost")


# ── record_commit ─────────────────────────────────────────────────────────────

class TestRecordCommit:
    @respx.mock
    def test_posts_commit(self, nc):
        sid = "negotiate_abc12345"
        route = respx.post(f"{BASE}/api/negotiations/{sid}/commits").mock(
            return_value=httpx.Response(201, json={"status": "ok"})
        )
        nc.record_commit(sid, {"sha": "deadbeef", "message": "refactor: extract helper"})
        assert route.called

    @respx.mock
    def test_raises_on_404(self, nc):
        respx.post(f"{BASE}/api/negotiations/ghost/commits").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )
        with pytest.raises(NegotiationClientError, match="404"):
            nc.record_commit("ghost", {"sha": "x"})


# ── get_commits ───────────────────────────────────────────────────────────────

class TestGetCommits:
    @respx.mock
    def test_returns_commit_list(self, nc):
        sid = "negotiate_abc12345"
        commits = [{"sha": "aaa"}, {"sha": "bbb"}]
        respx.get(f"{BASE}/api/negotiations/{sid}/commits").mock(
            return_value=httpx.Response(200, json=commits)
        )
        result = nc.get_commits(sid)
        assert result == commits

    @respx.mock
    def test_raises_on_404(self, nc):
        respx.get(f"{BASE}/api/negotiations/ghost/commits").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )
        with pytest.raises(NegotiationClientError, match="404"):
            nc.get_commits("ghost")


# ── add_feedback ──────────────────────────────────────────────────────────────

class TestAddFeedback:
    @respx.mock
    def test_posts_feedback(self, nc):
        sid = "negotiate_abc12345"
        route = respx.post(f"{BASE}/api/negotiations/{sid}/feedback").mock(
            return_value=httpx.Response(201, json={"status": "ok"})
        )
        nc.add_feedback(sid, author="sravan", body="Ship it")
        assert route.called
        import json
        body = json.loads(route.calls.last.request.content)
        assert body["author"] == "sravan"
        assert body["body"] == "Ship it"

    @respx.mock
    def test_raises_on_404(self, nc):
        respx.post(f"{BASE}/api/negotiations/ghost/feedback").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )
        with pytest.raises(NegotiationClientError, match="404"):
            nc.add_feedback("ghost", author="x", body="y")

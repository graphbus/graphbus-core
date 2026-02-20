"""
HTTP client for the GraphBus negotiations web service.

Mirrors the NegotiationSessionManager interface so it can be used
as a remote backend.
"""

from typing import Optional

import httpx


class NegotiationClientError(Exception):
    """Raised when an HTTP request to the negotiations API fails."""


class NegotiationClient:
    """Thin wrapper around the /api/negotiations REST API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {"X-Api-Key": api_key}

    # -- helpers --

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/negotiations{path}"

    def _raise_on_error(self, resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            detail = resp.text
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            raise NegotiationClientError(
                f"HTTP {resp.status_code} from {resp.request.url}: {detail}"
            )

    # -- session CRUD --

    def create_session(self, intent: str) -> dict:
        with httpx.Client() as client:
            resp = client.post(
                self._url(""),
                json={"intent": intent},
                headers=self._headers,
            )
        self._raise_on_error(resp)
        return resp.json()

    def get_session(self, session_id: str) -> Optional[dict]:
        with httpx.Client() as client:
            resp = client.get(
                self._url(f"/{session_id}"),
                headers=self._headers,
            )
        if resp.status_code == 404:
            return None
        self._raise_on_error(resp)
        return resp.json()

    def list_sessions(self, status: Optional[str] = None) -> list[dict]:
        params: dict = {}
        if status:
            params["status"] = status
        with httpx.Client() as client:
            resp = client.get(
                self._url(""),
                params=params,
                headers=self._headers,
            )
        self._raise_on_error(resp)
        return resp.json()

    def update_session(self, session_id: str, **kwargs: object) -> dict:
        with httpx.Client() as client:
            resp = client.patch(
                self._url(f"/{session_id}"),
                json=kwargs,
                headers=self._headers,
            )
        self._raise_on_error(resp)
        return resp.json()

    # -- proposals --

    def record_proposal(self, session_id: str, proposal: dict) -> None:
        with httpx.Client() as client:
            resp = client.post(
                self._url(f"/{session_id}/proposals"),
                json=proposal,
                headers=self._headers,
            )
        self._raise_on_error(resp)

    def get_proposals(self, session_id: str) -> list[dict]:
        with httpx.Client() as client:
            resp = client.get(
                self._url(f"/{session_id}/proposals"),
                headers=self._headers,
            )
        self._raise_on_error(resp)
        return resp.json()

    # -- commits --

    def record_commit(self, session_id: str, commit_record: dict) -> None:
        with httpx.Client() as client:
            resp = client.post(
                self._url(f"/{session_id}/commits"),
                json=commit_record,
                headers=self._headers,
            )
        self._raise_on_error(resp)

    def get_commits(self, session_id: str) -> list[dict]:
        with httpx.Client() as client:
            resp = client.get(
                self._url(f"/{session_id}/commits"),
                headers=self._headers,
            )
        self._raise_on_error(resp)
        return resp.json()

    # -- feedback --

    def add_feedback(self, session_id: str, author: str, body: str) -> None:
        with httpx.Client() as client:
            resp = client.post(
                self._url(f"/{session_id}/feedback"),
                json={"author": author, "body": body},
                headers=self._headers,
            )
        self._raise_on_error(resp)

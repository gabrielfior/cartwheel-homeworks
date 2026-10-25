"""Offline authentication tests for the Homework 2 endpoint.

No Langfuse, Docker, or model key: these call the route functions directly.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from server import app as server_app


@pytest.fixture(autouse=True)
def isolated_sessions(world, monkeypatch) -> None:
    """Fresh session registry and in-memory history store for every test."""
    monkeypatch.setattr(server_app, "_SESSIONS", {})
    monkeypatch.setattr(server_app, "SESSIONS_DB", ":memory:")


def test_create_session_rejects_role_that_differs_from_database() -> None:
    # User 1 is a shopper in the seeded database; the client claims support.
    with pytest.raises(HTTPException) as exc:
        server_app.create_session(server_app.SessionCreate(user_id=1, role="support"))

    assert exc.value.status_code == 403
    assert server_app._SESSIONS == {}  # no session was created


def test_token_for_one_session_cannot_authorize_another() -> None:
    first = server_app.create_session(server_app.SessionCreate(user_id=1, role="shopper"))
    second = server_app.create_session(
        server_app.SessionCreate(user_id=9002, role="merchant")
    )

    with pytest.raises(HTTPException) as exc:
        server_app._authorize(second["session_id"], f"Bearer {first['token']}")
    assert exc.value.status_code == 403

    # Control: the same token does work for the session it was issued for.
    ctx = server_app._authorize(first["session_id"], f"Bearer {first['token']}")
    assert ctx.user_id == 1 and ctx.role == "shopper"

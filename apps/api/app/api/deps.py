"""Shared FastAPI dependencies (guest session cart)."""

from __future__ import annotations

from fastapi import Header, Response

from app.repositories import cart as cart_repo

SESSION_HEADER = "X-Session-Token"
SESSION_COOKIE = "vs_session"


def resolve_session_token(
    response: Response,
    x_session_token: str | None = Header(default=None, alias=SESSION_HEADER),
) -> str:
    """Use client-provided session token or mint a new one (returned via header)."""
    token = (x_session_token or "").strip()
    if not token:
        token = cart_repo.new_session_token()
    response.headers[SESSION_HEADER] = token
    return token

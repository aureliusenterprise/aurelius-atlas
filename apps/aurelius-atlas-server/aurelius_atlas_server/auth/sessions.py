"""Server-side sessions: the ``ATLASSESSIONID`` store of a logged-in user (AUTH-08, AUTH-09).

Atlas keeps sessions in the servlet container (``SessionCreationPolicy.ALWAYS`` of ``AtlasSecurityConfig``,
the session attribute of ``AtlasCSRFPreventionFilter``); this is the same in-process store for one server
process (DD-037 — shared state across replicas is not planned).
"""

import secrets
import string
import time
from dataclasses import dataclass, field
from typing import Any

CSRF_TOKEN_LENGTH = 20
_CSRF_ALPHABET = string.ascii_letters + string.digits


def csrf_token() -> str:
    """A new random CSRF token of 20 letters and digits, as ``AdminResource.getUserProfile`` makes one."""
    return "".join(secrets.choice(_CSRF_ALPHABET) for _ in range(CSRF_TOKEN_LENGTH))


@dataclass
class Session:
    """One logged-in user's session."""

    sid: str
    username: str
    groups: list[str]
    csrf_token: str
    access_token: str
    refresh_token: str | None
    access_expires_at: float
    """``time.monotonic()`` at which the access token expires (AUTH-09)."""

    created_at: float
    last_used_at: float
    """Wall time, so the idle check survives a restart of the monotonic clock being irrelevant."""

    transient: dict[str, Any] = field(default_factory=dict)
    """Per-login scratch (``state``/``nonce``/``next`` of the flow, removed once used)."""


class SessionStore:
    """The in-memory sessions keyed by their id cookie (AUTH-08)."""

    def __init__(self, *, idle_seconds: int | None = None) -> None:
        self._sessions: dict[str, Session] = {}
        self._idle_seconds = idle_seconds

    def __len__(self) -> int:
        return len(self._sessions)

    def create(
        self,
        *,
        username: str,
        groups: list[str],
        access_token: str,
        refresh_token: str | None,
        access_expires_at: float,
    ) -> Session:
        """A new session for an authenticated user (AUTH-07)."""
        now = time.time()
        session = Session(
            sid=secrets.token_urlsafe(32),
            username=username,
            groups=groups,
            csrf_token=csrf_token(),
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires_at,
            created_at=now,
            last_used_at=now,
        )
        self._sessions[session.sid] = session
        return session

    def get(self, sid: str | None) -> Session | None:
        """The session for a cookie value, or None.

        An idle session is destroyed here rather than answered (AUTH-07 of the session timeout, ADM-07);
        a hit refreshes its idle clock (AUTH-08).
        """
        if sid is None:
            return None
        session = self._sessions.get(sid)
        if session is None:
            return None
        if self._idle_seconds is not None and time.time() - session.last_used_at > self._idle_seconds:
            del self._sessions[sid]
            return None
        session.last_used_at = time.time()
        return session

    def destroy(self, sid: str | None) -> Session | None:
        """Remove and return the session, for logout (AUTH-10) or a failed refresh (AUTH-09)."""
        if sid is None:
            return None
        return self._sessions.pop(sid, None)

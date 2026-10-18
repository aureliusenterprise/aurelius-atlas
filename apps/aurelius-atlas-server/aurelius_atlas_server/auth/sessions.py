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

MAX_LIFETIME_SECONDS = 8 * 3600
"""The absolute bound on a session's life (DD-041): with no idle timeout configured, this is the
retention policy — a session is gone by its next store activity after it, however often it was used."""


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

    access_lifetime_seconds: float = 300.0
    """The access token's issued lifetime: caps the refresh window, so a short-lived token refreshes
    within its own lifetime (AUTH-09)."""

    transient: dict[str, Any] = field(default_factory=dict)
    """Per-login scratch (``state``/``nonce``/``next`` of the flow, removed once used)."""


class SessionStore:
    """The in-memory sessions keyed by their id cookie (AUTH-08)."""

    def __init__(self, *, idle_seconds: int | None = None, max_lifetime_seconds: float = MAX_LIFETIME_SECONDS) -> None:
        self._sessions: dict[str, Session] = {}
        self._idle_seconds = idle_seconds
        self._max_lifetime_seconds = max_lifetime_seconds

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
        self._sweep()
        now = time.time()
        session = Session(
            sid=secrets.token_urlsafe(32),
            username=username,
            groups=groups,
            csrf_token=csrf_token(),
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires_at,
            # The expiry handed in was minted as "now + expires_in", so the difference here recovers
            # the token's issued lifetime — the value the refresh window is capped by (AUTH-09).
            access_lifetime_seconds=max(access_expires_at - time.monotonic(), 0.0),
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
        self._sweep()
        if sid is None:
            return None
        return self._sessions.pop(sid, None)

    def _sweep(self) -> None:
        """Drop every expired session, whether or not its cookie is being presented (DD-041).

        Runs on store activity — the events that grow the store — so a closed browser or a replaced
        cookie cannot leave a session resident for the process's lifetime: each is gone by the next
        activity after it went idle (when a timeout is configured) or past its absolute lifetime.
        """
        now = time.time()
        for sid in [
            sid
            for sid, session in self._sessions.items()
            if (self._idle_seconds is not None and now - session.last_used_at > self._idle_seconds)
            or now - session.created_at > self._max_lifetime_seconds
        ]:
            del self._sessions[sid]

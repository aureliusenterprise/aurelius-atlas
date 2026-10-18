"""The session store and the CSRF check (AUTH-08, ADM-07, CRS-01 to CRS-03)."""

import re
import time

import pytest
from aurelius_atlas_server.auth.csrf import CUSTOM_HEADER, csrf_rejected, is_browser
from aurelius_atlas_server.auth.sessions import Session, SessionStore, csrf_token
from fastapi import Request

BROWSER = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
CLIENT = "atlas-sdk/0.6"
ACCESS = "at"


def _request(method: str, *, user_agent: str | None = None, xsrf: str | None = None) -> Request:
    headers: dict[str, str] = {}
    if user_agent is not None:
        headers["user-agent"] = user_agent
    if xsrf is not None:
        headers[CUSTOM_HEADER] = xsrf
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": method,
        "path": "/api/atlas/entity",
        "raw_path": b"/api/atlas/entity",
        "query_string": b"",
        "root_path": "",
        "scheme": "https",
        "server": ("aurelius-atlas", 443),
        "client": ("127.0.0.1", 1234),
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
    }
    return Request(scope)


def _create(store: SessionStore) -> Session:
    return store.create(
        username="writer",
        groups=["ADMIN"],
        access_token=ACCESS,
        refresh_token=None,
        access_expires_at=time.monotonic() + 300,
    )


@pytest.mark.covers("aurelius_atlas_server.auth.sessions.csrf_token", rules=["CRS-02"])
def test__a_csrf_token_is_20_letters_and_digits() -> None:
    """Each token has the length and alphabet of the one Atlas mints, and tokens differ."""
    token = csrf_token()

    assert re.fullmatch(r"[A-Za-z0-9]{20}", token)
    assert csrf_token() != token


@pytest.mark.covers(
    "aurelius_atlas_server.auth.sessions.SessionStore.create",
    "aurelius_atlas_server.auth.sessions.SessionStore.get",
    rules=["AUTH-08"],
)
def test__a_session_is_fetched_by_its_id_and_keeps_its_identity() -> None:
    """A created session answers its sid with the user, groups and a token of its own; an unknown sid does not."""
    store = SessionStore()
    session = _create(store)

    fetched = store.get(session.sid)
    assert fetched is session
    assert fetched is not None
    assert fetched.username == "writer"
    assert fetched.groups == ["ADMIN"]
    assert store.get("no-such-sid") is None
    assert store.get(None) is None
    assert len(store) == 1


@pytest.mark.covers("aurelius_atlas_server.auth.sessions.SessionStore.get", rules=["AUTH-08"])
def test__a_request_touches_the_session_and_a_quiet_one_times_out() -> None:
    """The idle clock resets on each get; a session idle past the timeout is destroyed, not answered."""
    store = SessionStore(idle_seconds=60)
    session = _create(store)

    session.last_used_at -= 30
    assert store.get(session.sid) is session  # a hit, 30 s before the timeout: kept and touched
    assert session.last_used_at == pytest.approx(time.time(), abs=2)

    session.last_used_at = time.time() - 61
    assert store.get(session.sid) is None
    assert len(store) == 0  # destroyed, not merely refused


@pytest.mark.covers("aurelius_atlas_server.auth.sessions.SessionStore.destroy", rules=["AUTH-10"])
def test__a_destroyed_session_is_gone() -> None:
    """Logout removes the session; a second destroy and the unknown sid do nothing."""
    store = SessionStore()
    session = _create(store)

    assert store.destroy(session.sid) is session
    assert store.destroy(session.sid) is None
    assert store.destroy(None) is None
    assert len(store) == 0


@pytest.mark.covers("aurelius_atlas_server.auth.csrf.is_browser", rules=["CRS-03"])
@pytest.mark.parametrize(
    ("user_agent", "browser"),
    [
        (BROWSER, True),
        ("Opera/9.80", True),
        ("Chrome/140.0", True),
        (CLIENT, False),
        ("curl/8.5.0", False),
        (None, False),
    ],
)
def test__the_guarded_user_agents_are_the_browsers(user_agent: str | None, *, browser: bool) -> None:
    """Atlas's patterns guard Mozilla, Opera and Chrome user agents; a service client's passes."""
    assert is_browser(user_agent) is browser


@pytest.mark.covers("aurelius_atlas_server.auth.csrf.csrf_rejected", rules=["CRS-01"])
@pytest.mark.parametrize("method", ["GET", "OPTIONS", "HEAD", "TRACE"])
def test__the_ignored_methods_are_never_rejected(method: str) -> None:
    """A browser request without the CSRF header still passes when its method is one Atlas ignores."""
    assert csrf_rejected(_request(method, user_agent=BROWSER), "aCsrfToken") is False


@pytest.mark.covers("aurelius_atlas_server.auth.csrf.csrf_rejected", rules=["CRS-01"])
def test__a_browser_post_must_carry_the_sessions_token() -> None:
    """The header must equal the session's token: a missing, wrong or empty one is refused."""
    request = _request("POST", user_agent=BROWSER)

    assert csrf_rejected(request, "aCsrfToken") is True
    assert csrf_rejected(_request("POST", user_agent=BROWSER, xsrf="wrong"), "aCsrfToken") is True
    assert csrf_rejected(_request("POST", user_agent=BROWSER, xsrf=""), "aCsrfToken") is True
    assert csrf_rejected(_request("POST", user_agent=BROWSER, xsrf="aCsrfToken"), "aCsrfToken") is False


@pytest.mark.covers("aurelius_atlas_server.auth.csrf.csrf_rejected", rules=["CRS-01"])
def test__without_a_session_the_older_empty_token_is_the_comparison() -> None:
    """With no session the filter compares against the empty string: only an empty header passes."""
    assert csrf_rejected(_request("POST", user_agent=BROWSER, xsrf=""), None) is False
    assert csrf_rejected(_request("POST", user_agent=BROWSER), None) is True


@pytest.mark.covers("aurelius_atlas_server.auth.csrf.csrf_rejected", rules=["CRS-03"])
def test__a_service_client_needs_no_csrf_header() -> None:
    """A non-browser user agent carries no session token, and none is asked for (CRS-03)."""
    assert csrf_rejected(_request("POST", user_agent=CLIENT), "aCsrfToken") is False
    assert csrf_rejected(_request("POST"), "aCsrfToken") is False

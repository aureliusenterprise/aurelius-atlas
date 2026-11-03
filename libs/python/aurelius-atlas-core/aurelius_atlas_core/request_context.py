"""``RequestContext``: the user, client address and start time of the request being served (ADA-02).

Atlas keeps them in a thread-local ``RequestContext``; here they are a context variable the server binds for each
request, so the admin audits written deep in a change name who asked for it and from where.
"""

import getpass
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RequestContext:
    """The request's user, its client's address, and when it started in epoch milliseconds."""

    user: str | None = None
    client_ip_address: str | None = None
    request_time: int = field(default_factory=lambda: int(time.time() * 1000))


_CURRENT: ContextVar[RequestContext | None] = ContextVar("aurelius_atlas_request_context", default=None)


def current() -> RequestContext:
    """``RequestContext.get``: the bound request's context, or one of no user and no client, starting now."""
    return _CURRENT.get() or RequestContext()


@contextmanager
def bound(context: RequestContext) -> Iterator[RequestContext]:
    """The context bound while the block runs, the one before it bound again after."""
    token = _CURRENT.set(context)
    try:
        yield context
    finally:
        _CURRENT.reset(token)


def current_user() -> str:
    """``getCurrentUser``: the bound request's user, else the process's login name, else ``atlas`` (ADA-02)."""
    user = current().user
    if user and user.strip():
        return user
    try:
        login = getpass.getuser()
    except KeyError, OSError:  # no name for the process's user
        login = ""
    return login if login.strip() else "atlas"

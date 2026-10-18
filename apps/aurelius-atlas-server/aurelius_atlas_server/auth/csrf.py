"""The CSRF check of ``AtlasCSRFPreventionFilter`` (CRS-01 to CRS-03).

Atlas's filter guards every request whose ``User-Agent`` matches its browser patterns
(``atlas.rest-csrf.browser-useragents-regex``, ``^Mozilla.*,^Opera.*,^Chrome``) and whose method is not in
``atlas.rest-csrf.methods-to-ignore`` (``GET,OPTIONS,HEAD,TRACE``): the request must carry
``atlas.rest-csrf.custom-header`` (``X-XSRF-HEADER`` by default) with the session's ``_csrfToken``. A
rejected request answers 400 with ``{"msgDesc": ...}``. A non-browser ``User-Agent`` — the path service
clients take — passes untouched (CRS-03).
"""

import re

from fastapi import Request
from fastapi.responses import JSONResponse

BROWSER_USERAGENTS = "^Mozilla.*,^Opera.*,^Chrome"
METHODS_TO_IGNORE = frozenset({"GET", "OPTIONS", "HEAD", "TRACE"})
CUSTOM_HEADER = "X-XSRF-HEADER"
"""The header Atlas's filter names in the session response."""

CSRF_DENIED = "Missing header or invalid Header value for CSRF Vulnerability Protection"
"""The message ``AtlasCSRFPreventionFilter`` answers a rejected request with."""


def _browser_patterns(regex: str) -> list[re.Pattern[str]]:
    """The compiled browser patterns, as the filter splits its configuration on commas.

    Atlas compiles Java regexes; the configured patterns (``^Mozilla.*`` …) are identical in Python's
    syntax. A pattern that does not compile is skipped rather than breaking the check.
    """
    patterns: list[re.Pattern[str]] = []
    for part in regex.split(","):
        try:
            patterns.append(re.compile(part))
        except re.error:
            continue
    return patterns


BROWSER_PATTERNS = _browser_patterns(BROWSER_USERAGENTS)


def is_browser(user_agent: str | None) -> bool:
    """Whether a ``User-Agent`` is one of the browsers the filter guards (its ``isBrowser``)."""
    if user_agent is None:
        return False
    return any(pattern.match(user_agent) for pattern in BROWSER_PATTERNS)


def csrf_denied() -> JSONResponse:
    """The 400 answer of the filter, with its JSON body (CRS-01)."""
    return JSONResponse(status_code=400, content={"msgDesc": CSRF_DENIED}, media_type="application/json")


def csrf_rejected(request: Request, session_token: str | None) -> bool:
    """Whether a request must be refused by the CSRF check (CRS-01 to CRS-03).

    Args:
        request: The incoming request; its method, ``User-Agent`` and custom header decide.
        session_token: The CSRF token of the request's session, or None when it has none.
    """
    if not is_browser(request.headers.get("user-agent")):
        return False
    if request.method.upper() in METHODS_TO_IGNORE:
        return False
    client_token = request.headers.get(CUSTOM_HEADER)
    # The filter compares with StringUtils.equals against the session attribute, which is the empty
    # string when the request has no session: only an equally empty header passes then.
    expected = session_token if session_token is not None else ""
    return client_token != expected

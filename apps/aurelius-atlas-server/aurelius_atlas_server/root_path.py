"""The server under a path prefix: ``root_path``, the part of a URL a proxy maps to the server (PFX-01, DD-363).

Uvicorn's ``root_path`` makes every request's path start with it, and its base URL end with it. The checks that
judge a path by where it is in the server read it without the prefix; the redirects the server makes put it back.
"""

from starlette.types import Scope


def site_path(scope: Scope) -> str:
    """The request's path within the server: without its ``root_path`` (PFX-02)."""
    path: str = scope.get("path", "")
    root: str = scope.get("root_path", "")
    if root and (path == root or path.startswith(f"{root}/")):
        return path[len(root) :] or "/"
    return path


def under_root(scope: Scope, path: str) -> str:
    """A path of the server as the browser reaches it: under its ``root_path`` (PFX-03)."""
    return f"{scope.get('root_path', '')}{path}"

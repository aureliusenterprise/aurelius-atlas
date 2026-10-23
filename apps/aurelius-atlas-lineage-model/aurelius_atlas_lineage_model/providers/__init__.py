"""Factories for the app's collaborators: auth, the upstreams, telemetry (DD-118, DD-119).

Each factory builds one collaborator from the settings and nothing else — the
composition root (``app.py``) calls them, and tests replace them by injection
(DD-111's seam). No factory reads the environment: settings in, object out.
"""

from .auth import build_auth
from .telemetry import configure_telemetry, ingest_pipeline
from .upstreams import atlas_breaker, build_upstreams, d2m_breaker, is_upstream_fact, upstream_http

__all__ = [
    "atlas_breaker",
    "build_auth",
    "build_upstreams",
    "configure_telemetry",
    "d2m_breaker",
    "ingest_pipeline",
    "is_upstream_fact",
    "upstream_http",
]

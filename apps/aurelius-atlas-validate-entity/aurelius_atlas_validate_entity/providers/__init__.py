"""The factories that build the app's collaborators: auth, the upstreams, the telemetry (DD-197, DD-209).

The composition root in ``app.py`` wires what these build; the routes serve
requests. Since 12.7 the app has one upstream — the catalogue server the
governance rules are read from — built by the upstreams' factory with the
app's own service identity (VEV-04, DD-499).
"""

from aurelius_atlas_validate_entity.providers.auth import build_auth
from aurelius_atlas_validate_entity.providers.telemetry import configure_telemetry, ingest_pipeline
from aurelius_atlas_validate_entity.providers.upstreams import (
    build_upstreams,
    is_upstream_fact,
    server_breaker,
    upstream_http,
)

__all__ = [
    "build_auth",
    "build_upstreams",
    "configure_telemetry",
    "ingest_pipeline",
    "is_upstream_fact",
    "server_breaker",
    "upstream_http",
]

"""The per-request values a route takes as a dependency (SVC-02, DD-794, DD-799).

FastAPI resolves a dependency once per request and reuses that value, so a route that needs both the store
set and the authorizer sees one resolve of each (DD-799): the store set is where a closed tenant refuses
(SVC-01) and the authorizer is built from the acting user. The dependencies read what ``create_app`` wired on
``app.state``, so the app stays the composition root (DD-794) and a test overrides the dependency instead of
writing app state behind a route's back.
"""

from typing import Annotated

from aurelius_atlas_core.authorization import Granted
from fastapi import Depends, Request

from aurelius_atlas_server.authorization import authorizer
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_server.tenant_stores import TenantStores, stores

__all__ = ["Authorizer", "Settings", "StoreSet", "read_settings"]


def read_settings(request: Request) -> ServerSettings:
    """The server's settings, as ``create_app`` wired them (SVC-02)."""
    settings: ServerSettings = request.app.state.settings
    return settings


Settings = Annotated[ServerSettings, Depends(read_settings)]
"""The settings a route reads through its signature, not through ``request.app.state`` (DD-794)."""

StoreSet = Annotated[TenantStores, Depends(stores)]
"""The store set of the request's tenant, resolved once per request (TSS-06, DD-799)."""

Authorizer = Annotated[Granted, Depends(authorizer)]
"""The request's authorizer, built from its acting user once per request (AUZ-03, DD-799)."""

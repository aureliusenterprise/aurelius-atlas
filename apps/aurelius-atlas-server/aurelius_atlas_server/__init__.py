"""The Aurelius Atlas server: the Apache Atlas 2.4.0 REST API on Elasticsearch."""

from aurelius_atlas_server.app import create_app
from aurelius_atlas_server.settings import ServerSettings

__all__ = ["ServerSettings", "create_app"]

"""The app's routers: the OpenAI-shaped embeddings API and the health probes."""

from aurelius_atlas_embedder.routes.embeddings import EMBEDDINGS
from aurelius_atlas_embedder.routes.health import HEALTH

__all__ = ["EMBEDDINGS", "HEALTH"]

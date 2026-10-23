"""The app's routers: built by factories, mounted by the composition root (``app.py``)."""

from .health import HEALTH
from .lineage import build_router

__all__ = ["HEALTH", "build_router"]

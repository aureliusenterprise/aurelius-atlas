"""The app's name, logger and health answers (EMB-07)."""

import logging

NAME = "aurelius-atlas-embedder"
"""The app's name: the FastAPI title and the logger's name."""

LOGGER = logging.getLogger(NAME)

NO_CONTENT = 204
"""The health probes' answer while the app serves (EMB-07)."""

NOT_READY = 503
"""The readiness probe's answer, and the embeddings', until the model has loaded (EMB-07)."""

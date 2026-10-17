import importlib.metadata
import logging

NAME = "aurelius-atlas-fastapi-example"
METADATA = importlib.metadata.metadata(NAME)

LOGGER = logging.getLogger(NAME)

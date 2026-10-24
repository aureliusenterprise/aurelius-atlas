"""The app's name and logger (VE-01, VE-04)."""

import logging

NAME = "aurelius-atlas-validate-entity"
"""The app's name: the FastAPI title and the logger's name."""

LOGGER = logging.getLogger(NAME)

NO_CONTENT = 204
"""The healthcheck's answer while the process serves (VE-04, DV-59)."""

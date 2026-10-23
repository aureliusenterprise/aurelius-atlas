"""The app's name, logger and wire constants (DTM-01, DTM-11)."""

import logging

NAME = "aurelius-atlas-data2model"
"""The app's name: the FastAPI title and the logger's name."""

LOGGER = logging.getLogger(NAME)

NO_CONTENT = 204
"""The healthcheck's answer while the process serves (DTM-10)."""

BAD_REQUEST = 400
"""The status of a malformed request body (DTM-11, DV-18)."""

ATLAS_ERROR_CODE = "ATLAS-400-00-029"
"""Atlas's code for a request it will not process; the 8.x apps reuse it (DTM-11 family)."""

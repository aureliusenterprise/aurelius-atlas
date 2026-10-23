"""The app's name, logger and wire constants (LM-07, DV-20..DV-22)."""

import logging

NAME = "aurelius-atlas-lineage-model"
"""The app's name: the FastAPI title and the logger's name."""

LOGGER = logging.getLogger(NAME)

BAD_REQUEST = 400
"""The status of a query the app will not process (LM-07, DV-20, DV-21)."""

NOT_FOUND = 404
"""The upstream's answer for a guid it has no lineage for (LM-05)."""

NO_CONTENT = 204
"""The answer for an empty lineage graph (LM-05, LM-06) and the healthcheck (LM-09)."""

BAD_GATEWAY = 502
"""The status of a failing upstream (LM-07, DV-22)."""

SERVER_ERROR = 500
"""The status from which an upstream answer counts as an outage for the circuit (LM-13)."""

FAST_FAIL_ATLAS = "the lineage service is fast-failing"
"""The open-circuit answer for the Atlas feed (LM-12)."""

FAST_FAIL_D2M = "the model extraction is fast-failing"
"""The open-circuit answer for the data2model extract (LM-12)."""

UPSTREAM_TIMEOUT_SECONDS = 10.0
"""How long an upstream call may take before the app gives up on it (DD-111)."""

ATLAS_ERROR_CODE = "ATLAS-400-00-029"
"""Atlas's code for a request it will not process; the 8.x apps reuse it (DTM-11 family)."""

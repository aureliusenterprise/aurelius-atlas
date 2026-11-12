"""The app's name, logger and wire constants (VE-01, VE-04; VEV-01/06, DV-72..DV-80's sibling)."""

import logging

NAME = "aurelius-atlas-validate-entity"
"""The app's name: the FastAPI title and the logger's name."""

LOGGER = logging.getLogger(NAME)

NO_CONTENT = 204
"""The healthcheck's answer while the process serves (VE-04, DV-76)."""

BAD_REQUEST = 400
"""The status of a draft the app will not read (VEV-01, DV-79's posture)."""

BAD_GATEWAY = 502
"""The status of a catalogue this app cannot read (VEV-06, DV-80's sibling)."""

SERVER_ERROR = 500
"""The status from which a catalogue answer counts as an outage for the circuit (VEV-06)."""

FAST_FAIL_SERVER = "the catalogue is fast-failing"
"""The open-circuit answer for the rule read (VEV-06, LM-12's sibling)."""

UPSTREAM_TIMEOUT_SECONDS = 10.0
"""How long a catalogue call may take before the app gives up on it (DD-200's seam)."""

ATLAS_ERROR_CODE = "ATLAS-400-00-029"
"""Atlas's code for a request it will not process; the 8.x apps reuse it (DTM-11 family)."""

"""What the check and the report know of parity scenarios: their test properties and the deviations table.

The property names are set by ``aurelius-atlas-parity`` (DD-014); they change together.
"""

import re
from pathlib import Path

ENDPOINT_PROPERTY = "parity.endpoint"
"""One per endpoint a scenario calls: the method and the URL before substitution, ``GET /api/atlas/admin/version``."""
DEVIATION_PROPERTY = "parity.deviation"
"""One per deviation id a scenario declares."""

_DEVIATION_ROW_PATTERN = re.compile(r"^\|\s*(DV-\d{2,3})\s*\|")


def read_deviation_ids(path: Path) -> set[str]:
    """Read the deviation ids of the deviations table: the rows whose first cell is ``DV-NN`` (SCN-13)."""
    return {row[1] for line in path.read_text().splitlines() if (row := _DEVIATION_ROW_PATTERN.match(line))}

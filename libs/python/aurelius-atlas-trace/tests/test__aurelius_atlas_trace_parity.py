from pathlib import Path

import pytest
from aurelius_atlas_trace.parity import read_deviation_ids


@pytest.mark.covers("aurelius_atlas_trace.parity.read_deviation_ids", rules=["SCN-13"])
def test__read_deviation_ids_reads_the_first_column(tmp_path: Path) -> None:
    """Rows whose first cell is a DV id count; headers, prose and ids elsewhere in a row do not."""
    table = tmp_path / "deviations.md"
    table.write_text(
        "# Deviations\n\nSee DV-09 below.\n\n| # | Area |\n| --- | --- |\n"
        "| DV-01 | Notifications |\n|  DV-102  | Long id |\n| x | mentions DV-03 |\n"
    )

    assert read_deviation_ids(table) == {"DV-01", "DV-102"}

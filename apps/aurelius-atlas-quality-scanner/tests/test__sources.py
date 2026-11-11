"""The dataset reader (DQS-04, DQS-05): format by extension, no guessing, a bounded read."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import polars as pl
import pytest
from aurelius_atlas_quality_scanner.settings import ScannerSettings
from aurelius_atlas_quality_scanner.sources import NO_FILE, NO_SOURCE, TRUNCATED, UNKNOWN_FORMAT, FileReader

CSV_TEXT = "total,region\n1,north\n2,south\n3,north\n"
FRAME = pl.DataFrame({"total": [1, 2, 3], "region": ["north", "south", "north"]})


def _write_extract(root: Path, name: str, fmt: str) -> Path:
    path = root / name
    if fmt == "csv":
        path.write_text(CSV_TEXT)
    elif fmt == "parquet":
        FRAME.write_parquet(path)
    elif fmt == "ndjson":
        path.write_text("".join(f"{json.dumps(row)}\n" for row in FRAME.to_dicts()))
    elif fmt == "json":
        path.write_text(json.dumps(FRAME.to_dicts()))
    else:  # pragma: no cover - guards the helper itself
        raise AssertionError(fmt)
    return path


@pytest.mark.parametrize("fmt", ["csv", "parquet", "ndjson", "json"])
@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.FileReader.read", rules=["DQS-04"])
def test_each_configured_format_reads(tmp_path: Path, settings: Callable[..., ScannerSettings], fmt: str) -> None:
    """DQS-04: each readable extension reads the extract, whichever way its data is stored."""
    path = _write_extract(tmp_path, f"extract.{fmt}", fmt)
    reader = FileReader({"/d3": str(path)}, settings().max_rows)
    read = reader.read("/d3", "g")
    assert read is not None
    assert read.notice is None
    assert read.frame.sort("total").equals(FRAME)


@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.FileReader.read", rules=["DQS-04"])
def test_a_table_without_an_extension_is_skipped_not_guessed(
    tmp_path: Path, settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-04: a file whose format cannot be told is skipped — the scan never guesses a reader."""
    path = tmp_path / "extract.tbl"
    path.write_text(CSV_TEXT)
    reader = FileReader({"/d3": str(path)}, settings().max_rows)
    assert reader.read("/d3", "g") is None
    assert reader.skip_reason("/d3", "g") == UNKNOWN_FORMAT


@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.FileReader.skip_reason", rules=["DQS-04"])
def test_a_dataset_without_a_source_is_skipped() -> None:
    """DQS-04: an unconfigured dataset is skipped with its reason, counted rather than failing the run."""
    reader = FileReader({}, 1000)
    assert reader.read("/d9", "g") is None
    assert reader.skip_reason("/d9", "g") == NO_SOURCE


@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.FileReader.skip_reason", rules=["DQS-04"])
def test_a_configured_but_missing_file_is_skipped(tmp_path: Path) -> None:
    """DQS-04: a configured source that is not there is a skip, not a crash mid-evaluation."""
    reader = FileReader({"/d3": str(tmp_path / "gone.parquet")}, 1000)
    assert reader.read("/d3", "g") is None
    assert reader.skip_reason("/d3", "g") == NO_FILE


@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.FileReader.read", rules=["DQS-05"])
def test_a_large_parquet_extract_is_cut_at_the_budget(tmp_path: Path) -> None:
    """DQS-05: a bigger extract than the row budget is scored on the first budget rows, with a notice."""
    big = pl.DataFrame({"total": list(range(1000))})
    big.write_parquet(tmp_path / "big.parquet")
    reader = FileReader({"/d3": str(tmp_path / "big.parquet")}, 100)
    read = reader.read("/d3", "g")
    assert read is not None
    assert read.frame.height == 100
    assert read.notice == TRUNCATED


@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.FileReader.read", rules=["DQS-05"])
def test_the_json_reader_also_stops_at_the_budget(tmp_path: Path) -> None:
    """DQS-05: the budget applies to the whole-file reader too, so no format reads unbounded."""
    path = tmp_path / "many.json"
    path.write_text(json.dumps([{"total": i} for i in range(500)]))
    reader = FileReader({"/d3": str(path)}, 50)
    read = reader.read("/d3", "g")
    assert read is not None
    assert read.frame.height == 50
    assert read.notice == TRUNCATED


@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.FileReader.read", rules=["DQS-05"])
def test_an_extract_within_the_budget_carries_no_notice(
    tmp_path: Path, settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-05: the whole-table checks see the whole extract when it fits — no notice, no cut."""
    path = _write_extract(tmp_path, "extract.csv", "csv")
    reader = FileReader({"/d3": str(path)}, settings().max_rows)
    read = reader.read("/d3", "g")
    assert read is not None
    assert read.notice is None
    assert read.frame.height == 3


@pytest.mark.covers("aurelius_atlas_quality_scanner.scan._read_dataset", rules=["DQS-05"])
def test_a_cut_extract_is_counted_and_said_in_the_report(tmp_path: Path) -> None:
    """DQS-05: the scan reads once per dataset and carries the cut into its summary notices."""
    from aurelius_atlas_quality_scanner.catalogue import DatasetRef  # noqa: PLC0415 - the ref the report names
    from aurelius_atlas_quality_scanner.scan import ScanReport, _read_dataset  # noqa: PLC0415 - the seam under test

    path = _write_extract(tmp_path, "extract.csv", "csv")
    reader = FileReader({"/d3": str(path)}, 2)
    report = ScanReport()
    read = _read_dataset(reader, DatasetRef("g3", "/d3"), report)
    assert read is not None
    assert read.frame.height == 2
    assert report.truncated == 1
    assert [notice for notice in report.notices if "truncated" in notice]

"""One scan end to end over the fake catalogue (DQS-01, DQS-03, DQS-08, DQS-09)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_quality_scanner.scan import run_scan, score_line
from aurelius_atlas_quality_scanner.settings import ScannerSettings
from aurelius_atlas_quality_scanner.sources import FileReader
from aurelius_atlas_server_client import AtlasClient, AtlasClientError
from fake_catalogue import FakeCatalogue, entity_with_fields, field_with_datasets, related, rule_header

PASSING_CSV = "total\n1\n2\n3\n"
FAILING_CSV = "total,region\n1,north\n,north\n3,south\n"
RUN_MS = 1_700_000_000_000


def _attrs(name: str, **extra: Any) -> dict[str, Any]:  # noqa: ANN401 - attribute values are untyped JSON
    """A stored ACTIVE ``not_null`` rule over ``total``, plus what a test names."""
    values: dict[str, Any] = {
        "name": name,
        "active": True,
        "dqcheckkind": "COLUMN_NOT_NULL_RATIO",
        "dqcolumn": "total",
    }
    values.update(extra)
    return values


def _seed(
    catalogue: FakeCatalogue,
    entries: list[tuple[str, dict[str, Any], list[tuple[str, list[tuple[str, str]]]]]],
) -> None:
    """Load the catalogue: rule headers, each rule's fields, and each field's datasets."""
    catalogue.add_rule_page([rule_header(guid, attrs) for guid, attrs, _ in entries])
    for guid, _, fields in entries:
        catalogue.rules[guid] = entity_with_fields(guid, [related(field_guid, "") for field_guid, _ in fields])
        for field_guid, datasets in fields:
            catalogue.fields[field_guid] = field_with_datasets(field_guid, [related(g, q) for g, q in datasets])


def _sources(tmp_path: Path, **files: str) -> dict[str, str]:
    """Write each named extract under ``tmp_path`` and answer the ``sources`` map."""
    sources: dict[str, str] = {}
    for qualified_name, text in files.items():
        path = tmp_path / f"{qualified_name.lstrip('/')}.csv"
        path.write_text(text)
        sources[qualified_name] = str(path)
    return sources


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.scan.run_scan", rules=["DQS-01", "DQS-06"])
async def test_a_happy_scan_scores_and_stores_once(
    client: AtlasClient,
    catalogue: FakeCatalogue,
    settings: Callable[..., ScannerSettings],
    reader: Callable[..., FileReader],
    tmp_path: Path,
) -> None:
    """DQS-01/DQS-06: the scan reads, evaluates, and stores every score plus the dataset summary — one write."""
    _seed(catalogue, [("r1", _attrs("r1"), [("f1", [("/d1", "/d1")])])])
    report = await run_scan(
        client, reader(_sources(tmp_path, **{"/d1": PASSING_CSV})), settings(), run_id="run-1", run_at_ms=RUN_MS
    )
    assert report.written is True
    assert catalogue.write_requests == 1
    assert report.rules_total == 1
    assert report.datasets_read == 1
    by_key = catalogue.written_by_key()
    assert by_key["/d1/r1"]["attributes"]["verdict"] == "PASS"
    assert by_key["/d1/r1"]["attributes"]["score"] == 1.0
    assert by_key["/d1/overall"]["attributes"]["verdict"] == "PASS"  # every scored rule passed
    assert by_key["/d1/r1"]["attributes"]["runId"] == "run-1"


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.scan.run_scan", rules=["DQS-07"])
async def test_a_failed_rule_lowers_the_score_and_the_summary(
    client: AtlasClient,
    catalogue: FakeCatalogue,
    settings: Callable[..., ScannerSettings],
    reader: Callable[..., FileReader],
    tmp_path: Path,
) -> None:
    """DQS-07: one failed rule verdict FAIL, the shared score below 1, and the summary says FAIL too."""
    _seed(catalogue, [("r1", _attrs("r1"), [("f1", [("/d1", "/d1")])])])
    await run_scan(
        client, reader(_sources(tmp_path, **{"/d1": FAILING_CSV})), settings(), run_id="run-1", run_at_ms=RUN_MS
    )
    by_key = catalogue.written_by_key()
    assert by_key["/d1/r1"]["attributes"]["verdict"] == "FAIL"
    assert by_key["/d1/r1"]["attributes"]["rowsChecked"] == 3
    assert by_key["/d1/r1"]["attributes"]["rowsFailed"] == 1
    assert by_key["/d1/overall"]["attributes"]["verdict"] == "FAIL"


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.scan.run_scan", rules=["DQS-07"])
async def test_a_score_over_the_threshold_passes(
    client: AtlasClient,
    catalogue: FakeCatalogue,
    settings: Callable[..., ScannerSettings],
    reader: Callable[..., FileReader],
    tmp_path: Path,
) -> None:
    """DQS-07: the rule's own threshold decides the verdict — 0.67 clears 0.5, so PASS."""
    _seed(catalogue, [("r1", _attrs("r1", threshold=0.5), [("f1", [("/d1", "/d1")])])])
    await run_scan(
        client, reader(_sources(tmp_path, **{"/d1": FAILING_CSV})), settings(), run_id="run-1", run_at_ms=RUN_MS
    )
    assert catalogue.written_by_key()["/d1/r1"]["attributes"]["verdict"] == "PASS"


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.scan._scan_dataset", rules=["DQS-08"])
async def test_a_rule_that_cannot_run_is_an_error_and_the_run_goes_on(
    client: AtlasClient,
    catalogue: FakeCatalogue,
    settings: Callable[..., ScannerSettings],
    reader: Callable[..., FileReader],
    tmp_path: Path,
) -> None:
    """DQS-08: a rule naming a missing column is stored ERROR for that dataset; its sibling still scores."""
    _seed(
        catalogue,
        [
            ("r1", _attrs("r1", dqcolumn="ghost"), [("f1", [("/d1", "/d1")])]),
            ("r2", _attrs("r2"), [("f1", [("/d1", "/d1")])]),
        ],
    )
    report = await run_scan(
        client, reader(_sources(tmp_path, **{"/d1": PASSING_CSV})), settings(), run_id="run-1", run_at_ms=RUN_MS
    )
    by_key = catalogue.written_by_key()
    assert by_key["/d1/r1"]["attributes"]["verdict"] == "ERROR"
    assert "ghost" in by_key["/d1/r1"]["attributes"]["errorMessage"]
    assert by_key["/d1/r2"]["attributes"]["verdict"] == "PASS"  # the run went on with the other rule
    assert report.written is True


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.scan.run_scan", rules=["DQS-08"])
async def test_a_rule_the_vocabulary_cannot_read_is_stored_error_per_dataset(
    client: AtlasClient,
    catalogue: FakeCatalogue,
    settings: Callable[..., ScannerSettings],
    reader: Callable[..., FileReader],
    tmp_path: Path,
) -> None:
    """DQS-08: an unreadable rule still reaches its datasets, and each dataset gets its ERROR entity."""
    _seed(catalogue, [("r1", {"name": "legacy", "active": True}, [("f1", [("/d1", "/d1"), ("/d2", "/d2")])])])
    report = await run_scan(
        client,
        reader(_sources(tmp_path, **{"/d1": PASSING_CSV, "/d2": PASSING_CSV})),
        settings(),
        run_id="run-1",
        run_at_ms=RUN_MS,
    )
    by_key = catalogue.written_by_key()
    assert {key: row["attributes"]["verdict"] for key, row in by_key.items() if key.endswith("/r1")} == {
        "/d1/r1": "ERROR",
        "/d2/r1": "ERROR",
    }
    assert "vocabulary" in by_key["/d1/r1"]["attributes"]["errorMessage"]
    assert report.datasets_read == 2  # the datasets were read; only the rule failed to parse


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.scan.run_scan", rules=["DQS-02", "DQS-03"])
async def test_inactive_and_unbound_rules_are_counted_not_stored(
    client: AtlasClient,
    catalogue: FakeCatalogue,
    settings: Callable[..., ScannerSettings],
    reader: Callable[..., FileReader],
    tmp_path: Path,
) -> None:
    """DQS-02/DQS-03: the run leaves inactive and unbound rules out of the store and counts them."""
    catalogue.add_rule_page([rule_header("r1", _attrs("r1", active=False)), rule_header("r2", _attrs("r2"))])
    catalogue.rules["r2"] = entity_with_fields("r2", [])  # no fields: unbound
    report = await run_scan(
        client, reader(_sources(tmp_path, **{"/d1": PASSING_CSV})), settings(), run_id="run-1", run_at_ms=RUN_MS
    )
    assert (report.rules_total, report.rules_inactive, report.rules_unbound) == (2, 1, 1)
    assert report.entities == []
    assert catalogue.write_requests == 0  # nothing to store: no write is sent


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.scan._read_dataset", rules=["DQS-04"])
async def test_a_dataset_with_no_extract_is_skipped_with_its_reason(
    client: AtlasClient,
    catalogue: FakeCatalogue,
    settings: Callable[..., ScannerSettings],
    reader: Callable[..., FileReader],
) -> None:
    """DQS-04: an unconfigured dataset is skipped, named in a notice, and counted — the scan finishes."""
    _seed(catalogue, [("r1", _attrs("r1"), [("f1", [("/d1", "/d1")])])])
    report = await run_scan(client, reader({}), settings(), run_id="run-1", run_at_ms=RUN_MS)
    assert report.datasets_skipped == 1
    assert report.datasets_read == 0
    assert any("no source configured" in notice for notice in report.notices)


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.scan.run_scan", rules=["DQS-09"])
async def test_a_dry_run_stores_nothing_but_answers_every_entity(
    client: AtlasClient,
    catalogue: FakeCatalogue,
    settings: Callable[..., ScannerSettings],
    reader: Callable[..., FileReader],
    tmp_path: Path,
) -> None:
    """DQS-09: the dry-run scans, answers every candidate, and sends no write at all."""
    _seed(catalogue, [("r1", _attrs("r1"), [("f1", [("/d1", "/d1")])])])
    report = await run_scan(
        client,
        reader(_sources(tmp_path, **{"/d1": PASSING_CSV})),
        settings(),
        run_id="run-1",
        run_at_ms=RUN_MS,
        dry_run=True,
    )
    assert report.written is False
    assert catalogue.write_requests == 0
    assert {(entity.attributes or {})["scoreKey"] for entity in report.entities} == {"/d1/r1", "/d1/overall"}


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.scan.run_scan", rules=["DQS-09"])
async def test_the_dataset_filter_limits_the_scan_and_frees_its_rules(
    client: AtlasClient,
    catalogue: FakeCatalogue,
    settings: Callable[..., ScannerSettings],
    reader: Callable[..., FileReader],
    tmp_path: Path,
) -> None:
    # DQS-09: the filter's two answers: what was read, and the rule the filter left without a dataset.
    """DQS-09: filtered out, a dataset is never read — and a rule left with no dataset counts unbound."""
    _seed(
        catalogue,
        [
            ("r1", _attrs("r1"), [("f1", [("/d1", "/d1")])]),
            ("r2", _attrs("r2"), [("f2", [("/d2", "/d2")])]),
        ],
    )
    report = await run_scan(
        client,
        reader(_sources(tmp_path, **{"/d1": PASSING_CSV, "/d2": PASSING_CSV})),
        settings(),
        run_id="run-1",
        run_at_ms=RUN_MS,
        dataset_filter={"/d1"},
    )
    assert report.datasets_read == 1
    assert report.rules_unbound == 1
    keys = set(catalogue.written_by_key())
    assert keys == {"/d1/r1", "/d1/overall"}  # /d2 and its only rule are out of the run


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.scan.run_scan", rules=["DQS-01"])
async def test_a_refusing_catalogue_fails_the_run(
    settings: Callable[..., ScannerSettings], reader: Callable[..., FileReader]
) -> None:
    """DQS-01: a catalogue call that fails is a run-level failure and raises to the CLI."""

    def refusing(request: httpx.Request) -> httpx.Response:  # noqa: ARG001 - the request never matters
        return httpx.Response(500, json={"errorCode": "ATLAS-500-00-001", "errorMessage": "store down"})

    http = httpx.AsyncClient(base_url="http://atlas.test", transport=httpx.MockTransport(refusing))
    with pytest.raises(AtlasClientError):
        await run_scan(AtlasClient(http, "token"), reader({}), settings(), run_id="run-1", run_at_ms=RUN_MS)


def test_the_dry_run_line_names_key_verdict_and_score() -> None:
    """DQS-09: the line a dry-run prints per candidate: its key, its verdict, and its score."""
    from aurelius_atlas_quality_scanner.records import score_entity  # noqa: PLC0415 - the document behind the line

    entity = score_entity(
        {"ruleGuid": "r1", "datasetGuid": "d1", "runId": "x", "runAtMs": 1, "score": 0.75, "passed": False}
    )
    assert score_line(entity) == "d1/r1 FAIL score=0.75"

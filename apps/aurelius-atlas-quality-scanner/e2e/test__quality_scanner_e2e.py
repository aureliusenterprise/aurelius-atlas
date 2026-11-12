"""E2E: the scanner's own identity against the real server (DQS-10).

The suite drives the job in-process — the scanner is a batch CLI, not a service — on the
stack of ``e2e/docker-compose.yaml``: a real Atlas server on the dev store and the dev
issuer. Every scan speaks as the scanner's own service client (DD-458): the reads and the
writes of a run ride its client-credentials token, so this is the spec's end-to-end proof
that the identity answers read AND write, and that the score entities land in the real
catalogue — not a fake's record list. Each scenario namespaces its names to one ``zz<run>``
word, scans with the dataset filter (DQS-09) so a foreign rule of the shared store — the
sample corpus rides it — is never evaluated, and hard-deletes what it seeded (DD-223);
nothing here restarts the store.
"""

import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.instance import AtlasEntity
from aurelius_atlas_quality_scanner.records import ERROR_VERDICT, OVERALL, PASSED_VERDICT
from aurelius_atlas_quality_scanner.scan import run_scan
from aurelius_atlas_quality_scanner.settings import ScannerSettings, SourceEntry
from aurelius_atlas_quality_scanner.sources import SourceRouter
from aurelius_atlas_server_client import AtlasClient

if TYPE_CHECKING:
    from conftest import Seeded

PASSING_CSV = "total\n1\n2\n3\n"
"""A three-row extract whose ``total`` column carries no null: a not-null rule passes (1.0)."""

NOT_NULL = {"dqcheckkind": "COLUMN_NOT_NULL_RATIO", "dqcolumn": "total"}
"""The typed rule attributes of a not-null ratio over ``total`` (the DD-457 vocabulary)."""

Seed = Callable[[str, dict[str, Any]], Awaitable[dict[str, str]]]
WaitForRule = Callable[[str, str], Awaitable[None]]


def _write_extract(root: Path, run: str, text: str = PASSING_CSV) -> str:
    """One run's CSV extract under the test's temp dir; its path for the source list."""
    extract = root / f"{run}.csv"
    extract.write_text(text)
    return str(extract)


def _attributes(entity: AtlasEntity) -> dict[str, Any]:
    """The wire attributes of a read-back entity (the model's map is optional)."""
    return dict(entity.attributes or {})


def _reader(sources: dict[str, str]) -> SourceRouter:
    """The real router over file sources pointing at the test's extracts (12.4a: the e2e rides the envelope)."""
    entries = [
        SourceEntry.model_validate(
            {"dataset": {"qualifiedName": name}, "kind": "file", "config": {"path": path}},
        )
        for name, path in sources.items()
    ]
    return SourceRouter(entries, max_rows=1_000_000)


async def _scores(writer: AtlasClient, keys: list[str]) -> dict[str, AtlasEntity]:
    """The stored score entities by ``scoreKey``; a key that stored nothing is absent."""
    found = await writer.entity.entities_by_unique_attributes("m4i_dq_score", [{"scoreKey": key} for key in keys])
    return {str(_attributes(entity)["scoreKey"]): entity for entity in found.entities or []}


def _now_ms() -> int:
    """The scan's run instant, epoch millis."""
    return int(time.time() * 1000)


@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_quality_scanner.scan.run_scan",
    "aurelius_atlas_quality_scanner.catalogue.fetch_rules",
    "aurelius_atlas_quality_scanner.catalogue.bind_datasets",
    "aurelius_atlas_quality_scanner.catalogue.write_scores",
    "aurelius_atlas_quality_scanner.__main__.build_client",
    rules=["DQS-10", "DQS-01"],
)
async def test__the_scanners_own_token_reads_rules_writes_scores_and_reads_them_back(
    scanner: AtlasClient,
    writer: AtlasClient,
    scanner_settings: ScannerSettings,
    seed: Seed,
    wait_for_rule: WaitForRule,
    cleanup: Seeded,
    run_token: str,
    tmp_path: Path,
) -> None:
    """The scan as its own service identity: the real store answers every leg (DQS-10, DQS-01).

    Seed a dataset/field/rule graph, point the source list at a CSV extract, run the scan,
    and read the scores back by their unique keys: the rule's PASS score and the dataset's
    summary. Every call rode the scanner's client-credentials token — a wrong audience or a
    missing role grant fails the scan at the server, not here (the DD-458 posture).
    """
    extract = _write_extract(tmp_path, run_token)
    guids = await seed(run_token, dict(NOT_NULL))
    await wait_for_rule(guids["field"], guids["rule"])
    cleanup.graph(*guids.values())

    sources = {f"zz{run_token}warehouse": extract}
    report = await run_scan(
        scanner,
        _reader(sources),
        scanner_settings,
        run_id=str(uuid4()),
        run_at_ms=_now_ms(),
        dataset_filter=set(sources),
    )
    assert report.written
    assert report.datasets_read == 1

    keys = [f"{guids['dataset']}/{guids['rule']}", f"{guids['dataset']}/{OVERALL}"]
    cleanup.scores(*keys)
    stored = await _scores(writer, keys)
    assert set(stored) == set(keys)

    score = _attributes(stored[keys[0]])
    assert score["verdict"] == PASSED_VERDICT
    assert score["score"] == 1.0
    assert score["ruleGuid"] == guids["rule"]
    assert score["datasetGuid"] == guids["dataset"]
    summary = _attributes(stored[keys[1]])
    assert summary["ruleGuid"] is None
    assert summary["verdict"] == PASSED_VERDICT
    assert summary["dimensions"] == {"COMPLETENESS": "1.0"}


# impact=severe, likelihood=low (the spine path moves rarely between increments)
@pytest.mark.high
@pytest.mark.covers(
    "aurelius_atlas_quality_scanner.scan.run_scan",
    "aurelius_atlas_quality_scanner.catalogue.write_scores",
    rules=["DQS-10", "DQS-06"],
)
async def test__a_second_run_updates_the_same_score_entities_in_place(
    scanner: AtlasClient,
    writer: AtlasClient,
    scanner_settings: ScannerSettings,
    seed: Seed,
    wait_for_rule: WaitForRule,
    cleanup: Seeded,
    run_token: str,
    tmp_path: Path,
) -> None:
    """DD-456 under the scanner's own identity: re-run, same keys, same entities, new run id.

    The scan stores by unique ``scoreKey`` and the store resolves each key to its entity
    (EWR-05/EWR-06): the second run answers with the first run's GUIDs — updated in place,
    no copies — and carries only the second run's id.
    """
    extract = _write_extract(tmp_path, run_token)
    guids = await seed(run_token, dict(NOT_NULL))
    await wait_for_rule(guids["field"], guids["rule"])
    cleanup.graph(*guids.values())
    keys = [f"{guids['dataset']}/{guids['rule']}", f"{guids['dataset']}/{OVERALL}"]
    cleanup.scores(*keys)

    sources = {f"zz{run_token}warehouse": extract}
    first, second = str(uuid4()), str(uuid4())
    await run_scan(
        scanner, _reader(sources), scanner_settings, run_id=first, run_at_ms=_now_ms(), dataset_filter=set(sources)
    )
    after_first = await _scores(writer, keys)
    await run_scan(
        scanner, _reader(sources), scanner_settings, run_id=second, run_at_ms=_now_ms(), dataset_filter=set(sources)
    )
    after_second = await _scores(writer, keys)

    assert {str(entity.guid) for entity in after_second.values()} == {
        str(entity.guid) for entity in after_first.values()
    }
    assert {_attributes(entity)["runId"] for entity in after_second.values()} == {second}


# impact=severe, likelihood=low (a dry run that writes is unwanted data; it moves rarely)
@pytest.mark.high
@pytest.mark.covers(
    "aurelius_atlas_quality_scanner.scan.run_scan",
    "aurelius_atlas_quality_scanner.catalogue.write_scores",
    rules=["DQS-10", "DQS-09"],
)
async def test__a_dry_run_writes_nothing(
    scanner: AtlasClient,
    writer: AtlasClient,
    scanner_settings: ScannerSettings,
    seed: Seed,
    wait_for_rule: WaitForRule,
    cleanup: Seeded,
    run_token: str,
    tmp_path: Path,
) -> None:
    """DQS-09 under the real identity: the dry scan answers the candidates, the store stays empty.

    The unique-attribute read answers nothing for either key: the scan never spoke its write.
    """
    extract = _write_extract(tmp_path, run_token)
    guids = await seed(run_token, dict(NOT_NULL))
    await wait_for_rule(guids["field"], guids["rule"])
    cleanup.graph(*guids.values())

    sources = {f"zz{run_token}warehouse": extract}
    report = await run_scan(
        scanner,
        _reader(sources),
        scanner_settings,
        run_id=str(uuid4()),
        run_at_ms=_now_ms(),
        dataset_filter=set(sources),
        dry_run=True,
    )
    assert not report.written
    assert len(report.entities) == 2  # The rule's score and the summary, as candidates only.

    stored = await _scores(writer, [f"{guids['dataset']}/{guids['rule']}", f"{guids['dataset']}/{OVERALL}"])
    assert stored == {}


# impact=major, likelihood=medium (a bad rule must land visibly; a young error path)
@pytest.mark.high
@pytest.mark.covers(
    "aurelius_atlas_quality_scanner.scan.run_scan",
    "aurelius_atlas_quality_scanner.catalogue.write_scores",
    rules=["DQS-10", "DQS-08"],
)
async def test__an_unreadable_rule_lands_as_an_error_entity(
    scanner: AtlasClient,
    writer: AtlasClient,
    scanner_settings: ScannerSettings,
    seed: Seed,
    wait_for_rule: WaitForRule,
    cleanup: Seeded,
    run_token: str,
    tmp_path: Path,
) -> None:
    """DQS-08 through the job's own identity: a rule the vocabulary cannot read is stored, as ERROR.

    A rule with no check kind is the corpus shape the bridge names its error for (DD-454);
    the scan still binds its dataset through the rule's ``fields`` end (DQS-03) and stores
    the ERROR entity in the same single write — no score, with the cause in ``errorMessage``.
    """
    extract = _write_extract(tmp_path, run_token)
    broken = await seed(run_token, {})  # No dqcheckkind: unreadable, its ERROR names the cause.
    await wait_for_rule(broken["field"], broken["rule"])
    cleanup.graph(*broken.values())

    sources = {f"zz{run_token}warehouse": extract}
    report = await run_scan(
        scanner,
        _reader(sources),
        scanner_settings,
        run_id=str(uuid4()),
        run_at_ms=_now_ms(),
        dataset_filter=set(sources),
    )
    assert report.written

    key = f"{broken['dataset']}/{broken['rule']}"
    cleanup.scores(key)
    stored = await _scores(writer, [key])
    entity = stored.get(key)
    assert entity is not None, "the unreadable rule stored no entity"
    attributes = _attributes(entity)
    assert attributes["verdict"] == ERROR_VERDICT
    assert attributes["errorMessage"]
    # The store materialises every primitive the entity omits to its type's default (EWR-09), so
    # the stored score and row counts read 0, never absent; "no score" is the written entity's
    # truth, which the unit pair of this rule names on the fake's record (test__scan.py).
    assert attributes["rowsChecked"] == 0


# impact=severe, likelihood=low (the audit trail names the scanner; a governance promise, stable)
@pytest.mark.high
@pytest.mark.covers(
    "aurelius_atlas_quality_scanner.scan.run_scan",
    "aurelius_atlas_quality_scanner.__main__.build_client",
    rules=["DQS-10"],
)
async def test__every_score_write_is_audited_as_the_scanner(
    scanner: AtlasClient,
    writer: AtlasClient,
    scanner_settings: ScannerSettings,
    scanner_claims: dict[str, Any],
    seed: Seed,
    wait_for_rule: WaitForRule,
    cleanup: Seeded,
    run_token: str,
    tmp_path: Path,
) -> None:
    """The audit reason the job has its own identity (DD-458): each score names the scanner.

    The write's create event names the scanner's service account — never the seeding writer
    and never anonymous. The name is what the server's ``user_of`` reads from the token:
    the principal claim, else the ``sub`` (AUT-03).
    """
    extract = _write_extract(tmp_path, run_token)
    guids = await seed(run_token, dict(NOT_NULL))
    await wait_for_rule(guids["field"], guids["rule"])
    cleanup.graph(*guids.values())

    sources = {f"zz{run_token}warehouse": extract}
    await run_scan(
        scanner,
        _reader(sources),
        scanner_settings,
        run_id=str(uuid4()),
        run_at_ms=_now_ms(),
        dataset_filter=set(sources),
    )

    stored = await _scores(writer, [f"{guids['dataset']}/{guids['rule']}"])
    entity = next(iter(stored.values()))
    cleanup.scores(str(_attributes(entity)["scoreKey"]))

    events = await writer.entity.audit_events(str(entity.guid))
    created = [event for event in events if event.action is EntityAuditActionV2.ENTITY_CREATE]
    assert created, f"the score has no create event: {events}"
    expected = scanner_claims.get("preferred_username") or scanner_claims["sub"]
    assert {event.user for event in created} == {str(expected)}

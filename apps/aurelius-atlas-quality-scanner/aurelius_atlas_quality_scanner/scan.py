"""One scan: the five steps and the per-rule, per-dataset outcomes (12.2, DQS-01, DQS-08, DQS-09).

The scan reads the rules (DQS-02), binds their datasets (DQS-03), reads each dataset's extract
through the reader (DQS-04), evaluates the bound rules over it with the engine, and answers the
entities the run would store; the one write (DQS-06) happens here too, unless ``--dry-run`` asked
for no write (DQS-09). A rule that cannot run is an ERROR entity, not a failed run (DQS-08).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

import polars as pl
from aurelius_atlas_model.instance import AtlasEntity
from aurelius_atlas_quality import RuleResult, evaluate, result_documents, summarise
from aurelius_atlas_server_client import AtlasClient
from polars.exceptions import ColumnNotFoundError

from aurelius_atlas_quality_scanner import catalogue, records
from aurelius_atlas_quality_scanner.catalogue import DatasetRef, RuleEntry
from aurelius_atlas_quality_scanner.settings import ScannerSettings
from aurelius_atlas_quality_scanner.sources import DatasetReader, Read

MAX_FAILED_ROWS_NONE = 0
"""The engine's failed-row sample the scan never keeps: the score entities carry counts, not rows."""


@dataclass
class ScanReport:
    """What one scan did: the entities it stored (or would store, dry-run) and what it says so."""

    entities: list[AtlasEntity] = field(default_factory=list)
    """Every score and ERROR entity of the run, in scan order (DQS-06)."""

    notices: list[str] = field(default_factory=list)
    """The skips and cuts the run says out loud (DQS-03, DQS-04, DQS-05)."""

    rules_total: int = 0
    """The rules the search answered, ACTIVE or not."""

    rules_inactive: int = 0
    """The rules the ACTIVE filter left out (DQS-02)."""

    rules_unbound: int = 0
    """The ACTIVE rules that reached no dataset and were skipped (DQS-03)."""

    datasets_read: int = 0
    """The datasets whose extract was read and evaluated."""

    datasets_skipped: int = 0
    """The datasets with no readable extract, skipped with a reason (DQS-04)."""

    truncated: int = 0
    """The extracts cut at the row budget (DQS-05)."""

    written: bool = False
    """Whether the run wrote its entities; false for ``--dry-run`` (DQS-09)."""


def _dataset_line(ref: DatasetRef) -> str:
    """How the scan names a dataset in a notice."""
    return f"{ref.qualified_name} ({ref.guid})"


def _read_dataset(reader: DatasetReader, ref: DatasetRef, report: ScanReport) -> Read | None:
    """Read one dataset, counting the skip and the cut into ``report`` (DQS-04, DQS-05)."""
    read = reader.read(ref.qualified_name, ref.guid)
    if read is None:
        report.notices.append(f"skipped {_dataset_line(ref)}: {reader.skip_reason(ref.qualified_name, ref.guid)}")
        report.datasets_skipped += 1
        return None
    if read.notice:
        report.notices.append(f"{_dataset_line(ref)}: {read.notice} at the row budget")
        report.truncated += 1
    report.datasets_read += 1
    return read


def _bound_to(entry: RuleEntry, ref: DatasetRef) -> bool:
    """Whether the rule reached this dataset through its fields (DQS-03)."""
    return any(dataset.guid == ref.guid for dataset in entry.datasets)


def _scan_dataset(  # noqa: PLR0913 - one dataset's rule set and frame and the run's identity
    ref: DatasetRef,
    entries: list[RuleEntry],
    frame: pl.DataFrame,
    *,
    run_id: str,
    run_at_ms: int,
    as_of: datetime,
) -> list[AtlasEntity]:
    """The entities of one dataset: every bound rule's document, or its ERROR entity (DQS-08).

    A rule whose column the extract lacks is recorded for that dataset and the scan moves on with
    the dataset's other rules; a rule the vocabulary could not read is recorded once per dataset it
    was bound to. The summary document's verdict is the rule rows' shared verdict: PASS only when
    every scored rule of the dataset passed.
    """
    entities: list[AtlasEntity] = []
    results: list[RuleResult] = []
    for entry in entries:
        if not _bound_to(entry, ref):
            continue
        if entry.rule is None:
            entities.append(records.error_entity(entry.guid, ref.guid, run_id, run_at_ms, entry.parse_error or ""))
            continue
        try:
            results.append(evaluate(entry.rule, frame, as_of=as_of, max_failed_rows=MAX_FAILED_ROWS_NONE))
        except ColumnNotFoundError as cause:
            entities.append(records.error_entity(entry.guid, ref.guid, run_id, run_at_ms, str(cause)))
    summary_verdict = (
        records.PASSED_VERDICT if results and all(result.passed for result in results) else records.FAILED_VERDICT
    )
    documents = result_documents(results, summarise(results), dataset_guid=ref.guid, run_id=run_id, run_at_ms=run_at_ms)
    for document in documents:
        verdict = summary_verdict if document.get("ruleGuid") is None else None
        entities.append(records.score_entity(document, verdict))
    return entities


async def run_scan(  # noqa: PLR0913 - the scan's doors and identity and its two switches
    client: AtlasClient,
    reader: DatasetReader,
    settings: ScannerSettings,
    *,
    run_id: str,
    run_at_ms: int,
    dataset_filter: set[str] | None = None,
    dry_run: bool = False,
) -> ScanReport:
    """Run one scan over ``client`` and ``reader``; answer the report (DQS-01..09).

    The dataset filter (DQS-09) limits the scan to the named qualified names before anything is
    read, so a rule reaching none of them is never evaluated. A catalogue call that fails is a
    run-level failure and raises: the CLI answers it with exit 1 (DQS-01).
    """
    report = ScanReport()
    entries = await catalogue.fetch_rules(client, settings)
    report.rules_total = len(entries)
    report.rules_inactive = sum(1 for entry in entries if not entry.active)
    active = [entry for entry in entries if entry.active]
    datasets = await catalogue.bind_datasets(client, active)
    if dataset_filter is not None:
        datasets = {guid: ref for guid, ref in datasets.items() if ref.qualified_name in dataset_filter}
        for entry in active:
            entry.datasets = [ref for ref in entry.datasets if ref.qualified_name in dataset_filter]
    report.rules_unbound = sum(1 for entry in active if not entry.datasets)
    as_of = datetime.fromtimestamp(run_at_ms / 1000, tz=UTC)
    for ref in datasets.values():
        read = _read_dataset(reader, ref, report)
        if read is not None:
            report.entities.extend(
                _scan_dataset(ref, active, read.frame, run_id=run_id, run_at_ms=run_at_ms, as_of=as_of)
            )
    if not dry_run:
        await catalogue.write_scores(client, report.entities)
        report.written = True
    return report


def score_line(entity: AtlasEntity) -> str:
    """The dry-run line of one entity candidate: its key, verdict and score (DQS-09)."""
    attributes = entity.attributes or {}
    score = attributes.get("score")
    return f"{attributes['scoreKey']} {attributes['verdict']}" + (f" score={score}" if score is not None else "")

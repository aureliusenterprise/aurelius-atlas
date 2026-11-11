"""The catalogue door: the rules to scan, their datasets, and the scores back in (12.2, DQS-02, DQS-03, DQS-06).

The rules arrive by the basic search of ``m4i_data_quality``, paged by marker (DQS-02). A rule's
datasets are reached through its ``fields`` end and each field's ``datasets`` end (DD-457), so the
door reads the rules' relationship attributes and then the fields' — both as bulk reads (DQS-03).
Scores leave through one bulk write per scan (DQS-06).
"""

from dataclasses import dataclass, field
from typing import Any

from aurelius_atlas_model.discovery import SearchParameters
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, AtlasEntityHeader
from aurelius_atlas_quality import (
    KINDS,
    RULE_TYPE_NAME,
    CheckKind,
    DqRule,
    QualityRuleError,
    rule_from_atlas_attributes,
)
from aurelius_atlas_server_client import AtlasClient

from aurelius_atlas_quality_scanner.settings import ScannerSettings

MARKER_START = "*"
"""The marker that starts a paged search (SRC-08): the server answers a next marker only for a
request that carries one, so the walk starts here, not without a marker."""

MARKER_END = "-1"
"""The marker the server answers after the last page (SRC-08)."""

RULE_ATTRIBUTES: tuple[str, ...] = (
    "name",
    "qualifiedName",
    "active",
    "qualityDimension",
    "expression",
    "threshold",
    "dqcheckkind",
    "dqcolumn",
    "dqpattern",
    "dqvalues",
    "dqcolumns",
    "dqotherColumn",
    "dqtype",
    "dqmin",
    "dqmax",
    "dqmaxAgeHours",
    "dqminColumns",
)
"""The rule attributes the search answers (DQS-02): the search refuses a name the type does not
have, so the legacy pair's attributes (`dataqualitytype`, `columnname`, ...) are not asked — a
rule with no typed kind is unread (DD-454: its ERROR names the cause, never a guess). The rule's
``fields`` are not asked either: :func:`bind_datasets` reads the rule entities in bulk, where the
relationship attributes arrive with their qualified names."""


@dataclass(frozen=True)
class DatasetRef:
    """One dataset the scan reads: its GUID and its qualified name, the reader's key (DQS-04)."""

    guid: str
    qualified_name: str


@dataclass
class RuleEntry:
    """One rule of the catalogue: what the scan does with it, decided when the header was read (DQS-02).

    ``rule`` is set when the vocabulary can read it; ``parse_error`` names the cause when it cannot
    (DQS-08); both are ``None`` when the rule is not ACTIVE and is skipped (DQS-02).
    """

    guid: str
    name: str
    rule: DqRule | None = None
    parse_error: str | None = None
    active: bool = True
    datasets: list[DatasetRef] = field(default_factory=list)


def _raw(value: object) -> object:
    """The bare value of a webapp-wrapped attribute: ``{"raw": x}`` is ``x`` (DV-132)."""
    if isinstance(value, dict) and "raw" in value:
        return value["raw"]
    return value


def is_active(attributes: dict[str, Any]) -> bool:
    """Whether a rule is ACTIVE: only the boolean false is not (DQS-02).

    A missing ``active``, or one stored as text (the corpus holds both shapes), is active —
    matching what the legacy job treated as running rules.
    """
    return _raw(attributes.get("active")) is not False


_VOCABULARY_PARAMETERS: dict[str, str] = {
    "dqcolumn": "column",
    "dqpattern": "pattern",
    "dqvalues": "values",
    "dqcolumns": "columns",
    "dqotherColumn": "otherColumn",
    "dqtype": "type",
    "dqmin": "min",
    "dqmax": "max",
    "dqmaxAgeHours": "maxAgeHours",
    "dqminColumns": "minColumns",
}
"""The ``dq``-prefixed parameter attributes, by the name the bridge reads their parameter (DQ-07)."""


def rule_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """The attributes the engine's bridge reads, from the attributes the search answered.

    The type names the dimension ``qualityDimension``; the bridge reads ``dataqualityruledimension``,
    the legacy API's name, so the typed name is carried under the name the bridge reads — a stored
    dimension the rule's kind disagrees with is then the bridge's error, which the scan stores as
    ERROR. A rule with no ``dqcheckkind`` has no typed pair on this type (the legacy pair's
    attributes are not part of it), and the bridge's error names it: ERROR, never a guess (DD-454).

    A rule whose stored kind the vocabulary knows keeps only that kind's parameter attributes: the
    store materialises every primitive the entity omits to its type's default (EWR-09), so foreign
    parameters ride on every stored rule (``dqmin`` 0.0, ``dqminColumns`` 0, ...) and are not
    tellable from given ones — but a kind can only carry its own (DD-461).
    """
    plain = {key: _raw(value) for key, value in attributes.items()}
    if plain.get("qualityDimension") is not None:
        plain.setdefault("dataqualityruledimension", plain["qualityDimension"])
    try:
        spec = KINDS[CheckKind(str(plain.get("dqcheckkind")))]
    except ValueError:
        return plain  # the legacy pair, or an unknown kind: the bridge's error names it (DD-454).
    allowed = spec.required | spec.optional
    for attribute, parameter in _VOCABULARY_PARAMETERS.items():
        if parameter not in allowed:
            plain.pop(attribute, None)
    return plain


def _related_refs(value: object) -> list[tuple[str, str]]:
    """The ``(guid, qualifiedName)`` pairs of a SET relationship attribute, in order.

    Nothing for a value that is not a list, or for entries without a GUID or a qualified name.
    """
    if not isinstance(value, list):
        return []
    return [
        (str(item["guid"]), str(_raw(item.get("qualifiedName")) or ""))
        for item in value
        if isinstance(item, dict) and item.get("guid")
    ]


async def _by_guids(client: AtlasClient, guids: list[str]) -> list[AtlasEntity]:
    """The entities of ``guids``, or nothing for no GUIDs (the bulk route refuses an empty list)."""
    if not guids:
        return []
    found = await client.entity.by_guids(guids)
    return list(found.entities or [])


async def fetch_rules(client: AtlasClient, settings: ScannerSettings) -> list[RuleEntry]:
    """The ACTIVE rules of the catalogue, parsed where the vocabulary can read them (DQS-02).

    The search is paged by marker to the end, started at ``*`` (SRC-08: only a request that
    carries a marker is answered with the next one); a rule whose attributes the vocabulary cannot
    read still comes back, with :attr:`RuleEntry.parse_error` naming the cause (DQS-08), because
    its datasets are still reachable through its ``fields`` end.
    """
    entries: list[RuleEntry] = []
    marker: str | None = MARKER_START
    while True:
        parameters = SearchParameters(
            type_name=RULE_TYPE_NAME,
            exclude_deleted_entities=True,
            include_sub_types=False,
            limit=settings.search_limit,
            marker=marker,
            attributes=list(RULE_ATTRIBUTES),
        )
        result = await client.search.search_with_parameters(parameters)
        entries.extend(_entry_from_header(header) for header in result.entities or [])
        if not result.next_marker or result.next_marker == MARKER_END:
            return entries
        marker = result.next_marker


def _entry_from_header(header: AtlasEntityHeader) -> RuleEntry:
    """One search header as a rule entry: skipped when inactive, parsed where the vocabulary can (DQS-02)."""
    attributes = dict(header.attributes or {})
    guid = str(header.guid)
    if not is_active(attributes):
        return RuleEntry(guid=guid, name=str(_raw(attributes.get("name")) or ""), active=False)
    plain = rule_attributes(attributes)
    plain["guid"] = guid
    try:
        rule = rule_from_atlas_attributes(plain)
    except QualityRuleError as cause:
        return RuleEntry(guid=guid, name=rule_name(attributes), parse_error=str(cause))
    return RuleEntry(guid=guid, name=rule_name(attributes), rule=rule)


def rule_name(attributes: dict[str, Any]) -> str:
    """The rule's name, for the scan's lines: its ``name``, else its display text, else empty."""
    for key in ("name", "displayText"):
        raw = _raw(attributes.get(key))
        if raw:
            return str(raw)
    return ""


async def bind_datasets(client: AtlasClient, entries: list[RuleEntry]) -> dict[str, DatasetRef]:
    """Fill each bound rule's ``datasets`` and answer every dataset reached, by GUID, first-seen (DQS-03).

    The walk is rule -> ``fields`` -> each field's ``datasets`` (DD-457). A rule that reaches no
    dataset stays unbound, which the scan counts as a skip. A relationship that names a GUID the
    catalogue no longer holds fails its bulk read, and the run fails with it (DQS-01) — the store
    keeps its relationship ends consistent, so a dangling one is a catalogue fault worth failing on.
    """
    by_guid = {entry.guid: entry for entry in entries if entry.active}
    rules = await _by_guids(client, list(by_guid))
    field_refs: dict[str, set[str]] = {}
    for entity in rules:
        entry = by_guid.get(str(entity.guid))
        if entry is None:
            continue
        refs = _related_refs((entity.relationship_attributes or {}).get("fields"))
        field_refs[entry.guid] = {guid for guid, _ in refs}
    fields = await _by_guids(client, sorted({guid for guids in field_refs.values() for guid in guids}))
    datasets: dict[str, DatasetRef] = {}
    field_datasets: dict[str, list[DatasetRef]] = {}
    for entity in fields:
        refs = [
            DatasetRef(guid=guid, qualified_name=name)
            for guid, name in _related_refs((entity.relationship_attributes or {}).get("datasets"))
            if name
        ]
        field_datasets[str(entity.guid)] = refs
        for ref in refs:
            datasets.setdefault(ref.guid, ref)
    for entry in by_guid.values():
        seen: dict[str, DatasetRef] = {}
        for field_guid in field_refs.get(entry.guid, set()):
            for ref in field_datasets.get(field_guid, []):
                seen.setdefault(ref.guid, ref)
        entry.datasets = list(seen.values())
    return datasets


async def write_scores(client: AtlasClient, entities: list[AtlasEntity]) -> None:
    """The one bulk write of the scan: every score and finding entity at once (DQS-06).

    No entity carries an assigned GUID, so the store resolves each by its unique ``scoreKey`` and
    updates the entity with that key in place (EWR-05/EWR-06, DD-456). Nothing is written for no
    entities.
    """
    if entities:
        await client.entity.create_or_update_bulk(AtlasEntitiesWithExtInfo(entities=entities))

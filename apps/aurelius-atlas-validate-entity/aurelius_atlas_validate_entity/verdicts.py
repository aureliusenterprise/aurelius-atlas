"""The rules door: the cached ACTIVE rules and the draft's verdicts (VEV-02/03/05/07/08; DD-498, DD-631/632).

The rules arrive by the server's basic search of ``m4i_gov_data_quality``, paged by
marker to the end (VEV-03, 12.2's reading). A rule is ACTIVE unless its ``active``
attribute says otherwise, and the vocabulary's reading of it either yields a
:class:`~aurelius_atlas_quality.GovRule` or names why it cannot (VEV-03, DV-146):
an unread rule is recorded, never executed. The read set is cached for
``RULES_CACHE_SECONDS`` (VEV-05) — the draft always rides live.

Each rule carries the type its ``qualifiedName`` names before the first ``--``
(LAS-13, VEV-07): the draft is judged by the rules of its own type alone, as 14.6's
engine judges a stored entity, and a rule naming no type answers nothing at all. The
record the check reads is the draft's unwrapped attributes beside its unwrapped
relationship picks (VEV-08, ASG-04/DD-536's reading of 14.6).

One read travels the app's one circuit breaker (DD-500): the 502 of VEV-06 is
raised as :class:`~aurelius_atlas_validate_entity.errors.UpstreamError` for the
root's handler — an open circuit, an unreachable server, a refused search and a
refused mint all answer the same way, never a no-rules answer.
"""

import time
from dataclasses import dataclass
from typing import Any

from aurelius_atlas_model.discovery import SearchParameters
from aurelius_atlas_model.instance import AtlasEntityHeader
from aurelius_atlas_quality import (
    GOV_RULE_TYPE_NAME,
    GovRule,
    QualityRuleError,
    evaluate_gov_entity,
    rule_from_gov_attributes,
)
from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError
from aurelius_atlas_validate_entity_client.models import GovernanceVerdict, UnreadRule, ValidationResponse
from pybreaker import CircuitBreaker, CircuitBreakerError

from aurelius_atlas_validate_entity.errors import UpstreamError
from aurelius_atlas_validate_entity.globals import BAD_GATEWAY, FAST_FAIL_SERVER, LOGGER
from aurelius_atlas_validate_entity.models import DraftEntity

MARKER_START = "*"
"""The marker that starts a paged search (SRC-08): the server answers a next marker only for a
request that carries one, so the walk starts here, not without a marker."""

MARKER_END = "-1"
"""The marker the server answers after the last page (SRC-08)."""

SEARCH_LIMIT = 100
"""The page size of the rule search: the corpus is dozens of rules, and the walk pages to the end."""

RULE_ATTRIBUTES: tuple[str, ...] = (
    "name",
    "qualifiedName",
    "active",
    "qualityDimension",
    "expression",
    "dqcheckkind",
    "dqattribute",
    "dqanyOf",
    "compliantMessage",
    "nonCompliantMessage",
)
"""The rule attributes the search answers (VEV-03): the search refuses a name the type does not
have, so only the governance type's own attributes and its supertypes' ``name`` and
``qualifiedName`` are asked — the qualified name carries the type the rule is for (VEV-07, LAS-13).
The stored ``expression`` is asked to be seen — the vocabulary never reads it (DV-146)."""


def _raw(value: object) -> object:
    """The bare value of a webapp-wrapped attribute: ``{"raw": x}`` is ``x`` (DV-132)."""
    if isinstance(value, dict) and "raw" in value:
        return value["raw"]
    return value


def is_active(attributes: dict[str, Any]) -> bool:
    """Whether a rule is ACTIVE: only the boolean false is not (VEV-03, 12.2's reading).

    A missing ``active``, or one stored as text (the corpus holds both shapes), is active —
    matching what the legacy job treated as running rules.
    """
    return _raw(attributes.get("active")) is not False


@dataclass(frozen=True)
class RuleEntry:
    """One rule of one read: its type, its readable check or the reason it has none (VEV-03, VEV-07).

    ``check`` is the vocabulary's rule; a readable rule has one. An ACTIVE rule the
    vocabulary cannot read has none, and :attr:`unread` names why (VEV-03, DV-146).
    ``type_name`` is the type the rule's qualified name names (VEV-07): it is never
    none, because a rule naming no type enters the read set nowhere.
    """

    guid: str
    name: str
    type_name: str
    check: GovRule | None = None
    error: str | None = None

    @property
    def unread(self) -> UnreadRule:
        """The unread entry for the answer of a call this rule's type matches (VEV-03)."""
        return UnreadRule(ruleGuid=self.guid, ruleName=self.name, error=self.error or "")


class VerdictEngine:
    """The rules door and the verdict assembly: search, cache, run, scoped by type (VEV-02/03/05/07).

    Args:
        atlas: The catalogue client, carrying the app's own identity (VEV-04).
        breaker: The leg's one circuit breaker (VEV-06, DD-500).
        cache_seconds: How long a read set is held; 0 reads on every call (VEV-05).
    """

    def __init__(self, atlas: AtlasClient, breaker: CircuitBreaker, cache_seconds: float) -> None:
        self._atlas = atlas
        self._breaker = breaker
        self._cache_seconds = cache_seconds
        self._cached: tuple[RuleEntry, ...] | None = None
        self._expires_at = 0.0

    async def evaluate_draft(self, draft: DraftEntity) -> ValidationResponse:
        """Run the draft's type's ACTIVE readable rules over the draft (VEV-02/05/07/08).

        The rules ride the cache; the draft never does — each call answers over
        what it was sent. Only the rules of the draft's own type answer (VEV-07):
        the verdicts and unread entries of a foreign type's rules stay out of the
        call wholly. A failed rules read raises as VEV-05/06 say: a 502, never an
        answer with no rules.
        """
        entries = await self.rules()
        matching = [entry for entry in entries if entry.type_name == draft.type_name]
        record = _draft_record(draft)
        verdicts = [
            GovernanceVerdict(
                ruleGuid=rule.guid or "",
                ruleName=rule.name,
                attribute=rule.attribute,
                dimension=rule.dimension.value,
                compliant=verdict.compliant,
                message=verdict.message,
            )
            for entry in matching
            if (rule := entry.check) is not None
            for verdict in (evaluate_gov_entity(rule, record),)
        ]
        return ValidationResponse(
            verdicts=verdicts,
            unreadRules=[entry.unread for entry in matching if entry.check is None],
        )

    async def rules(self) -> tuple[RuleEntry, ...]:
        """The read set: the cached one while fresh, a fresh read otherwise (VEV-05).

        A failed read caches nothing — the next call reads again — and answers
        the 502 of VEV-06. The breaker wraps the whole walk: one circuit counts
        the leg, not each page (DD-500). The set holds every type's rules; the
        type filter of VEV-07 runs per call on it.
        """
        now = time.monotonic()
        if self._cached is not None and now < self._expires_at:
            return self._cached
        try:
            with self._breaker.calling():
                rules = await self._read()
        except CircuitBreakerError as error:
            raise UpstreamError(BAD_GATEWAY, FAST_FAIL_SERVER) from error
        except AtlasClientError as error:
            LOGGER.warning("The rule search failed, answered 502: %s", error)
            raise UpstreamError(BAD_GATEWAY, "the catalogue refused the rule search") from error
        self._cached = rules
        self._expires_at = now + self._cache_seconds
        return rules

    async def _read(self) -> tuple[RuleEntry, ...]:
        """The paged walk of the rule search (VEV-03): every header, until the end marker."""
        entries: list[RuleEntry] = []
        marker: str | None = MARKER_START
        while True:
            parameters = SearchParameters(
                type_name=GOV_RULE_TYPE_NAME,
                exclude_deleted_entities=True,
                include_sub_types=False,
                limit=SEARCH_LIMIT,
                marker=marker,
                attributes=list(RULE_ATTRIBUTES),
            )
            result = await self._atlas.search.search_with_parameters(parameters)
            for header in result.entities or []:
                entry = _entry_from_header(header)
                if entry is not None:
                    entries.append(entry)
            if not result.next_marker or result.next_marker == MARKER_END:
                return tuple(entries)
            marker = result.next_marker


def _rule_type(qualified_name: object) -> str | None:
    """The type a rule's qualified name names before the first ``--`` (VEV-07, LAS-13).

    ``m4i_dataset--name`` is for ``m4i_dataset``. A qualified name with no ``--``,
    or none before it, names no type, and the rule judges nothing anywhere — the
    reading the store's own App Search verdicts keep (LAS-13, ASG-03).
    """
    type_name, separator, _ = str(qualified_name or "").partition("--")
    if not separator or not type_name:
        return None
    return type_name


def _entry_from_header(header: AtlasEntityHeader) -> RuleEntry | None:
    """One search header as a read-set entry, or nothing (VEV-03, VEV-07).

    An inactive rule enters nowhere: it runs nowhere and is no news (12.2's
    reading). A rule naming no type enters nowhere either (VEV-07): it is for no
    draft, so it answers no verdict and rides no call's unread list. An active
    rule the vocabulary cannot read — the stored expression rule — enters as
    unread, with the cause, never executed (DV-146).
    """
    attributes = dict(header.attributes or {})
    guid = str(header.guid)
    if not is_active(attributes):
        return None
    type_name = _rule_type(attributes.get("qualifiedName"))
    if type_name is None:
        return None
    plain = {key: _raw(value) for key, value in attributes.items()}
    plain["guid"] = guid
    name = str(_raw(attributes.get("name")) or header.display_text or "")
    try:
        return RuleEntry(guid=guid, name=name, type_name=type_name, check=rule_from_gov_attributes(plain))
    except QualityRuleError as cause:
        return RuleEntry(guid=guid, name=name, type_name=type_name, error=str(cause))


def _draft_record(draft: DraftEntity) -> dict[str, Any]:
    """The record the checks run over: the draft's attributes beside its picks (VEV-08, DD-632).

    A ``{"raw": x}`` value reads as ``x`` — the unwrapping the rule read has always
    applied, and what a draft's wrapped value needs not to count as content. Each
    relationship key rides the draft's own value, unwrapped whole: a list of picks
    holds content by its length, a single pick by being there, and a ``null`` (a
    cleared picker) by nothing — the reading ASG-04/DD-536 gives a stored entity's
    ends, and an unsaved draft can only answer as its own picks, never resolved.
    """
    record: dict[str, Any] = {name: _raw(value) for name, value in draft.attributes.items()}
    for name, picks in (draft.relationship_attributes or {}).items():
        record[name] = _raw(picks)
    return record

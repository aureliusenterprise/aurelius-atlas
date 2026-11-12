"""The rules door: the cached ACTIVE rules and the draft's verdicts (VEV-02/03/05; DD-498, DD-500).

The rules arrive by the server's basic search of ``m4i_gov_data_quality``, paged by
marker to the end (VEV-03, 12.2's reading). A rule is ACTIVE unless its ``active``
attribute says otherwise, and the vocabulary's reading of it either yields a
:class:`~aurelius_atlas_quality.GovRule` or names why it cannot (VEV-03, DV-146):
an unread rule is recorded, never executed. The read set is cached for
``RULES_CACHE_SECONDS`` (VEV-05) — the draft always rides live.

One read travels the app's one circuit breaker (DD-500): the 502 of VEV-06 is
raised as :class:`~aurelius_atlas_validate_entity.errors.UpstreamError` for the
root's handler — an open circuit, an unreachable server, a refused search and a
refused mint all answer the same way, never a no-rules answer.
"""

import time
from collections.abc import Mapping
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
have, so only the governance type's own attributes and the supertype's ``name`` are asked. The
stored ``expression`` is asked to be seen — the vocabulary never reads it (DV-146)."""


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
class RuleSet:
    """One read of the catalogue: the rules to run, and the ones the vocabulary cannot read (VEV-03)."""

    rules: tuple[GovRule, ...] = ()
    unread: tuple[UnreadRule, ...] = ()


class VerdictEngine:
    """The rules door and the verdict assembly: search, cache, run (VEV-02/03/05).

    Args:
        atlas: The catalogue client, carrying the app's own identity (VEV-04).
        breaker: The leg's one circuit breaker (VEV-06, DD-500).
        cache_seconds: How long a read set is held; 0 reads on every call (VEV-05).
    """

    def __init__(self, atlas: AtlasClient, breaker: CircuitBreaker, cache_seconds: float) -> None:
        self._atlas = atlas
        self._breaker = breaker
        self._cache_seconds = cache_seconds
        self._cached: RuleSet | None = None
        self._expires_at = 0.0

    async def evaluate_draft(self, attributes: Mapping[str, Any]) -> ValidationResponse:
        """Run every ACTIVE readable rule over the draft's attributes (VEV-02, VEV-05).

        The rules ride the cache; the draft never does — each call answers over
        the attributes it was sent. A failed rules read raises as VEV-05/06 say:
        a 502, never an answer with no rules.
        """
        rules = await self.rules()
        verdicts = [
            GovernanceVerdict(
                ruleGuid=rule.guid or "",
                ruleName=rule.name,
                attribute=rule.attribute,
                dimension=rule.dimension.value,
                compliant=verdict.compliant,
                message=verdict.message,
            )
            for rule in rules.rules
            for verdict in (evaluate_gov_entity(rule, attributes),)
        ]
        return ValidationResponse(verdicts=verdicts, unreadRules=list(rules.unread))

    async def rules(self) -> RuleSet:
        """The rule set: the cached one while fresh, a fresh read otherwise (VEV-05).

        A failed read caches nothing — the next call reads again — and answers
        the 502 of VEV-06. The breaker wraps the whole walk: one circuit counts
        the leg, not each page (DD-500).
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

    async def _read(self) -> RuleSet:
        """The paged walk of the rule search (VEV-03): every header, until the end marker."""
        rules: list[GovRule] = []
        unread: list[UnreadRule] = []
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
                rule, unread_rule = _rule_from_header(header)
                if rule is not None:
                    rules.append(rule)
                elif unread_rule is not None:
                    unread.append(unread_rule)
            if not result.next_marker or result.next_marker == MARKER_END:
                return RuleSet(rules=tuple(rules), unread=tuple(unread))
            marker = result.next_marker


def _rule_from_header(header: AtlasEntityHeader) -> tuple[GovRule | None, UnreadRule | None]:
    """One search header as a rule, an unread entry, or nothing (VEV-03).

    An inactive rule answers neither: it runs nowhere and is no news (12.2's
    reading). An active one the vocabulary cannot read — the stored expression
    rule — is recorded with the cause, never executed (DV-146).
    """
    attributes = dict(header.attributes or {})
    guid = str(header.guid)
    if not is_active(attributes):
        return None, None
    plain = {key: _raw(value) for key, value in attributes.items()}
    plain["guid"] = guid
    name = str(_raw(attributes.get("name")) or header.display_text or "")
    try:
        return rule_from_gov_attributes(plain), None
    except QualityRuleError as cause:
        return None, UnreadRule(ruleGuid=guid, ruleName=name, error=str(cause))

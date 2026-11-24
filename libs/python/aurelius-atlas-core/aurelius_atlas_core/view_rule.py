"""``view_rule``: the verdicts door of the view family (ASG-09, AVS-12, VDR-14, ADR 071, DD-845..847).

One thin door over the verdicts index: it names a rule's GUID, reads that rule's stored verdicts with the
documents contract's read (ASG-09, DD-845), and answers one row per verdict (AVS-12, DD-846). It never reads
the rule's entity, judges nothing, and starts no task — the verdicts are what 14.6's worker last wrote
(ASG-06, ADR 071 R2), so any GUID without verdicts answers the empty list (VDR-14). Its refusals are
``VIEW_REFUSED`` in the door's shape, one message per problem (AVR-13's pattern).
"""

from collections.abc import Sequence
from typing import Any, NoReturn
from uuid import UUID

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.views import RuleVerdict

from aurelius_atlas_core.app_search_document import StoredVerdict
from aurelius_atlas_core.entity_documents import EntityDocuments


def _refuse(messages: list[str]) -> NoReturn:
    """Answer every problem found as the door's refusal (AVR-13's shape): the Atlas error, one message each.

    Raises:
        AtlasError: ``VIEW_REFUSED`` always.
    """
    raise AtlasError(AtlasErrorCode.VIEW_REFUSED, "; ".join(messages), messages=messages)


def _rows(verdicts: Sequence[StoredVerdict]) -> list[RuleVerdict]:
    """AVS-12's rows over the stored verdicts, in the read's order (DD-846).

    ``compliant`` is the document's ``"1"`` or ``"0"`` as a boolean; a document holding neither — a verdict
    written before the field's rule, or a corrupt one — answers ``null``, which the screen draws in neither
    list (DET-51).
    """
    rows = []
    for verdict in verdicts:
        compliant: bool | None
        if verdict.compliant == "1":
            compliant = True
        elif verdict.compliant == "0":
            compliant = False
        else:
            compliant = None
        rows.append(
            RuleVerdict(
                entity=verdict.entity_guid,
                compliant=compliant,
                name=verdict.name,
                message=verdict.noncompliant_message,
            )
        )
    return rows


class ViewRuleEngine:
    """The verdicts door over ``documents``' verdicts index (VDR-14, ADR 071).

    The engine parses the body itself — the route passes it through as read, as the search door does — and
    answers AVS-12's rows for the named rule's stored verdicts in ASG-09's order.
    """

    def __init__(self, documents: EntityDocuments) -> None:
        """The door reading ``documents``' verdicts index."""
        self._documents = documents

    async def verdicts(self, body: object) -> dict[str, Any]:
        """The door's answer: the stored verdict rows of the body's rule (AVS-12, VDR-14).

        Raises:
            AtlasError: ``VIEW_REFUSED`` for a body that is not an object, a missing ``rule``, or a ``rule``
                that is no GUID (AVR-13's one-message-per-problem shape).
        """
        if not isinstance(body, dict):
            _refuse(["The request body must be a JSON object"])
        errors: list[str] = []
        rule = body.get("rule")
        if rule is None:
            errors.append("The body must name a rule GUID")
        elif not isinstance(rule, str) or not _is_guid(rule):
            errors.append("rule must be a GUID")
        if errors:
            _refuse(errors)
        verdicts = await self._documents.verdicts_by_rule(str(rule))
        return {"verdicts": [row.model_dump(by_alias=True) for row in _rows(verdicts)]}


def _is_guid(value: str) -> bool:
    """Whether the text is a GUID as the REST endpoints read one (DV-161's rule, without their error codes).

    The door answers a GUID that names nothing with the empty list (VDR-14), so only the shape is checked —
    an invalid shape is the refusal, an unknown GUID is not.
    """
    try:
        UUID(value)
    except ValueError:
        return False
    return True

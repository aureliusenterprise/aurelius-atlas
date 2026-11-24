"""``view_rule``: the verdicts door's rows and refusals (AVS-12, VDR-14, DD-846, DD-847)."""

from collections.abc import Sequence

import pytest
from aurelius_atlas_core.app_search_document import StoredVerdict
from aurelius_atlas_core.view_rule import ViewRuleEngine
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode

E = "aurelius_atlas_core.view_rule.ViewRuleEngine"


def verdict(
    entity_guid: str,
    rule_guid: str,
    *,
    compliant: str = "0",
    name: str = "",
    message: str = "",
) -> StoredVerdict:
    """One stored verdict of ``entity_guid`` by the rule ``rule_guid``, named and messaged."""
    return StoredVerdict(
        id=f"{entity_guid}--{rule_guid}",
        entity_guid=entity_guid,
        guid=rule_guid,
        name=name or rule_guid.upper(),
        compliant=compliant,
        noncompliant_message=message,
    )


class HeldDocuments:
    """The narrow contract's one read the door makes, answered from a list (ASG-09's shape)."""

    def __init__(self, held: Sequence[StoredVerdict]) -> None:
        """The verdicts the store holds, as ASG-09 would answer them."""
        self._held = list(held)
        self.asked: list[str] = []

    async def verdicts_by_rule(self, rule_guid: str) -> list[StoredVerdict]:
        """The held verdicts of one rule in id order, the read recorded (ASG-09)."""
        self.asked.append(rule_guid)
        return sorted((item for item in self._held if item.guid == rule_guid), key=lambda item: item.id)


@pytest.mark.covers(f"{E}.verdicts", rules=["AVS-12", "VDR-14"])
async def test__the_door_answers_one_row_per_verdict_in_store_order() -> None:
    """AVS-12's four fields per row, ASG-09's order, refused and passed rows together (DD-846, DD-847)."""
    documents = HeldDocuments(
        [
            verdict("e-2", "66666666-6666-6666-6666-666666666666", message="e-2 fails one"),
            verdict("e-1", "66666666-6666-6666-6666-666666666666", compliant="1", message="e-1 passes"),
        ],
    )

    answer = await ViewRuleEngine(documents).verdicts({"rule": "66666666-6666-6666-6666-666666666666"})  # type: ignore[arg-type]

    assert [row["entity"] for row in answer["verdicts"]] == ["e-1", "e-2"]
    assert [row["compliant"] for row in answer["verdicts"]] == [True, False]


@pytest.mark.covers(f"{E}.verdicts", rules=["AVS-12", "VDR-14"])
async def test__a_rule_s_rows_answer_its_verdicts_and_no_others() -> None:
    """One door call answers both verdict sets the legacy asked in two (DV-201): the split is the screen's."""
    rule = "11111111-1111-1111-1111-111111111111"
    other = "22222222-2222-2222-2222-222222222222"
    documents = HeldDocuments(
        [
            verdict("e-2", rule, message="e-2 fails one"),
            verdict("e-1", rule, compliant="1", message="e-1 passes"),
            verdict("e-3", other, message="e-3 fails another"),
        ],
    )

    answer = await ViewRuleEngine(documents).verdicts({"rule": rule})  # type: ignore[arg-type]

    assert answer == {
        "verdicts": [
            {"entity": "e-1", "compliant": True, "name": rule.upper(), "message": "e-1 passes"},
            {"entity": "e-2", "compliant": False, "name": rule.upper(), "message": "e-2 fails one"},
        ]
    }  # id order, the other rule's verdict left out; the screen splits by compliant (DET-51)
    assert documents.asked == [rule]


@pytest.mark.covers(f"{E}.verdicts", rules=["AVS-12"])
async def test__a_verdict_that_is_neither_one_nor_zero_answers_null_compliant() -> None:
    """A document holding no verdict answers ``null``, which the screen draws in neither list (AVS-12, DET-51)."""
    rule = "33333333-3333-3333-3333-333333333333"
    documents = HeldDocuments([verdict("e-1", rule, compliant="")])

    answer = await ViewRuleEngine(documents).verdicts({"rule": rule})  # type: ignore[arg-type]

    assert answer["verdicts"][0]["compliant"] is None


@pytest.mark.covers(f"{E}.verdicts", rules=["VDR-14"])
async def test__a_guid_without_verdicts_answers_the_empty_list() -> None:
    """The door never reads the rule: any GUID without verdict documents answers none (VDR-14, ADR 071 R2)."""
    documents = HeldDocuments([verdict("e-1", "44444444-4444-4444-4444-444444444444")])

    answer = await ViewRuleEngine(documents).verdicts({"rule": "55555555-5555-5555-5555-555555555555"})  # type: ignore[arg-type]

    assert answer == {"verdicts": []}
    assert len(documents.asked) == 1  # the verdicts index only — no entity read exists here (DD-847)


@pytest.mark.covers(f"{E}.verdicts", rules=["VDR-14"])
@pytest.mark.parametrize(
    ("body", "message"),
    [
        (None, "The request body must be a JSON object"),
        ([], "The request body must be a JSON object"),
        ("{}", "The request body must be a JSON object"),
        ({}, "The body must name a rule GUID"),
        ({"rule": None}, "The body must name a rule GUID"),
        ({"rule": 4}, "rule must be a GUID"),
        ({"rule": "not-a-guid"}, "rule must be a GUID"),
    ],
)
async def test__every_bad_request_refuses_with_its_one_message(body: object, message: str) -> None:
    """The door's refusals in the door's shape, one message per problem (VDR-14, AVR-13's pattern)."""
    documents = HeldDocuments([])

    with pytest.raises(AtlasError) as raised:
        await ViewRuleEngine(documents).verdicts(body)  # type: ignore[arg-type]

    assert raised.value.code is AtlasErrorCode.VIEW_REFUSED
    assert raised.value.messages == [message]
    assert documents.asked == []  # a refusal never reached the store

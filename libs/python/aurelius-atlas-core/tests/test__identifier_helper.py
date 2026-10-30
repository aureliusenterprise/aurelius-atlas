"""How a DSL query's names and values are unquoted and its patterns read (DSE-06 to DSE-09).

Read from ``IdentifierHelper`` of Apache Atlas 2.4.0, and the text sub-field's words of ``free_text`` (DD-092).
"""

import pytest
from aurelius_atlas_core import identifier_helper as ih
from aurelius_atlas_core.free_text import words

H = "aurelius_atlas_core.identifier_helper"


@pytest.mark.covers(f"{H}.get", rules=["DSE-06"])
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("`Log Data`", "Log Data"),
        ("'hive_db.name'", "hive_db.name"),
        ('"a b"', "a b"),
        ("'-x'", "'-x'"),
        ("`é`", "`é`"),
        ("plain", "plain"),
        ("", None),
    ],
)
def test__get_unquotes_a_word(value: str, expected: str | None) -> None:
    """A word of ASCII letters, digits, dots and spaces inside quotes; anything else as given."""
    assert ih.get(value) == expected


@pytest.mark.covers(f"{H}.is_quoted", f"{H}.remove_quotes", rules=["DSE-06"])
def test__quotes_are_recognised_and_removed() -> None:
    """The same quote at both ends; every quote character removed, wherever it is."""
    assert [ih.is_quoted(value) for value in ("'a'", '"a"', "`a`", "'a\"", "a", "")] == [
        True,
        True,
        True,
        False,
        False,
        False,
    ]
    assert ih.remove_quotes("'it''s' \"x\" `y`") == "its x y"


@pytest.mark.covers(f"{H}.is_true_or_false", rules=["DSE-06"])
def test__true_or_false_in_any_case() -> None:
    """``equalsIgnoreCase``."""
    assert [ih.is_true_or_false(value) for value in ("true", "FALSE", "True", "yes", "")] == [
        True,
        True,
        True,
        False,
        False,
    ]


@pytest.mark.covers(f"{H}.get_fixed_reg_ex", f"{H}.escape_characters", f"{H}.remove_wildcards", rules=["DSE-08"])
def test__like_patterns_become_regular_expressions() -> None:
    """``*`` and ``?`` as ``.*`` and ``.``; ``@ # & ~ /`` escaped; wildcards and quotes removed to test the rest."""
    assert ih.get_fixed_reg_ex("'Tab*_?'") == "'Tab.*_.'"
    assert ih.escape_characters("Jane/.*@#&~x") == "Jane\\/.*\\@\\#\\&\\~x"
    assert ih.remove_wildcards("'sa?es*'") == "saes"


@pytest.mark.covers(f"{H}.is_complete_value", f"{H}.is_in_complete_value", rules=["DSE-09"])
def test__complete_and_incomplete_values() -> None:
    """Empty, ``0`` or ``false`` is complete; ``1`` or ``true`` incomplete; anything else neither."""
    assert [ih.is_complete_value(value) for value in ("", "0", "FALSE", "1", "2")] == [True, True, True, False, False]
    incomplete = [ih.is_in_complete_value(value) for value in ("1", "True", "0", "", "2")]
    assert incomplete == [True, True, False, False, False]


@pytest.mark.covers("aurelius_atlas_core.free_text.words", rules=["DSE-08"])
def test__words_are_lower_cased_runs_of_word_characters() -> None:
    """The in-memory reading of the text sub-field's analysis: ``_`` joins a word, other characters split it."""
    assert words("Joe BI sales_fact/2014-v2") == ["joe", "bi", "sales_fact", "2014", "v2"]

from pathlib import Path

import pytest
from aurelius_atlas_trace.rules import DuplicateRuleError, Increment, read_rules


def write_spec(directory: Path, name: str, text: str) -> Path:
    """Write one specification file."""
    path = directory / name
    path.write_text(text)
    return path


@pytest.mark.covers("aurelius_atlas_trace.rules.read_rules", rules=["TRC-08"])
def test__read_rules_reads_the_first_column_of_rule_tables(tmp_path: Path) -> None:
    """Rows whose first cell is a rule id are rules; other tables and prose are not."""
    spec = write_spec(
        tmp_path,
        "0-2-sample.md",
        "# 0.2 Sample\n\nMentions ABC-09 in prose.\n\n"
        "| Id | Rule |\n| --- | --- |\n| ABC-01 | One |\n|ABC-02|Two|\n\n"
        "| Not delivered | By |\n| --- | --- |\n| Something | 0.3 |\n",
    )

    rules = read_rules(tmp_path, Increment(0, 2))

    assert sorted(rules) == ["ABC-01", "ABC-02"]
    assert rules["ABC-01"].increment == Increment(0, 2)
    assert rules["ABC-01"].spec == spec


@pytest.mark.covers("aurelius_atlas_trace.rules.read_rules", rules=["TRC-08"])
def test__read_rules_starts_at_the_enforced_increment(tmp_path: Path) -> None:
    """Earlier increments and files not named ``N-M-slug.md`` are ignored; 0.10 sorts after 0.2."""
    write_spec(tmp_path, "0-1-old.md", "| OLD-01 | Old |\n")
    write_spec(tmp_path, "0-2-now.md", "| NOW-01 | Now |\n")
    write_spec(tmp_path, "0-10-later.md", "| LAT-01 | Later |\n")
    write_spec(tmp_path, "template.md", "| XXX-01 | Template |\n")

    assert sorted(read_rules(tmp_path, Increment(0, 2))) == ["LAT-01", "NOW-01"]


@pytest.mark.covers("aurelius_atlas_trace.rules.read_rules", rules=["TRC-08"])
def test__read_rules_refuses_a_rule_defined_twice(tmp_path: Path) -> None:
    """The same id in two specifications is an error that names both."""
    write_spec(tmp_path, "0-2-a.md", "| ABC-01 | One |\n")
    write_spec(tmp_path, "0-3-b.md", "| ABC-01 | Again |\n")
    enforce_from = Increment(0, 2)

    with pytest.raises(DuplicateRuleError, match=r"ABC-01 is defined in both 0-2-a\.md and 0-3-b\.md"):
        read_rules(tmp_path, enforce_from)


@pytest.mark.covers("aurelius_atlas_trace.rules.Increment.parse")
def test__increment_parse_reads_major_and_minor() -> None:
    """``N.M`` becomes a numerically ordered increment."""
    assert Increment.parse("0.10") == Increment(0, 10)
    assert Increment.parse("0.10") > Increment.parse("0.9")
    assert str(Increment.parse("2.3")) == "2.3"
    with pytest.raises(ValueError, match="not enough values"):
        Increment.parse("1")

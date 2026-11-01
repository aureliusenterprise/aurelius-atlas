from pathlib import Path

import pytest
from aurelius_atlas_trace.rules import DuplicateRuleError, Increment, read_rules


def write_spec(directory: Path, name: str, text: str) -> Path:
    """Write one specification file, creating its directories."""
    directory.mkdir(parents=True, exist_ok=True)
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

    rules = read_rules([tmp_path], Increment(0, 2))

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

    assert sorted(read_rules([tmp_path], Increment(0, 2))) == ["LAT-01", "NOW-01"]


@pytest.mark.covers("aurelius_atlas_trace.rules.read_rules", rules=["TRC-08"])
def test__read_rules_reads_the_per_project_layout(tmp_path: Path) -> None:
    """Below each root, ``N-M-slug/spec.md`` is the increment's specification; other files in it are not."""
    first = write_spec(tmp_path / "apps" / "one" / "specs" / "2-6-parts", "spec.md", "| ONE-01 | First |\n")
    second = write_spec(tmp_path / "apps" / "two" / "specs" / "2-6-parts", "spec.md", "| TWO-01 | Second |\n")
    write_spec(tmp_path / "apps" / "one" / "specs" / "2-6-parts", "design.md", "| NOPE-01 | Not a spec |\n")
    write_spec(tmp_path / "apps" / "three" / "specs" / "notes", "spec.md", "| NOPE-02 | Not an increment |\n")

    rules = read_rules([tmp_path], Increment(0, 2))

    assert sorted(rules) == ["ONE-01", "TWO-01"]
    assert rules["ONE-01"].spec == first
    assert rules["TWO-01"].spec == second
    assert rules["ONE-01"].increment == Increment(2, 6)


@pytest.mark.covers("aurelius_atlas_trace.rules.read_rules", rules=["TRC-08"])
def test__read_rules_reads_a_letter_suffix_directory(tmp_path: Path) -> None:
    """An increment directory may carry a letter slug suffix, like ``7-4a-search``."""
    spec = write_spec(tmp_path / "7-4a-search", "spec.md", "| SRH-01 | Searched |\n")

    rules = read_rules([tmp_path], Increment(0, 2))

    assert rules["SRH-01"].increment == Increment(7, 4)
    assert rules["SRH-01"].spec == spec


@pytest.mark.covers("aurelius_atlas_trace.rules.read_rules", rules=["TRC-08"])
def test__read_rules_skips_pruned_directories(tmp_path: Path) -> None:
    """Vendored trees are never searched."""
    write_spec(tmp_path / "node_modules" / "pkg" / "specs" / "9-9-vendored", "spec.md", "| VEN-01 | Hidden |\n")
    write_spec(tmp_path / "specs" / "9-9-real", "spec.md", "| REA-01 | Found |\n")

    assert sorted(read_rules([tmp_path], Increment(0, 2))) == ["REA-01"]


@pytest.mark.covers("aurelius_atlas_trace.rules.read_rules", rules=["TRC-08"])
def test__read_rules_takes_parts_of_one_increment_as_one_source_of_truth(tmp_path: Path) -> None:
    """The same id in the parts of one increment is fine when the rows agree, an error when they differ."""
    row = "| ENT-07 | The endpoint answers |\n"
    write_spec(tmp_path / "one" / "specs" / "2-6-slug", "spec.md", row)
    write_spec(tmp_path / "two" / "specs" / "2-6-slug", "spec.md", "|  ENT-07 |The endpoint answers|\n")

    assert sorted(read_rules([tmp_path / "one", tmp_path / "two"], Increment(0, 2))) == ["ENT-07"]

    write_spec(tmp_path / "two" / "specs" / "2-6-slug", "spec.md", "| ENT-07 | The endpoint refuses |\n")
    with pytest.raises(DuplicateRuleError, match=r"ENT-07 is .*\| in .* and .* in 2-6-slug/spec\.md"):
        read_rules([tmp_path / "one", tmp_path / "two"], Increment(0, 2))


@pytest.mark.covers("aurelius_atlas_trace.rules.read_rules", rules=["TRC-08"])
def test__read_rules_ignores_link_depth_in_shared_rows(tmp_path: Path) -> None:
    """Two parts of one increment restate a shared row at different tree depths: the same rule."""
    row = "| ESD-05 | The heap is fixed ([ADR 006](../adr/006-x.md)) |\n"
    write_spec(tmp_path / "a" / "specs" / "0-2-slug", "spec.md", row)
    write_spec(
        tmp_path / "b" / "c" / "specs" / "0-2-slug",
        "spec.md",
        "| ESD-05 | The heap is fixed ([ADR 006](../../adr/006-x.md)) |\n",
    )

    assert sorted(read_rules([tmp_path], Increment(0, 2))) == ["ESD-05"]


@pytest.mark.covers("aurelius_atlas_trace.rules.read_rules", rules=["TRC-08"])
def test__read_rules_refuses_a_rule_defined_twice(tmp_path: Path) -> None:
    """The same id in two increments is an error that names both files."""
    write_spec(tmp_path, "0-2-a.md", "| ABC-01 | One |\n")
    write_spec(tmp_path, "0-3-b.md", "| ABC-01 | Again |\n")
    enforce_from = Increment(0, 2)

    with pytest.raises(DuplicateRuleError, match=r"ABC-01 is defined in both 0-2-a\.md and 0-3-b\.md"):
        read_rules([tmp_path], enforce_from)


@pytest.mark.covers("aurelius_atlas_trace.rules.Increment.parse")
def test__increment_parse_reads_major_and_minor() -> None:
    """``N.M`` becomes a numerically ordered increment."""
    assert Increment.parse("0.10") == Increment(0, 10)
    assert Increment.parse("0.10") > Increment.parse("0.9")
    assert str(Increment.parse("2.3")) == "2.3"
    with pytest.raises(ValueError, match="not enough values"):
        Increment.parse("1")

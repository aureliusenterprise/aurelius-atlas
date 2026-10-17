import pytest
from aurelius_atlas_parity.path import PathError, Wildcard, format_location, parse_path

DOCUMENT = {"entities": [{"guid": "a", "name": "x"}, {"guid": "b"}], "odd key": {"k": 1}, "count": 2}


@pytest.mark.covers("aurelius_atlas_parity.path.parse_path", rules=["SCN-07"])
@pytest.mark.parametrize(
    ("text", "segments"),
    [
        ("$", ()),
        ("$.entities", ("entities",)),
        ("$.entities[0].guid", ("entities", 0, "guid")),
        ("$['odd key'].k", ("odd key", "k")),
        ("$.entities[*].guid", ("entities", Wildcard(), "guid")),
        ("$.attr-name", ("attr-name",)),
    ],
)
def test__parse_path_reads_the_subset(text: str, segments: tuple[object, ...]) -> None:
    """Root, names, quoted names, indexes and the wildcard parse into segments."""
    assert parse_path(text).segments == segments


@pytest.mark.covers("aurelius_atlas_parity.path.parse_path", rules=["SCN-07"])
@pytest.mark.parametrize("text", ["entities", "$..guid", "$.entities[-1]", "$[?(@.guid)]", "$.", "$['x"])
def test__parse_path_rejects_everything_else(text: str) -> None:
    """Recursive descent, filters, negative indexes and anything malformed are refused, naming the path."""
    with pytest.raises(PathError, match="is not a path"):
        parse_path(text)


@pytest.mark.covers("aurelius_atlas_parity.path.JsonPath.find", rules=["SCN-07"])
@pytest.mark.parametrize(
    ("text", "matches"),
    [
        ("$", [((), DOCUMENT)]),
        ("$.count", [(("count",), 2)]),
        ("$.entities[1].guid", [(("entities", 1, "guid"), "b")]),
        ("$.entities[*].guid", [(("entities", 0, "guid"), "a"), (("entities", 1, "guid"), "b")]),
        ("$.entities[*].name", [(("entities", 0, "name"), "x")]),
        ("$['odd key'][*]", [(("odd key", "k"), 1)]),
        ("$.entities[5]", []),
        ("$.count.deeper", []),
        ("$.missing", []),
    ],
)
def test__find_returns_every_match_in_document_order(text: str, matches: list[object]) -> None:
    """Wildcards visit arrays and objects; a step into something absent matches nothing."""
    assert parse_path(text).find(DOCUMENT) == matches


@pytest.mark.covers("aurelius_atlas_parity.path.JsonPath.parent")
def test__parent_drops_the_last_segment() -> None:
    """The parent of a path is its prefix; the root is its own parent."""
    assert parse_path("$.a[0].b").parent.segments == ("a", 0)
    assert parse_path("$").parent.segments == ()


@pytest.mark.covers("aurelius_atlas_parity.path.format_location", rules=["SCN-11"])
def test__format_location_writes_a_readable_path() -> None:
    """Locations print as paths; names that are not identifiers are quoted."""
    assert format_location(()) == "$"
    assert format_location(("entities", 0, "guid")) == "$.entities[0].guid"
    assert format_location(("odd key", "a.b")) == "$['odd key']['a.b']"

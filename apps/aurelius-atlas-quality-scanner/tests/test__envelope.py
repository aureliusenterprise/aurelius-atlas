"""The source envelope and the router (12.4a): the shape of one source, and the reader choice by kind."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from aurelius_atlas_quality_scanner.settings import (
    KIND_CONFIG_SCHEMAS,
    SOURCE_MAP_ERROR,
    ScannerSettings,
    SourceEntry,
)
from aurelius_atlas_quality_scanner.sources import (
    KIND_NOT_AVAILABLE,
    NO_FILE,
    NO_SOURCE,
    TRUNCATED,
    SourceRouter,
)
from pydantic import ValidationError

CSV_TEXT = "total,region\n1,north\n2,south\n"


def _file_source(path: object, dataset: dict[str, str] | None = None) -> dict[str, object]:
    """One ``file`` source's JSON shape, naming its dataset (by name unless a test names otherwise)."""
    return {
        "dataset": {"qualifiedName": "/d3"} if dataset is None else dataset,
        "kind": "file",
        "config": {"path": path},
    }


def _entry(path: str, dataset: dict[str, str] | None = None) -> SourceEntry:
    """The parsed source for one file path, for the router's list."""
    return SourceEntry.model_validate(_file_source(path, dataset))


@pytest.mark.covers("aurelius_atlas_quality_scanner.settings.ScannerSettings._parse_sources", rules=["DQS-17"])
def test_a_source_object_parses(tmp_path: Path, settings: Callable[..., ScannerSettings]) -> None:
    """DQS-17: a {dataset, kind, config} source is the accepted shape, and its config path survives."""
    made = settings(sources=[_file_source(str(tmp_path / "d3.csv"))])
    assert made.sources[0].kind == "file"
    assert made.sources[0].dataset.qualified_name == "/d3"
    assert made.sources[0].config["path"] == str(tmp_path / "d3.csv")


@pytest.mark.covers("aurelius_atlas_quality_scanner.settings.DatasetIdentity._exactly_one", rules=["DQS-20"])
@pytest.mark.parametrize(
    "dataset",
    [
        pytest.param({"qualifiedName": "/d3"}, id="a name"),
        pytest.param({"guid": "g-1"}, id="a guid"),
    ],
)
def test_a_dataset_names_one_identity(dataset: dict[str, str], settings: Callable[..., ScannerSettings]) -> None:
    """DQS-20: a source names its dataset by qualified name, or by guid."""
    made = settings(sources=[_file_source("/x.csv", dataset)])
    assert made.sources[0].dataset.key() in {"/d3", "g-1"}


@pytest.mark.covers("aurelius_atlas_quality_scanner.settings.DatasetIdentity._exactly_one", rules=["DQS-20"])
@pytest.mark.parametrize(
    "dataset",
    [
        pytest.param({"guid": "g-1", "qualifiedName": "/d3"}, id="both identities"),
        pytest.param({}, id="neither identity"),
    ],
)
def test_a_dataset_with_two_or_no_identities_is_a_settings_error(
    dataset: dict[str, str], settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-20: exactly one of the two identities, always."""
    with pytest.raises(ValidationError):
        settings(sources=[_file_source("/x.csv", dataset)])


@pytest.mark.covers("aurelius_atlas_quality_scanner.settings.ScannerSettings._check_sources_unique", rules=["DQS-17"])
def test_a_dataset_named_twice_is_a_settings_error(settings: Callable[..., ScannerSettings]) -> None:
    """DQS-17: two sources for one dataset would leave the router with two answers — a settings error."""
    with pytest.raises(ValidationError):
        settings(sources=[_file_source("/a.csv"), _file_source("/b.csv")])


@pytest.mark.covers(
    "aurelius_atlas_quality_scanner.settings.ScannerSettings._parse_sources", rules=["DQS-17", "DQS-19"]
)
@pytest.mark.covers("aurelius_atlas_quality_scanner.settings.SourceEntry._check_config", rules=["DQS-17", "DQS-19"])
@pytest.mark.parametrize(
    "source",
    [
        pytest.param("/data/d3.csv", id="a bare path (the shape before 12.4a)"),
        pytest.param({"dataset": {"qualifiedName": "/d3"}, "kind": "file"}, id="no config"),
        pytest.param({"dataset": {"qualifiedName": "/d3"}, "config": {"path": "/d3.csv"}}, id="no kind"),
        pytest.param({"kind": "file", "config": {"path": "/d3.csv"}}, id="no dataset"),
        pytest.param(
            {"dataset": {"qualifiedName": "/d3"}, "kind": "file", "config": {}}, id="a file config without a path"
        ),
        pytest.param(
            {"dataset": {"qualifiedName": "/d3"}, "kind": "file", "config": {"path": 7}},
            id="a path that is not a string",
        ),
    ],
)
def test_a_malformed_source_is_a_settings_error(source: object, settings: Callable[..., ScannerSettings]) -> None:
    """DQS-17: every source that is not a {dataset, kind, config} object fails the settings."""
    with pytest.raises(ValidationError) as raised:
        settings(sources=[source])
    assert "sources" in str(raised.value)


@pytest.mark.covers("aurelius_atlas_quality_scanner.settings.ScannerSettings._parse_sources", rules=["DQS-17"])
def test_the_env_string_of_sources_parses_and_a_map_shape_names_the_array(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DQS-17: the environment's JSON array is read; the old map shape fails, naming the array."""
    monkeypatch.setenv("AURELIUS_ATLAS_QUALITY_SCANNER_CLIENT_SECRET", "s")
    monkeypatch.setenv(
        "AURELIUS_ATLAS_QUALITY_SCANNER_SOURCES",
        '[{"dataset": {"qualifiedName": "/d3"}, "kind": "file", "config": {"path": "/x.csv"}}]',
    )
    parsed = ScannerSettings()  # pyright: ignore[reportCallIssue] - read from the environment
    assert parsed.sources[0].kind == "file"
    monkeypatch.setenv("AURELIUS_ATLAS_QUALITY_SCANNER_SOURCES", "{}")
    assert ScannerSettings().sources == []  # pyright: ignore[reportCallIssue] - the empty dev default is no sources
    monkeypatch.setenv("AURELIUS_ATLAS_QUALITY_SCANNER_SOURCES", '{"/d3": "/x.csv"}')
    with pytest.raises(ValidationError) as raised:
        ScannerSettings()  # pyright: ignore[reportCallIssue]
    assert SOURCE_MAP_ERROR in str(raised.value)


@pytest.mark.covers("aurelius_atlas_quality_scanner.settings.SourceEntry._check_config", rules=["DQS-18"])
def test_an_unknown_kind_is_accepted_by_the_settings() -> None:
    """DQS-18: the settings do not know the future kinds; a newer source loads, and the router skips it (DD-462)."""
    entry = SourceEntry.model_validate(
        {"dataset": {"qualifiedName": "/d9"}, "kind": "postgres", "config": {"table": "t"}}
    )
    assert entry.kind not in KIND_CONFIG_SCHEMAS


@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.SourceRouter.read", rules=["DQS-18"])
def test_the_router_reads_a_file_dataset_through_the_envelope(tmp_path: Path) -> None:
    """DQS-18: a file source reaches the file reader, and its frame is the extract's."""
    path = tmp_path / "d3.csv"
    path.write_text(CSV_TEXT)
    router = SourceRouter([_entry(str(path))], 1000)
    read = router.read("/d3", "g")
    assert read is not None
    assert read.frame.height == 2


@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.SourceRouter.skip_reason", rules=["DQS-18"])
def test_a_kind_the_job_does_not_have_is_a_skip_with_its_reason() -> None:
    """DQS-18: an unknown kind skips its dataset with the reason, and the run continues (DQS-13)."""
    entry = SourceEntry.model_validate(
        {"dataset": {"qualifiedName": "/d9"}, "kind": "postgres", "config": {"table": "t"}}
    )
    router = SourceRouter([entry], 1000)
    assert router.read("/d9", "g") is None
    assert router.skip_reason("/d9", "g") == KIND_NOT_AVAILABLE


@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.SourceRouter.skip_reason", rules=["DQS-18"])
def test_a_dataset_no_source_names_keeps_the_reader_s_reason() -> None:
    """DQS-18: an un-named dataset is skipped exactly as 12.2 skipped it — no source configured."""
    router = SourceRouter([], 1000)
    assert router.read("/d9", "g") is None
    assert router.skip_reason("/d9", "g") == NO_SOURCE


@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.SourceRouter.read", rules=["DQS-20"])
def test_a_guid_source_answers_its_dataset_by_guid(tmp_path: Path) -> None:
    """DQS-20: a source keyed by guid answers the dataset with that guid, whatever its name is."""
    path = tmp_path / "d3.csv"
    path.write_text(CSV_TEXT)
    router = SourceRouter([_entry(str(path), {"guid": "g-1"})], 1000)
    read = router.read("/renamed/table", "g-1")
    assert read is not None
    assert read.frame.height == 2


@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.SourceRouter.read", rules=["DQS-20"])
def test_the_guid_source_answers_before_the_name_source(tmp_path: Path) -> None:
    """DQS-20: a guid source and a name source for one dataset — the guid source answers (the stable id)."""
    by_guid = tmp_path / "by_guid.csv"
    by_guid.write_text("n\n1\n")
    by_name = tmp_path / "by_name.csv"
    by_name.write_text("n\n1\n2\n3\n4\n5\n")
    router = SourceRouter(
        [_entry(str(by_guid), {"guid": "g-1"}), _entry(str(by_name), {"qualifiedName": "/d3"})],
        1000,
    )
    read = router.read("/d3", "g-1")
    assert read is not None
    assert read.frame.height == 1


@pytest.mark.covers("aurelius_atlas_quality_scanner.sources.SourceRouter.read", rules=["DQS-19"])
def test_a_file_source_keeps_the_reader_s_own_reasons_and_budget(
    tmp_path: Path, settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-19: through the envelope the file reader's floor stands — a gone path, and the cut with its notice."""
    gone = SourceRouter([_entry(str(tmp_path / "gone.csv"))], 1000)
    assert gone.read("/d3", "g") is None
    assert gone.skip_reason("/d3", "g") == NO_FILE

    big = tmp_path / "big.csv"
    big.write_text("n\n" + "".join(f"{i}\n" for i in range(100)))
    router = SourceRouter([_entry(str(big))], settings(max_rows=10).max_rows)
    read = router.read("/d3", "g")
    assert read is not None
    assert read.frame.height == 10
    assert read.notice == TRUNCATED

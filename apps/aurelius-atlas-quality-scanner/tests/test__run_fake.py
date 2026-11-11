"""The CLI around the scan: exit codes and printed output (DQS-01, DQS-09)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import httpx2 as httpx
import pytest
from aurelius_atlas_quality_scanner import __main__ as cli
from fake_catalogue import FakeCatalogue, entity_with_fields, field_with_datasets, related, rule_header

if TYPE_CHECKING:
    from aurelius_atlas_otel import ClientCredentialsTokenSource

PASSING_CSV = "total\n1\n2\n3\n"
ENV = "AURELIUS_ATLAS_QUALITY_SCANNER_"


class _StubSource:
    """A token source stand-in: the real one is Keycloak's, out of scope for these tests."""

    def __init__(self, answer: str | None) -> None:
        self._answer = answer

    def bearer(self) -> str | None:
        return self._answer


def _refusing(request: httpx.Request) -> httpx.Response:  # noqa: ARG001 - the request never matters
    """Answer every catalogue call with a server error."""
    return httpx.Response(500, json={"errorCode": "ATLAS-500-00-001", "errorMessage": "store down"})


def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point the CLI settings at the fake catalogue and one local extract."""
    extract = tmp_path / "d1.csv"
    extract.write_text(PASSING_CSV)
    monkeypatch.setenv(f"{ENV}SERVER_URL", "http://atlas.test")
    monkeypatch.setenv(f"{ENV}CLIENT_ID", "scanner")
    monkeypatch.setenv(f"{ENV}CLIENT_SECRET", "secret")
    monkeypatch.setenv(
        f"{ENV}SOURCES",
        f'[{{"dataset": {{"qualifiedName": "/d1"}}, "kind": "file", "config": {{"path": "{extract}"}}}}]',
    )


def _wire(monkeypatch: pytest.MonkeyPatch, http: httpx.AsyncClient) -> None:
    """Make the CLI talk to a transport of our choice, not Keycloak and a server (e2e covers the real wiring)."""
    from aurelius_atlas_server_client import AtlasClient  # noqa: PLC0415 - the seam stands in for the real builder

    monkeypatch.setattr(cli, "build_client", lambda _settings: (AtlasClient(http, "test-token"), http))


def _seed(catalogue: FakeCatalogue) -> None:
    """The smallest catalogue that scores: one ACTIVE ``not_null`` rule over ``/d1``."""
    catalogue.add_rule_page(
        [rule_header("r1", {"name": "r1", "active": True, "dqcheckkind": "COLUMN_NOT_NULL_RATIO", "dqcolumn": "total"})]
    )
    catalogue.rules["r1"] = entity_with_fields("r1", [related("f1", "")])
    catalogue.fields["f1"] = field_with_datasets("f1", [related("/d1", "/d1")])


# ``run`` is synchronous and owns its own event loop, so these tests are plain functions.


@pytest.mark.covers("aurelius_atlas_quality_scanner.__main__.run", rules=["DQS-01"])
def test_a_clean_run_exits_zero(catalogue: FakeCatalogue, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """DQS-01: the CLI scans the bound dataset, stores once, and exits zero."""
    _seed(catalogue)
    _env(monkeypatch, tmp_path)
    http = httpx.AsyncClient(base_url="http://atlas.test", transport=catalogue.transport())
    _wire(monkeypatch, http)
    assert cli.run([]) == 0
    assert catalogue.written_by_key()["/d1/r1"]["attributes"]["verdict"] == "PASS"


@pytest.mark.covers("aurelius_atlas_quality_scanner.__main__.run", rules=["DQS-09"])
def test_a_dry_run_prints_candidates_and_stores_nothing(
    catalogue: FakeCatalogue,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """DQS-09: ``--dry-run`` exits zero, prints each candidate, and sends no write at all."""
    _seed(catalogue)
    _env(monkeypatch, tmp_path)
    http = httpx.AsyncClient(base_url="http://atlas.test", transport=catalogue.transport())
    _wire(monkeypatch, http)
    assert cli.run(["--dry-run"]) == 0
    assert catalogue.write_requests == 0
    printed = capsys.readouterr().out
    assert "would store /d1/r1 PASS score=1.0" in printed
    assert "would store /d1/overall PASS score=1.0" in printed


@pytest.mark.covers("aurelius_atlas_quality_scanner.__main__.run", rules=["DQS-01"])
def test_a_refusing_catalogue_exits_non_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """DQS-01: a catalogue call that fails ends the run with exit 1, not a crash."""
    _env(monkeypatch, tmp_path)
    http = httpx.AsyncClient(base_url="http://atlas.test", transport=httpx.MockTransport(_refusing))
    _wire(monkeypatch, http)
    assert cli.run([]) == 1


@pytest.mark.covers("aurelius_atlas_quality_scanner.__main__.run", rules=["DQS-01"])
def test_a_missing_configuration_exits_non_zero() -> None:
    """DQS-01: without a client secret there is no identity, so the run fails before any call."""
    assert cli.run([]) == 1


def test_a_refused_token_stops_the_job_before_the_scan() -> None:
    """DQS-01/DQS-10: a refused mint raises — the job never speaks anonymously (``run`` turns that into exit 1)."""
    refused = cli._tokens(cast("ClientCredentialsTokenSource", _StubSource(None)))  # noqa: SLF001 - the seam under test
    granted = cli._tokens(cast("ClientCredentialsTokenSource", _StubSource("abc")))  # noqa: SLF001 - same wrapper
    with pytest.raises(RuntimeError, match="refused"):
        refused()
    assert granted() == "abc"

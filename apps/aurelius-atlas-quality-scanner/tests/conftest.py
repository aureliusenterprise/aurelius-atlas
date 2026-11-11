"""Fixtures for the scanner's unit tests: settings, a fake catalogue, a reader, the catalogue client.

The fake catalogue (``fake_catalogue``) answers the scan's three calls over the wire, so a test
exercises the real server-client and the real read/write models, not a stand-in for them. The
reader is the app's own file reader over extracts a test writes to ``tmp_path``. Helpers live in a
module of their own because the trace check collects ``tests/`` and ``e2e/`` in one run and
same-named ``conftest`` modules collide on ``sys.path``.
"""

from __future__ import annotations

import os
from collections.abc import Callable

import httpx2 as httpx
import pytest
from aurelius_atlas_quality_scanner.settings import ENV_PREFIX, ScannerSettings
from aurelius_atlas_quality_scanner.sources import FileReader
from aurelius_atlas_server_client import AtlasClient
from fake_catalogue import FakeCatalogue
from pydantic import HttpUrl

CATALOGUE = "http://atlas.test"


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test from a clean environment (DD-458).

    ``nx test`` injects the project's ``.env`` into the task's environment and pydantic-settings
    reads it; the dev values would leak into the settings the tests build. Tests set exactly the
    variables they mean.
    """
    for name in list(os.environ):
        if name.startswith(ENV_PREFIX):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def catalogue() -> FakeCatalogue:
    """The fake catalogue the scan reads rules and bindings from and writes scores to."""
    return FakeCatalogue()


@pytest.fixture
def settings() -> Callable[..., ScannerSettings]:
    """The app settings factory: a scan identity and a bounded search page, no sources by default."""

    def make(**overrides: object) -> ScannerSettings:
        values: dict[str, object] = {"client_secret": "test-secret", "search_limit": 2}
        values.update(overrides)
        return ScannerSettings(**values)  # pyright: ignore[reportArgumentType] - the overrides are the settings' fields

    return make


@pytest.fixture
def reader() -> Callable[..., FileReader]:
    """The file reader factory: the ``sources`` map and a row budget, both by argument."""

    def make(sources: dict[str, str], max_rows: int = 1_000_000) -> FileReader:
        return FileReader(sources, max_rows)

    return make


@pytest.fixture
def client(catalogue: FakeCatalogue) -> AtlasClient:
    """The catalogue client, speaking through the fake's recording transport."""
    http = httpx.AsyncClient(base_url=str(HttpUrl(CATALOGUE)), transport=catalogue.transport())
    return AtlasClient(http, "test-token")

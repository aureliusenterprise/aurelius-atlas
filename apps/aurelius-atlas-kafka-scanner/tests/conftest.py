"""Shared fixtures: a clean environment and a settings builder (13.1)."""

import os
from collections.abc import Callable

import pytest
from aurelius_atlas_kafka_scanner.settings import ENV_PREFIX, ScannerSettings

TEST_AUTH = "test-scanner-auth"
"""The client credential every test's settings carry (KSC-09: the identity is required)."""


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test from a clean environment (DD-199).

    ``nx test`` injects the project's ``.env`` into the task's environment and
    pydantic-settings reads it; the dev values would leak into the settings the
    tests build. Tests set exactly the variables they mean.
    """
    for name in list(os.environ):
        if name.startswith(ENV_PREFIX):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def settings() -> Callable[..., ScannerSettings]:
    """Build a :class:`ScannerSettings` with the one required secret filled in."""

    def build(**overrides: object) -> ScannerSettings:
        values: dict[str, object] = {"client_secret": TEST_AUTH}
        values.update(overrides)
        return ScannerSettings(**values)  # pyright: ignore[reportArgumentType] - the overrides are the settings' fields

    return build

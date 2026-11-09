"""Unit-test fixtures: the app and its model over the fakes in ``fakes.py`` (DD-433)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from aurelius_atlas_embedder.app import create_app
from aurelius_atlas_embedder.model import Model
from aurelius_atlas_embedder.settings import EmbedderSettings
from fakes import fake_model
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def model() -> Model:
    """A model over the fake session and tokenizer."""
    return fake_model()


@pytest.fixture
def settings(tmp_path: Path) -> EmbedderSettings:
    """Settings with an empty model directory, which the fake loader never reads."""
    return EmbedderSettings(model_dir=tmp_path)


@pytest.fixture
def app(settings: EmbedderSettings, model: Model) -> FastAPI:
    """The app with the fake model as its loader's result."""
    return create_app(settings, loader=lambda _settings: _warm(model))


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A client of the started app: its model loaded."""
    with TestClient(app) as started:
        yield started


def _warm(model: Model) -> Model:
    """``model`` after one embedding, as ``load_model`` warms the real one."""
    model.embed(["warm"])
    return model

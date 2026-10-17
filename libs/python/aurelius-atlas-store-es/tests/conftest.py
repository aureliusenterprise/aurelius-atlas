from collections.abc import Callable
from pathlib import Path

import pytest
from aurelius_atlas_store_es import StoreSettings, store
from aurelius_atlas_store_es.testing.fake import FakeClient

PASSWORD = "s3cret-for-tests"  # noqa: S105 - a fixed fake credential the tests search for in output


@pytest.fixture
def password() -> str:
    """The fake password; tests search for it in output that must not contain it (STO-08)."""
    return PASSWORD


@pytest.fixture
def ca_file(tmp_path: Path) -> Path:
    """A CA file that exists; its content does not matter to the fake client."""
    path = tmp_path / "ca.pem"
    path.write_text("not a real certificate\n")
    return path


@pytest.fixture
def settings(ca_file: Path) -> StoreSettings:
    """Settings for a single local node with the test password."""
    return StoreSettings.model_validate(
        {"hosts": ["https://localhost:9200"], "password": PASSWORD, "ca_certs": ca_file},
    )


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> Callable[[], FakeClient]:
    """Replace the real client in the store module; returns a getter for the client the store built."""
    clients: list[FakeClient] = []
    prepared = FakeClient()

    def build(**kwargs: object) -> FakeClient:
        prepared.kwargs = kwargs
        clients.append(prepared)
        return prepared

    monkeypatch.setattr(store, "AsyncElasticsearch", build)
    return lambda: clients[-1] if clients else prepared

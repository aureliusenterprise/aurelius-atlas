"""Fixtures for the data2model client: the recording transport (CL-02)."""

import httpx2 as httpx
import pytest
from d2m_recorder import Recorder


@pytest.fixture
def recorder() -> Recorder:
    """The recording transport every client test answers from."""
    return Recorder()


@pytest.fixture
def tracked_client_http(recorder: Recorder) -> httpx.AsyncClient:
    """A shared ``httpx.AsyncClient`` on the recorder (the with-token pool-sharing tests)."""
    return httpx.AsyncClient(base_url="https://data2model.test", transport=recorder.transport())

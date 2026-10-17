import textwrap
from collections.abc import AsyncIterator, Callable
from pathlib import Path

import httpx
import pytest
from aurelius_atlas_parity.testing import SampleApp


@pytest.fixture
def app() -> SampleApp:
    """A fresh sample application."""
    return SampleApp()


@pytest.fixture
async def client(app: SampleApp) -> AsyncIterator[httpx.AsyncClient]:
    """A client talking to the sample application in-process."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://sample") as client:
        yield client


@pytest.fixture
def write_scenario(tmp_path: Path) -> Callable[[str, str], Path]:
    """Write a scenario file below ``tmp_path/scenarios`` and return its path."""

    def write(relative: str, text: str) -> Path:
        file = tmp_path / "scenarios" / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(textwrap.dedent(text).lstrip())
        return file

    return write

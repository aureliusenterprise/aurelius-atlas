import itertools
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from aurelius_atlas_trace.testing import SampleWorkspace, build_sample_workspace

_names = itertools.count()


@pytest.fixture
def make_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., SampleWorkspace]]:
    """Build a sample workspace whose package name no other test uses, and put it on the path."""
    package = f"sample_{next(_names)}"

    def make(**parts: str | None) -> SampleWorkspace:
        workspace = build_sample_workspace(tmp_path / "workspace", package, **parts)  # pyright: ignore[reportArgumentType]
        monkeypatch.syspath_prepend(str(workspace.project))
        return workspace

    yield make
    for name in [module for module in sys.modules if module.startswith(package)]:
        del sys.modules[name]

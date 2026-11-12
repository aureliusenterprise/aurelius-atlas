"""Chart-packaging contract (CHT-05): what ``helm package`` puts in the archive.

The publish target (CHT-05, helm.ts) builds the OCI artifact with
``helm package`` from the chart directory, and ``.helmignore`` (helm.ts's
step-4 recipe, ``helm/.helmignore-shared``) is what decides its contents. The
suite pins both halves: the twelve chart copies match the curated template,
and the archive a release ships carries the chart and none of the render
inputs — ``tests/values.test.yaml`` is a source-tree fact the gates read with
``helm template -f`` (CHT-06), never a customer artifact.
"""

from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path

import pytest
from conftest import WORKSPACE

# The twelve chart trees the release ships: every apps/ and dev/ chart plus
# the umbrella (the layout helm.ts infers its targets from).
CHART_DIRS = (
    *sorted((WORKSPACE / "apps").glob("*/helm")),
    *sorted((WORKSPACE / "dev").glob("*/helm")),
    WORKSPACE / "helm",
)
SHARED_HELMIGNORE = WORKSPACE / "helm/.helmignore-shared"
# The chart packaged in the archive guard: a leaf chart with a
# tests/values.test.yaml and no file:// dependencies of its own.
PACKAGED_CHART = WORKSPACE / "apps/aurelius-atlas-server/helm"


@pytest.mark.covers(rules=["CHT-05"])
def test__helmignore_copies_match_the_shared_template() -> None:
    """Every chart carries the curated ignore file, verbatim (helm/AGENTS.md).

    The publish gate reads each chart's own ``.helmignore``; a chart whose
    copy drifted silently ships what the template keeps out — the first cut
    of this template leaked ``tests/values.test.yaml`` into every OCI
    artifact, which is the drift this guard closes.
    """
    shared = SHARED_HELMIGNORE.read_text()
    assert "/tests/" in shared.splitlines()  # the leak's fix, pinned
    assert not [d for d in CHART_DIRS if not (d / ".helmignore").is_file()]
    drifted = [str(d) for d in CHART_DIRS if (d / ".helmignore").read_text() != shared]
    assert not drifted, f"drifted from {SHARED_HELMIGNORE.relative_to(WORKSPACE)}: {drifted}"


@pytest.mark.covers(rules=["CHT-05"])
def test__packaged_chart_ships_the_chart_and_no_test_values(tmp_path: Path) -> None:
    """The OCI tarball: chart parts in, render inputs out (CHT-05/06).

    ``helm package`` honours ``.helmignore``; the archive must carry
    Chart.yaml, values.yaml and the templates, and no ``tests/`` entry —
    the gate renders from the source tree, so the packaged copy would be
    dead weight at best and a test-values leak at worst.
    """
    packed = subprocess.run(
        ["helm", "package", str(PACKAGED_CHART), "--version", "0.0.0-local", "-d", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert packed.returncode == 0, packed.stderr
    (tarball,) = list(tmp_path.glob("*.tgz"))
    with tarfile.open(tarball) as archive:
        names = archive.getnames()
    prefix = "atlas-server/"
    assert f"{prefix}Chart.yaml" in names
    assert f"{prefix}values.yaml" in names
    assert any(n.startswith(f"{prefix}templates/") for n in names)
    assert not [n for n in names if "/tests/" in n or n.endswith("values.test.yaml")], names

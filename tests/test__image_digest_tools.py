"""Unit suite for the digest drift guard (CHT-94/96, DD-278).

Parse -> diff -> rewrite against fixture values trees: the registry and
docker stay out of this file entirely (the resolvers are injected), which
is what lets CHT-96's logic run in the plain chart suite while the real
registry comparison lives in the scheduled workflow. The CHT-94 half
asserts the repo shape the guard must not disturb: the six Aurelius image
blocks carry empty digest fields — own images stay tag-referenced, and the
pipeline bakes nothing.
"""

from __future__ import annotations

import importlib.util
import sys
from types import ModuleType

import pytest
import yaml
from conftest import PINNED, WORKSPACE


def _load(name: str) -> ModuleType:
    """Import one tools/images script by path (they are scripts, not a package)."""
    path = WORKSPACE / "tools" / "images" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclass annotations resolve via sys.modules
    spec.loader.exec_module(module)
    return module


digests = _load("chart_digests")

# A fixture values tree: one block with a fresh digest, one drifted, one
# missing (closed by the next key at its indent), plus a global.image block
# the extractor must ignore (Aurelius images spell name/tag, not repo/tag).
FIXTURE = """\
global:
    image:
        registry: ghcr.io
        namespace: aureliusenterprise
        name: aurelius-atlas-server
        tag: ""
        digest: ""
image:
    repository: dhi.io/keycloak
    tag: "26.7-debian13"
    digest: sha256:aaa
postgres:
    image:
        repository: dhi.io/postgres
        tag: "18-alpine3.23"
        digest: sha256:old
telemetry:
    image:
        repository: dhi.io/opentelemetry-collector
        tag: "0-debian13-contrib"
        resources:
            cpu: 100m
"""

CURRENT = {
    ("dhi.io/keycloak", "26.7-debian13"): "sha256:aaa",
    ("dhi.io/postgres", "18-alpine3.23"): "sha256:new",
    ("dhi.io/opentelemetry-collector", "0-debian13-contrib"): "sha256:added",
}


def _current(repository: str, tag: str) -> str | None:
    return CURRENT.get((repository, tag))


@pytest.mark.covers(rules=["CHT-96"])
def test__extract_triples_pairs_repository_tag_digest() -> None:
    """Three triples, correct fields; the name/tag block is ignored (CHT-96)."""
    triples = digests.extract_triples("values.yaml", FIXTURE)
    assert [(t.repository, t.tag) for t in triples] == [
        ("dhi.io/keycloak", "26.7-debian13"),
        ("dhi.io/postgres", "18-alpine3.23"),
        ("dhi.io/opentelemetry-collector", "0-debian13-contrib"),
    ]
    by_repo = {t.repository: t for t in triples}
    assert by_repo["dhi.io/keycloak"].digest == "sha256:aaa"
    assert by_repo["dhi.io/keycloak"].digest_line is not None
    assert by_repo["dhi.io/opentelemetry-collector"].digest is None
    assert by_repo["dhi.io/opentelemetry-collector"].digest_line is None


@pytest.mark.covers(rules=["CHT-96"])
def test__check_reports_drift_and_missing_not_match() -> None:
    """A changed tag digest and a missing digest drift; a match does not (CHT-96)."""
    drift = digests.check(digests.extract_triples("values.yaml", FIXTURE), _current)
    assert [(d.triple.repository, d.triple.digest) for d in drift] == [
        ("dhi.io/postgres", "sha256:old"),
        ("dhi.io/opentelemetry-collector", None),
    ]
    assert [d.current for d in drift] == ["sha256:new", "sha256:added"]


@pytest.mark.covers(rules=["CHT-96"])
def test__check_ignores_unresolvable_tags() -> None:
    """A registry that returns nothing is not evidence of drift (CHT-96)."""
    quiet = digests.check(digests.extract_triples("values.yaml", FIXTURE), lambda _repo, _tag: None)
    assert [d for d in quiet if d.triple.digest] == []
    # A missing digest with an unresolvable tag stays quiet too — the pair is
    # just not checkable; only a *known* different digest, or a known digest
    # beside a missing field, is drift.
    assert {d.triple.repository for d in quiet} == set()


@pytest.mark.covers(rules=["CHT-96"])
def test__fix_text_rewrites_and_inserts_digest_lines() -> None:
    """--fix replaces drifted digests and inserts missing ones in place (CHT-96)."""
    fixed = digests.fix_text(FIXTURE, _current)
    assert 'digest: "sha256:new"' in fixed  # replaced
    assert 'digest: "sha256:added"' in fixed  # inserted after the tag line
    assert "sha256:old" not in fixed
    lines = fixed.splitlines()
    inserted = lines[lines.index('        tag: "0-debian13-contrib"') + 1]
    assert inserted == '        digest: "sha256:added"'  # tag's indent
    # Everything else is byte-identical: the global block kept its empty digest.
    assert '\n        digest: ""\n' in fixed
    assert fixed.endswith("\n")


@pytest.mark.covers(rules=["CHT-96"])
def test__workspace_triples_match_the_committed_pin_map() -> None:
    """The 13 committed pins agree with the suites' PINNED map (CHT-93/96)."""
    triples = digests.extract_all(WORKSPACE)
    assert len(triples) == 13
    assert all(t.digest for t in triples), [t.repository for t in triples if not t.digest]
    for triple in triples:
        assert triple.digest == PINNED[triple.repository], triple.repository


# The six Aurelius image blocks and where each one's digest field lives
# (dotted path into its chart's values). CHT-94: not digest-pinned — the
# fields exist for operators and stay empty in every committed values file.
AURELIUS_DIGEST_PATHS = {
    "apps/aurelius-atlas-server/helm/values.yaml": "image",
    "apps/aurelius-atlas-webapp/helm/values.yaml": "image",
    "apps/aurelius-atlas-data2model/helm/values.yaml": "image",
    "apps/aurelius-atlas-lineage-model/helm/values.yaml": "image",
    "apps/aurelius-atlas-validate-entity/helm/values.yaml": "image",
    "dev/elasticsearch/helm/values.yaml": "agent.image",
}


@pytest.mark.covers(rules=["CHT-94"])
def test__repo_keeps_aurelius_digest_fields_empty() -> None:
    r"""The six Aurelius blocks carry digest: "" — the pipeline bakes nothing (CHT-94)."""
    for values_rel, dotted in AURELIUS_DIGEST_PATHS.items():
        block = yaml.safe_load((WORKSPACE / values_rel).read_text())
        for part in dotted.split("."):
            block = block[part]
        assert block["digest"] == "", f"{values_rel}: {dotted}.digest is pinned in the repo"

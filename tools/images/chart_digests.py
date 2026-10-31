"""Chart image digest pinning guard (CHT-96, DD-278).

Every chart-pinned third-party image in the workspace's Helm values carries
a committed ``digest``: installs pull immutable bytes. The digest is only
honest while it matches what the registry serves under the paired tag, and a
tag bump that forgets its digest refresh is exactly the silent break this
script catches.

``extract_triples`` parses ``(repository, tag, digest)`` triples out of
values YAML text — line-based, so ``fix_text`` can rewrite digest values in
place without reformatting the file (prettier owns layout). ``check`` diffs
those triples against a ``current`` resolver; the CLI's resolver shells out
to ``docker buildx imagetools inspect`` (never called by the unit tests,
which inject fixtures — the registry stays out of CI's chart suite).

Usage (from the workspace root):

    uv run python tools/images/chart_digests.py            # list triples
    uv run python tools/images/chart_digests.py --check    # drift vs registry
    uv run python tools/images/chart_digests.py --fix      # rewrite digests
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
VALUES_GLOBS = ("apps/*/helm/values.yaml", "dev/*/helm/values.yaml", "helm/values.yaml")

# A chart-pinned image block is `repository:` + `tag:` at the same indent
# (the Aurelius images spell name/tag under global.image instead, so this
# heuristic selects exactly the third-party pins CHT-93 covers).
_REPO_RE = re.compile(r"^(\s*)repository:\s*(\S+)\s*$")
_TAG_RE = re.compile(r'^(\s*)tag:\s*"?([^"\n]+?)"?\s*$')
_DIGEST_RE = re.compile(r'^(\s*)digest:\s*"?([^"\n]+?)"?\s*$')


@dataclass(frozen=True)
class Triple:
    """One pinned image block: its registry, tag, digest, and where."""

    source: str
    repository: str
    tag: str
    digest: str | None
    digest_line: int | None  # 1-based; None when the block has no digest line


def _triples_from_lines(source: str, lines: list[str]) -> list[Triple]:
    """Pair each ``repository:``/``tag:`` block with its ``digest:`` line (or none)."""
    triples: list[Triple] = []
    repo_indent: str | None = None
    repo: str | None = None
    tag_indent = ""
    tag = ""
    for idx, line in enumerate(lines, start=1):
        repo_match = _REPO_RE.match(line)
        if repo_match:
            repo_indent, repo = repo_match.groups()
            continue
        if repo is None:
            continue
        tag_match = _TAG_RE.match(line)
        if tag_match and tag_match.group(1) == repo_indent:
            tag_indent, tag = tag_match.groups()
            continue
        digest_match = _DIGEST_RE.match(line)
        if digest_match and tag and len(digest_match.group(1)) >= len(tag_indent):
            triples.append(Triple(source, repo, tag, digest_match.group(2), idx))
            repo, tag, repo_indent = None, "", None
            continue
        # Any other key at the block's indent closes an incomplete pair.
        if repo_indent is not None and re.match(rf"^{repo_indent}\S", line) and tag:
            triples.append(Triple(source, repo, tag, None, None))
            repo, tag, repo_indent = None, "", None
    return triples


def extract_triples(source: str, text: str) -> list[Triple]:
    """The pinned image triples in one values file's text."""
    return _triples_from_lines(source, text.splitlines())


def workspace_values_files(workspace: Path = WORKSPACE) -> list[Path]:
    """Every chart values file the guard covers, sorted."""
    found: set[Path] = set()
    for pattern in VALUES_GLOBS:
        found.update(workspace.glob(pattern))
    return sorted(found)


def extract_all(workspace: Path = WORKSPACE) -> list[Triple]:
    """The triples across every chart values file."""
    return [
        t
        for path in workspace_values_files(workspace)
        for t in extract_triples(str(path.relative_to(workspace)), path.read_text())
    ]


@dataclass(frozen=True)
class Drift:
    """A committed digest that no longer matches the registry's tag."""

    triple: Triple
    current: str


def check(triples: Iterable[Triple], current: Callable[[str, str], str | None]) -> list[Drift]:
    """Diff committed digests against the ``current`` resolver (repo, tag) -> digest."""
    drift: list[Drift] = []
    for triple in triples:
        now = current(triple.repository, triple.tag)
        if triple.digest is None:
            if now is not None:
                drift.append(Drift(triple, now))
            continue
        if now is not None and now != triple.digest:
            drift.append(Drift(triple, now))
    return drift


def fix_text(text: str, current: Callable[[str, str], str | None]) -> str:
    """Rewrite each block's digest to ``current``; insert a line when missing."""
    lines = text.splitlines()
    output: list[str] = []
    replacements: dict[int, str] = {}
    inserts: dict[int, list[str]] = {}
    for triple in _triples_from_lines(text, lines):
        now = current(triple.repository, triple.tag)
        if now is None:
            continue
        if triple.digest_line is not None:
            if triple.digest != now:
                line = lines[triple.digest_line - 1]
                digest_match = _DIGEST_RE.match(line)
                if digest_match is None:  # pragma: no cover - extractor/fixer disagree
                    message = f"line {triple.digest_line} is not a digest line: {line!r}"
                    raise AssertionError(message)
                replacements[triple.digest_line - 1] = f'{digest_match.group(1)}digest: "{now}"'
        else:
            for idx, line in enumerate(lines):
                tag_match = _TAG_RE.match(line)
                if tag_match and tag_match.group(2) == triple.tag:
                    inserts[idx] = [f'{tag_match.group(1)}digest: "{now}"']
                    break
    for idx, line in enumerate(lines):
        output.append(replacements.get(idx, line))
        output.extend(inserts.get(idx, []))
    return "\n".join(output) + ("\n" if text.endswith("\n") else "")


def registry_current(repository: str, tag: str) -> str | None:
    """The registry's current manifest digest for ``repository:tag`` (None on failure)."""
    done = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", f"{repository}:{tag}", "--format", "{{.Manifest.Digest}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    digest = done.stdout.strip()
    return digest if done.returncode == 0 and digest.startswith("sha256:") else None


def main(argv: list[str] | None = None) -> int:
    """CLI entry: list, check (exit 1 on drift), or fix."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="fail on any digest/tag mismatch (CHT-96)")
    mode.add_argument("--fix", action="store_true", help="rewrite digests to the registry's current values")
    mode.add_argument("--list", action="store_true", help="print the committed triples (default)")
    args = parser.parse_args(argv)

    if args.check or args.fix:
        if args.fix:
            for path in workspace_values_files():
                text = path.read_text()
                fixed = fix_text(text, registry_current)
                if fixed != text:
                    path.write_text(fixed)
                    print(f"updated {path.relative_to(WORKSPACE)}")
            return 0
        drift = check(extract_all(), registry_current)
        for d in drift:
            want = d.triple.digest or "(missing)"
            print(f"DRIFT {d.triple.source}: {d.triple.repository}:{d.triple.tag} {want} != {d.current}")
        if drift:
            print(f"{len(drift)} drifted pin(s): run `uv run python tools/images/chart_digests.py --fix`")
            return 1
        print("all chart image digests match the registry")
        return 0

    for triple in extract_all():
        digest = triple.digest or "(none)"
        print(f"{triple.source}\t{triple.repository}:{triple.tag}\t{digest}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI wrapper
    sys.exit(main())

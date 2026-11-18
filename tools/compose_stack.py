"""The standalone stack's compose files, read as compose reads them (DD-671, DD-688).

The stack is a tree: one umbrella (`docker/docker-compose.yaml`) that `include`s ten pieces, three of
which `extend` a service from an `infra/` slice. The chart-contract suite and the standalone bundler both
need that tree resolved, so the resolution lives here once: `compose_load` reads one file with compose's
custom tags understood, and `merge_stack` returns the merged service set for a tree rooted anywhere.

`merge_stack` takes the tree's root and spells every bind source root-relative, which is what lets a test
assert on the path the container reads. The repository stack roots at the workspace; a built bundle roots at
the bundle folder, so the same call compares a bundle's service set against the repository's (SBD-08). It is
not the bundler's copy list: a copy needs each source as the declaring file wrote it, because compose rebases
a relative path from that file's own folder. `compose_files` returns the files in the tree, so a caller can
walk each file with its own folder.

The loader knows the clauses the stack actually uses: services and volumes merged by name; for `extends` a
deep merge of the fragment over the base, where `!reset` deletes a key and `!override` replaces it whole
(both measured on compose v5.7.1), `environment`/`depends_on` maps merge by key, and a `volumes` entry
replaces the base's at the same mount target (compose keeps the last entry per target). A name used twice
outside an extends is an error here, where compose only warns.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

#: The repository's standalone stack: the umbrella and the folder its pieces read relative paths from.
WORKSPACE = Path(__file__).resolve().parents[1]
STACK = WORKSPACE / "docker"
UMBRELLA = STACK / "docker-compose.yaml"


class Tagged:
    """A compose `!reset` (delete) or `!override` (replace) marker over its value."""

    def __init__(self, kind: str, value: Any) -> None:  # noqa: ANN401 - a YAML node's value
        self.kind = kind
        self.value = value


class _ComposeLoader(yaml.SafeLoader):
    """SafeLoader that reads compose's custom tags (DD-671).

    `!reset` as a delete marker, `!override` as a replace marker, everything else as
    SafeLoader does.
    """


def _tagged(kind: str) -> Any:  # noqa: ANN401 - returns a constructor, typed loosely by PyYAML
    def build(loader: _ComposeLoader, node: yaml.Node) -> Tagged:
        if isinstance(node, yaml.MappingNode):
            return Tagged(kind, loader.construct_mapping(node, deep=True))
        if isinstance(node, yaml.SequenceNode):
            return Tagged(kind, loader.construct_sequence(node, deep=True))
        assert isinstance(node, yaml.ScalarNode), f"!{kind} over {type(node)}"
        return Tagged(kind, loader.construct_scalar(node))

    return build


_ComposeLoader.add_constructor("!reset", _tagged("reset"))
_ComposeLoader.add_constructor("!override", _tagged("override"))


def _load(path: Path) -> dict[str, Any]:
    return yaml.load(path.read_text(), Loader=_ComposeLoader)  # noqa: S506 - _ComposeLoader extends SafeLoader


def _bind_target(item: str) -> str:
    """The mount target of a short-syntax volume entry (the part after the first colon)."""
    return item.split(":")[1] if ":" in item else item


def _rebase_volume(item: Any, base_dir: Path, root: Path) -> Any:  # noqa: ANN401 - a YAML scalar or mapping entry
    """A short-syntax volume whose bind source is relative, spelled root-relative.

    A named volume (``data:/target``) and an environment-mapped path (``${V}:/target``)
    pass through; a ``./`` or ``../`` source is read against the folder of the file that
    wrote the entry.
    """
    if not isinstance(item, str) or ":" not in item:
        return item
    head, *rest = item.split(":")
    if head != "." and not head.startswith(("./", "../")):
        return item
    source = (base_dir / head).resolve().relative_to(root)
    return ":".join([str(source), *rest])


def _merge_service(
    base: dict[str, Any], base_dir: Path, override: dict[str, Any], override_dir: Path, root: Path
) -> dict[str, Any]:
    """Compose's extends merge: the override deep-merged over the base, tags honoured.

    Each side's relative bind sources are spelled root-relative against its own folder
    first, so the merged service carries the paths the container reads.
    """
    merged = dict(base)
    if isinstance(merged.get("volumes"), list):
        merged["volumes"] = [_rebase_volume(item, base_dir, root) for item in merged["volumes"]]
    override = dict(override)
    if isinstance(override.get("volumes"), list) and not isinstance(override["volumes"], Tagged):
        override["volumes"] = [_rebase_volume(item, override_dir, root) for item in override["volumes"]]
    for key, raw in override.items():
        if isinstance(raw, Tagged):
            if raw.kind == "reset":
                merged.pop(key, None)
                continue
            value: Any = raw.value
            if key == "volumes" and isinstance(value, list):
                value = [_rebase_volume(item, override_dir, root) for item in value]
            merged[key] = value
            continue
        lower = merged.get(key)
        if key == "volumes" and isinstance(raw, list) and isinstance(lower, list):
            targets = {_bind_target(item) for item in raw}
            kept = [item for item in lower if _bind_target(item) not in targets]
            merged[key] = kept + list(raw)
        elif isinstance(raw, dict) and isinstance(lower, dict) and key != "extends":
            merged[key] = {**lower, **raw}
        else:
            merged[key] = raw
    return merged


def compose_load(path: Path) -> dict[str, Any]:
    """A compose file read with the stack's tags understood (DD-671).

    A suite asserting on a fragment as written uses this, not ``yaml.safe_load``, which
    refuses ``!reset``/``!override``.
    """
    return _load(path)


def compose_files(umbrella: Path) -> list[Path]:
    """Every compose file the umbrella reaches, umbrella first, each path resolved (DD-688).

    The `include` list plus every base file an `extends` names, transitively. A bundler copies these and
    needs each one's own folder, because compose reads a relative path from the folder of the file that
    wrote it.
    """
    found: list[Path] = []

    def walk(path: Path) -> None:
        if path in found:
            return
        found.append(path)
        doc = _load(path)
        for entry in doc.get("include") or ():
            walk((path.parent / entry["path"]).resolve())
        for service in (doc.get("services") or {}).values():
            spec = service.get("extends") if isinstance(service, dict) else None
            if spec:
                walk((path.parent / spec["file"]).resolve())

    walk(umbrella.resolve())
    return found


def merge_stack(root: Path, umbrella: Path) -> dict[str, Any]:
    """The compose tree under `root` with its fragments merged and its `extends` resolved.

    `root` is the folder every relative path resolves inside: the workspace for the repository stack, the
    bundle folder for a built bundle. The umbrella sits under it (the repository's under `docker/`). Bind
    sources come back root-relative, so a bundle rooted at `root` carries the same service set as the
    repository's stack when the bundle closed correctly (SBD-08).
    """
    root = root.resolve()
    umbrella = umbrella.resolve()
    merged: dict[str, Any] = dict(_load(umbrella))
    for section in ("services", "volumes"):
        merged[section] = dict(merged.get(section) or {})
    for entry in merged.get("include") or ():
        fragment_path = (umbrella.parent / entry["path"]).resolve()
        fragment = _load(fragment_path)
        for name, value in (fragment.get("services") or {}).items():
            assert name not in merged["services"], f"{name}: {entry['path']} and the rest of the stack"
            service = dict(value)
            if "extends" in service:
                # The stack uses one level of extends (DD-671); a nested one grows the loader.
                assert "extends" not in service["extends"], service["extends"]
                spec = service.pop("extends")
                base_file = (fragment_path.parent / spec["file"]).resolve()
                base = _load(base_file)["services"][spec["service"]]
                assert "extends" not in base, f"{spec['file']}: the loader knows one level"
                service = _merge_service(base, base_file.parent, service, fragment_path.parent, root)
            merged["services"][name] = service
        for name, value in (fragment.get("volumes") or {}).items():
            assert name not in merged["volumes"], f"volume {name}: {entry['path']} and the rest of the stack"
            merged["volumes"][name] = value
    return merged


def standalone_compose() -> dict[str, Any]:
    """The repository stack's compose file with its fragments merged and its `extends` resolved."""
    return merge_stack(WORKSPACE, UMBRELLA)

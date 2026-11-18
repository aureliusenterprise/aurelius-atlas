"""Build the standalone bundle (17.3, DD-682..688).

The bundle is a pruned **mirror** of the repository (DD-688): the same folder names and file contents, with
only the pieces the stack reads and the assets they mount. No text rewrite except the bundle's own ``.env``,
which the spec requires (SBD-04, SBD-05, SBD-06). Because the shape is the repository's, every compose copy
is byte-identical to the tracked one and every path it names still points inside the bundle: each piece's
``../`` include, the infra bases' ``./certs``, the umbrella's ``stack.env`` (which answers the eight folder
knobs, so a relative value still resolves from the piece that reads it), the folders ``make-certs.sh``
creates, and the sample. Nothing rewrites a path; the mirror is already closed, which refines DD-683's
"shorter paths" wording to "keep the tree" (DD-688).

What travels: the ten compose pieces and the three infra base files they extend, the files the stack bind-
mounts (configs, scripts, the importer, the coredump agent, the themes, the realm import), the sample
(SBD-05), the certificate script and its manifest (SBD-12), the committed ``stack.env``, and the starter
``.env.example`` roster the bundle's ``.env`` is built from (SBD-04). What never travels: the repository's
secrets — any ``.env`` or ``.env.enc``, the ``certs/`` folders, ``secrets/``, and any key or certificate
(SBD-04). The copy list is derived from the stack's own compose files through tools/compose_stack.py: the
tool keeps no second list of services, mounts, or images (SBD-07), and a bind source it cannot copy fails the
build instead of emitting a bundle that starts broken (SBD-03).

Run as a script (``uv run python tools/standalone_bundle.py --version v1.2.3``) or through the root target
``nx standalone-bundle -- --version v1.2.3``. The release workflow (DD-685) passes the tag it published for,
so the six image variables name the images the same run pushed; the copied compose keeps its ``:local``
default and names none of the ``dhi.io`` images (DD-686).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compose_stack import UMBRELLA, WORKSPACE, compose_files, compose_load, merge_stack

#: The compose spelling of a release image (DD-686): ``${NAME_IMAGE:-ghcr.io/<org>/<project>:local}``. The
#: pieces name their images this way and no Aurelius image appears in plain text (SBD-11), so the set of
#: variables the bundle must answer is read from the stack rather than kept here (SBD-06, SBD-07).
IMAGE_VARIABLE = re.compile(r"^\$\{([A-Z][A-Z0-9_]*_IMAGE):-ghcr\.io/aureliusenterprise/([a-z0-9][a-z0-9-]*):local\}$")

#: The committed files a running stack reads that no service names directly: the stack-wide folder answers
#: (the umbrella's include ``env_file``), the roster the bundle ``.env`` is built from, and the certificate
#: script with its manifest. Listed because compose binds only what a service mounts.
EXTRA_FILES = ("docker/stack.env", "docker/.env.example", "docker/make-certs.sh", "docker/certs.txt")

#: The folder the sample import and the tenants one shot read, which the person must not have to set
#: (SBD-05). The bundle's ``.env`` names it; the value comes from the committed ``stack.env`` (DD-687), so the
#: mirror ships one answer for a folder and the tool keeps no second copy of the path (SBD-07).
SAMPLE_VARIABLE = "SAMPLE_DIR"

#: Never copied from the repository (SBD-04, DD-684): the repository's own env files, the generated
#: certificate folders, the developer secrets tree, and any key, certificate, or truststore file.
NEVER_COPIED = re.compile(r"(^|/)(\.env|\.env\.enc|secrets)(/|$)|(^|/)certs(/|$)|\.(pem|key|p12|crt)$")

#: What must not appear *inside* a built bundle (SBD-04). Narrower than NEVER_COPIED: the bundle is allowed
#: its own ``.env`` (the empty roster it ships), so only certificates, keys, truststores, and ``.env.enc`` are
#: forbidden in the tree.
NEVER_BUNDLED = re.compile(r"(^|/)certs(/|$)|\.(pem|key|p12|crt)$|\.env\.enc$")

#: A setting the person must fill; the bundle's ``.env`` names it and leaves it empty (SBD-04). The image
#: variables also end in a secret-looking suffix by chance, so they are checked first and excluded.
SECRET_SUFFIX = ("PASSWORD", "SECRET", "TOKEN", "KEY")


class BundleError(SystemExit):
    """The bundle cannot be built as specced; the message names the rule the tree would break."""


def _declared_files(umbrella: Path = UMBRELLA) -> list[Path]:
    """The compose files whose own services enter the stack: the umbrella plus everything it includes.

    An ``extends`` base file is not declared: its services reach the stack only through a piece that extends
    one of them, so the bundler records an extended base service's mounts from the piece (SBD-07). A base
    service no piece extends (an infra slice's metrics puller) is not part of the stack and copies no asset.
    """
    found: list[Path] = []

    def walk(path: Path) -> None:
        if path in found:
            return
        found.append(path)
        for entry in compose_load(path).get("include") or ():
            walk((path.parent / entry["path"]).resolve())

    walk(umbrella.resolve())
    return found


def _direct_dirs(umbrella: Path = UMBRELLA) -> dict[str, Path]:
    """Each directly declared service's name to the folder of the piece that declares it.

    A service defined without ``extends`` keeps its relative mounts as written, and compose reads a relative
    path from the folder of the file that wrote it, so a mount such as ``./one.conf`` resolves from its own
    piece. An ``extends`` service needs no entry: merge_stack returns its mounts already spelled root-relative
    (the base's rebased to the base's folder, the piece's to the piece's), so they resolve from the tree root.
    """
    out: dict[str, Path] = {}
    for file in _declared_files(umbrella):
        for name, service in (compose_load(file).get("services") or {}).items():
            if not service.get("extends"):
                out[name] = file.parent
    return out


def _bind_head(item: object) -> str:
    """The host path a short-syntax volume entry names (the part before the first colon), or "" for none."""
    return item.split(":")[0] if isinstance(item, str) and ":" in item else ""


def _literal_binds(root: Path, umbrella: Path) -> list[tuple[str, Path]]:
    """(service, resolved host path) for every literal bind the merged stack mounts under `root`.

    The set comes from merge_stack, so an ``extends`` piece's mount override is honoured the way compose
    applies it (the identity provider's own realm folder replaces the slice's, DD-676). A ``${VAR}`` mount names
    a folder the person or ``make-certs.sh`` fills, and a bare name (``data``) is a named volume the stack
    creates at start, so neither is a file to copy; a service that builds an image or reads a compose
    ``env_file``/``config``/``secret`` is a shape this bundler has not learned, so it fails rather than ship a
    bundle missing that input (SBD-03, SBD-06).
    """
    merged = merge_stack(root, umbrella)
    direct = _direct_dirs(umbrella)
    found: list[tuple[str, Path]] = []
    for name, service in merged["services"].items():
        if service.get("build"):
            raise BundleError(f"service {name} builds an image, which a published-image bundle cannot carry (SBD-06)")
        for key in ("env_file", "configs", "secrets"):
            if service.get(key):
                raise BundleError(f"service {name} uses {key}, which the bundler must learn to copy (SBD-03)")
        for item in service.get("volumes") or ():
            head = _bind_head(item)
            if head.startswith(("./", "../")) or head == ".":
                resolved = (direct[name] / head).resolve()  # a direct service's own relative mount
            elif "/" in head:
                resolved = (root / head).resolve()  # an extends service's mount, rebased root-relative
            else:
                continue  # a named volume the stack creates at start
            if resolved.name == "certs":
                continue  # certificate material make-certs.sh issues at that mirrored path (SBD-04, SBD-12)
            found.append((name, resolved))
    return found


def image_variables(root: Path = WORKSPACE, umbrella: Path = UMBRELLA) -> dict[str, str]:
    """The image variables the stack names, variable -> its project (SBD-06, SBD-07).

    Read from the merged compose, so the bundle answers exactly the variables the pieces ask for and the
    repository keeps no second list of image names (SBD-07). A stack that named an Aurelius image in plain
    text would be missing from here, and SBD-11 guards that shape in ``tests/test__standalone_images.py``.
    """
    out: dict[str, str] = {}
    for service in merge_stack(root, umbrella)["services"].values():
        match = IMAGE_VARIABLE.match(service.get("image") or "")
        if match:
            out[match.group(1)] = match.group(2)
    if not out:
        raise BundleError("the stack names no release image variable, so a bundle could not set one (SBD-06)")
    return dict(sorted(out.items()))


def _sample_sources(root: Path = WORKSPACE) -> list[Path]:
    """The sample's files, the folder the import and tenancy one shots read (SBD-05)."""
    sample = root / "data/atlas-sample"
    if not sample.is_dir():
        raise BundleError(f"the bundle needs {sample.relative_to(root)} (SBD-05), which the tree does not have")
    return [file for file in sorted(sample.rglob("*")) if file.is_file()]


def _copy_plan(root: Path = WORKSPACE, umbrella: Path = UMBRELLA) -> dict[Path, Path]:
    """Map every source the stack reads to its bundle-relative path, derived from the stack (SBD-07).

    A source the tree cannot hand over, or one that is a secret, fails the build: a path that walks above the
    root has no home in the bundle, and a missing or forbidden one would start a broken stack (SBD-03, SBD-04).
    """
    copies: dict[Path, Path] = {}

    def add(source: Path, where: str) -> None:
        try:
            relative = source.relative_to(root)
        except ValueError as error:
            raise BundleError(
                f"{where}: {source} lies outside {root}, so the bundle cannot hold it (SBD-03)"
            ) from error
        if NEVER_COPIED.search(str(relative)):
            raise BundleError(f"{where}: the stack names {relative}, which the bundle never ships (SBD-04)")
        if not source.exists():
            raise BundleError(f"{where}: the stack names {relative}, which the tree lacks (SBD-03)")
        copies[source] = relative

    for name, source in _literal_binds(root, umbrella):
        add(source, f"service {name}")
    for file in compose_files(umbrella):
        add(file, "compose file")
    for relative in EXTRA_FILES:
        add(root / relative, "bundle file")
    for file in _sample_sources(root):
        add(file, "sample")
    return copies


def _stack_answer(name: str) -> str:
    """The committed ``stack.env`` answer for one folder knob (DD-687).

    The mirror ships ``stack.env`` and the bundle's ``.env`` overrides it, so a value this tool writes must be
    the same answer, read from the file rather than repeated here (SBD-07).
    """
    for line in (WORKSPACE / "docker/stack.env").read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip() == name:
            return value.strip()
    raise BundleError(f"docker/stack.env holds no {name}, which the bundle must answer (SBD-05)")


def _bundle_env(version: str) -> str:
    """The bundle's ``.env``: the 17.2 roster with empty secrets, the sample, and the release images.

    The certificate knobs stay commented exactly as ``docker/.env.example`` writes them: ``make-certs.sh``
    issues the leaves at the mirrored paths the committed ``stack.env`` names, and an empty value here would
    beat that file (SBD-12). The sample is the one folder the person must not set (SBD-05), so the file names
    it with the stack's own answer. The image variables are the only other values (SBD-06); every secret is
    named and left empty for the person to fill (SBD-04).
    """
    roster = (WORKSPACE / "docker/.env.example").read_text().rstrip()
    images = "\n".join(
        f"{variable}=ghcr.io/aureliusenterprise/{project}:{version}" for variable, project in image_variables().items()
    )
    banner = "# --- Images: the release build this bundle was made for (DD-685, SBD-06) ----------------"
    note = "# The compose copies keep their :local default; these values override it at the operator's start."
    sample_banner = "# --- The sample, shipped inside this bundle (SBD-05, DD-684) -----------------------------------"
    sample_note = "# The folder the sample import and the tenants one shot read. Points inside the bundle."
    return (
        f"{roster}\n\n{sample_banner}\n{sample_note}\n{SAMPLE_VARIABLE}={_stack_answer(SAMPLE_VARIABLE)}\n\n"
        f"{banner}\n{note}\n{images}\n"
    )


def _bundle_readme() -> str:
    return """# Aurelius Atlas standalone bundle

One Docker Compose stack: the Aurelius Atlas webapp and the Atlas server behind one nginx entry, on the
stack's own Elasticsearch, with Keycloak as the identity provider and the telemetry stack behind the same
port. It needs only Docker Engine, `docker compose`, `bash`, and `openssl` (SBD-09) and pulls the release
images named in `.env`; it builds nothing.

## Start

1. Make the certificates (from this folder):

   ```bash
   bash docker/make-certs.sh
   ```

2. Open `docker/.env` and fill in the values left empty: the Elasticsearch passwords, the Keycloak bootstrap
   admin and database, the realm's client secrets, the scanner service users, the telemetry ingest token, and
   the truststore password. The sample imports itself on first start.

3. Start the stack (the first pull takes a few minutes):

   ```bash
   docker compose -f docker/docker-compose.yaml up -d
   ```

4. Open https://localhost:9000/ and sign in. Trust `docker/certs/ca.pem` to quiet the browser warning; add a
   person to the realm first (the realm holds no user). Read `docker/README.md` for the paths, the demo users,
   and running on a named host.

## Stop

```bash
docker compose -f docker/docker-compose.yaml down -v
```

The `-v` discards the demo data; without it the stack resumes where it left off.
"""


def build_bundle(output: Path, version: str) -> Path:
    """Build the bundle in `output`, return the tarball written beside it, and self-check it.

    The folder `output` is rebuilt from scratch, so a run never carries a stale file over (SBD-01). It lives
    under the git-ignored `dist/`, which keeps `git status` clean after the target runs (SBD-01).
    """
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for source, relative in _copy_plan().items():
        target = output / relative
        if source.is_dir():
            # A folder bind (the realm import, the themes, the dashboards): copy the tree, dropping any
            # secret a repository folder might hold so the mirror ships none (SBD-04).
            shutil.copytree(source, target, dirs_exist_ok=True, ignore=_ignore_secrets)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    (output / "docker/.env").write_text(_bundle_env(version))
    (output / "README.md").write_text(_bundle_readme())
    _self_check(output, version)
    return _tar(output, output)


def _ignore_secrets(_directory: str, names: list[str]) -> list[str]:
    """shutil.copytree ignore: drop secret names so a copied folder carries none (SBD-04)."""
    return [name for name in names if NEVER_BUNDLED.search(name)]


def _self_check(output: Path, version: str) -> None:
    """Assert the built bundle is secret-free, closed, and names the release images (SBD-03, SBD-04, SBD-06).

    The resolved ``compose config`` checks (no ``:local`` after interpolation, service-set equality) need
    the person's secrets filled, so they run in the suite (SBD-08); the bundler checks what it can decide.
    """
    _check_no_secret_files(output)
    _check_bundle_env(output, version)
    _check_closed(output)


def _check_no_secret_files(output: Path) -> None:
    """No certificate, key, truststore, or ``.env.enc`` sits anywhere in the bundle (SBD-04)."""
    for path in output.rglob("*"):
        relative = str(path.relative_to(output))
        if NEVER_BUNDLED.search(relative):
            raise BundleError(f"the bundle carries {relative}, which no bundle holds (SBD-04)")


def _check_bundle_env(output: Path, version: str) -> None:
    """The bundle's ``.env`` leaves every secret empty and sets every image to the release tag (SBD-04, SBD-06)."""
    env = (output / "docker/.env").read_text()
    for line in env.splitlines():
        if line.lstrip().startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if name.endswith(SECRET_SUFFIX) and not name.endswith("_IMAGE") and value.strip():
            raise BundleError(f"the bundle's .env fills {name}, which the person must set (SBD-04)")
    for variable, project in image_variables().items():
        if f"{variable}=ghcr.io/aureliusenterprise/{project}:{version}" not in env:
            raise BundleError(f"the bundle's .env does not set {variable} to the release tag (SBD-06)")


def _check_closed(output: Path) -> None:
    """Re-read the built tree and refuse any literal bind that leaves it or names a file it lacks (SBD-03)."""
    for name, source in _literal_binds(output, output / "docker/docker-compose.yaml"):
        if not source.is_relative_to(output):
            raise BundleError(f"bundle service {name} mounts {source}, which leaves the bundle (SBD-03)")
        if not source.exists():
            raise BundleError(f"bundle service {name} mounts {source}, which the bundle does not hold (SBD-03)")


def _tar(base: Path, out: Path) -> Path:
    tarball = out.parent / f"{out.name}.tar.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball, "w:gz") as archive:
        archive.add(base, arcname=out.name, filter=_deterministic)
    return tarball


def _deterministic(info: tarfile.TarInfo) -> tarfile.TarInfo:
    """Zero owner, group, and time so a rebuild of the same tree yields the same archive bytes."""
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mtime = 0
    return info


def main(argv: list[str] | None = None) -> int:
    """Build the bundle for the given release version and print the tarball path."""
    parser = argparse.ArgumentParser(description="Build the standalone bundle (17.3).")
    parser.add_argument("--version", required=True, help="The release tag the images carry (SBD-06).")
    parser.add_argument(
        "--output", default="dist/standalone-bundle", help="Folder to build in; a tarball goes beside it."
    )
    parser.add_argument("--keep", action="store_true", help="Keep the bundle folder; the tarball is the artefact.")
    args = parser.parse_args(argv)

    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?", args.version):
        parser.error(f"--version must look like v1.2.3 (got {args.version!r})")

    output = WORKSPACE / args.output
    tarball = build_bundle(output, args.version)
    if not args.keep:
        shutil.rmtree(output)
    print(f"bundle: {tarball.relative_to(WORKSPACE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

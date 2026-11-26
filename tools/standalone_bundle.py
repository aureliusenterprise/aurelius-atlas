"""Build the standalone release bundle (17.3, DD-682..690).

The bundle ships ONE compose file: the resolved view of the repository's standalone stack, produced by
``docker compose config --no-interpolate`` on the umbrella (DD-689). Compose itself resolves the ``include``
tree, the ``extends`` chains, and the shared anchors, so the tool carries no compose semantics of its own:
it merges no fragments, follows no includes, and applies no override rules (SBD-07). The flat file keeps every
``${VAR}`` the pieces wrote, so every setting stays a setting the operator can change in one place.

Two things the raw ``config`` output cannot ship as-is, and the tool fixes mechanically (DD-690):

- Compose anchors every host path to the folder of the file that wrote it, so baked bind sources come back as
  absolute paths into THIS checkout. The tool rewrites each to a path relative to the bundle's ``docker/``
  folder (where the flat file and the operator's ``.env`` live) and copies the file or folder to the mirrored
  place inside the bundle (SBD-03).
- With ``--no-interpolate`` compose cannot tell a guarded host folder (``${VAR:?...}``) from a named volume,
  so it types those mounts ``volume``; an operator who fills ``.env`` then meets "refers to undefined volume".
  The tool types them ``bind``. The folder each guard names comes from the committed ``stack.env`` (DD-687)
  read from the piece that wrote the guard, rebased to a bundle-relative value the tool writes into the
  bundle's ``.env``, so the knobs stay knobs and no value names a machine (SBD-05, SBD-12).

What travels: the flat compose file, every file or folder the flat file mounts, the sample (SBD-05), the
scripts folder a person runs by hand with its certificate manifest (17.2, SPC-11), and the starter
``.env.example`` roster. What never travels: the repository's secrets — any ``.env``/``.env.enc``, the
``certs/`` folders, ``secrets/``, and any key or certificate (SBD-04). A certificate folder is mounted but not
copied: ``docker/bin/make-certs.sh`` fills it inside the bundle (SBD-09). The tool writes the bundle's own
``.env`` and ``README.md``. A bind it cannot copy, or a shape it has not learned, fails the build rather than
ship a bundle that starts broken (SBD-03).

Run as a script (``uv run python tools/standalone_bundle.py --version v1.2.3``) or through the root target
``nx standalone-bundle -- --version v1.2.3``. Producing the flat file needs the ``docker compose`` CLI; that
run is daemon-free (DD-689). The release workflow passes the tag it published for, so the image variables
name the images the same run pushed (DD-685).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compose_cli import UMBRELLA, WORKSPACE, ComposeError, compose_config, load_piece, minimal_env


def _piece_files(umbrella: Path = UMBRELLA) -> list[Path]:
    """Every compose file the umbrella reaches: the `include` list and every `extends` base, transitively.

    The folder of each file is what compose anchors a relative path to, so the folder answers below read
    each guard's value from the piece that wrote it (SBD-12). The walk needs no merge: `load_piece` reads
    one file with compose's tags as identity (DD-693).
    """
    found: list[Path] = []

    def walk(path: Path) -> None:
        if path in found:
            return
        found.append(path)
        document = load_piece(path)
        for entry in document.get("include") or ():
            walk((path.parent / entry["path"]).resolve())
        for service in (document.get("services") or {}).values():
            spec = service.get("extends") if isinstance(service, dict) else None
            if spec:
                walk((path.parent / spec["file"]).resolve())

    walk(umbrella.resolve())
    return found


#: The folder inside the bundle that holds the flat compose file and the operator's ``.env``. Compose reads a
#: relative bind source from the folder of the compose file, so this is the anchor every path rebases to.
BUNDLE_COMPOSE_DIR = "docker"

#: The compose spelling of a release image: ``${NAME_IMAGE:-ghcr.io/<org>/<project>:local}``. The set of
#: variables the bundle answers is read from the flat file, never kept here (SBD-06, SBD-07).
IMAGE_VARIABLE = re.compile(r"^\$\{([A-Z][A-Z0-9_]*_IMAGE):-ghcr\.io/aureliusenterprise/([a-z0-9][a-z0-9-]*):local\}$")

#: A required folder guard ``${VAR:?message}``. Compose types these ``volume`` in ``--no-interpolate`` mode,
#: so the tool types them ``bind`` and answers them in the bundle's ``.env`` (DD-690).
GUARDED_VARIABLE = re.compile(r"^\$\{([A-Z][A-Z0-9_]*):\?[^}]*\}$")

#: The committed files a running stack reads that no service mounts: the roster the bundle ``.env`` is built
#: from, the scripts folder a person runs by hand (SPC-11, DD-699), and the certificate manifest (17.2,
#: SBD-09). The whole scripts folder ships, so a bundle holds every script its own README names.
EXTRA_FILES = ("docker/.env.example", "docker/bin", "docker/certs.txt")

#: Never copied from the repository (SBD-04, DD-684): the repository's own env files, the generated certificate
#: folders, the developer secrets tree, and any key, certificate, or truststore file.
NEVER_COPIED = re.compile(r"(^|/)(\.env|\.env\.enc|secrets)(/|$)|(^|/)certs(/|$)|\.(pem|key|p12|crt)$")

#: What must not appear *inside* a built bundle (SBD-04). Narrower than NEVER_COPIED: the bundle ships its own
#: ``.env`` (the empty roster), so only certificates, keys, truststores, and ``.env.enc`` are forbidden.
NEVER_BUNDLED = re.compile(r"(^|/)certs(/|$)|\.(pem|key|p12|crt)$|\.env\.enc$")

#: A setting the operator must fill; the bundle's ``.env`` names it and leaves it empty (SBD-04). The image
#: variables end in a secret-looking suffix by chance, so they are checked first and excluded.
SECRET_SUFFIX = ("PASSWORD", "SECRET", "TOKEN", "KEY")

#: A throwaway project name for the daemon-free ``config`` runs, so a check never touches the stack's project.
SCRATCH_PROJECT = "aurelius-atlas-bundle-build"


class BundleError(SystemExit):
    """The bundle cannot be built as specced; the message names the rule the tree would break."""


def _compose_document(text: str) -> dict:
    """Parse a resolved compose document into plain Python (the CLI's output is plain YAML)."""
    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict) or "services" not in loaded:
        raise BundleError("the resolved compose document has no services (DD-689)")
    return loaded


def _run_compose_config(*, interpolate: bool) -> str:
    """Run ``docker compose config`` on the repository umbrella and return the document text.

    The CLI resolves ``config`` without a daemon (DD-689), with no env file and the minimal environment
    ``compose_cli`` gives every run here, so the flat file depends on the tracked tree alone (SBD-01,
    DD-692). ``interpolate=False`` keeps every ``${VAR}`` the pieces wrote. No ``-p``: the document keeps
    the project name the umbrella declares, because a bundler's scratch name must not travel in the
    shipped file.
    """
    try:
        return compose_config(interpolate=interpolate)
    except ComposeError as error:
        raise BundleError(f"{error} (DD-689)") from error


def _guarded_folder_names(flat: dict) -> set[str]:
    """The ``${VAR:?...}`` guards the flat file mounts as host paths (the cert and sample folder knobs).

    A secret guard names a value in ``environment``, never a mount source, so every guard in a volume source
    is a folder the tool answers (SBD-12).
    """
    return {
        match.group(1)
        for service in flat.get("services", {}).values()
        for entry in service.get("volumes") or ()
        if isinstance(entry, dict) and (match := GUARDED_VARIABLE.match(str(entry.get("source"))))
    }


def _stack_env_answers() -> dict[str, str]:
    """The committed ``docker/stack.env`` answers (DD-687): folder knob -> the relative folder its piece reads."""
    answers: dict[str, str] = {}
    for line in (WORKSPACE / "docker/stack.env").read_text().splitlines():
        if line.lstrip().startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        answers[name.strip()] = value.strip()
    return answers


def _folder_answers(flat: dict) -> dict[str, str]:
    """Folder knob -> a bundle-relative folder, read from the committed ``stack.env`` (DD-687, SBD-05, SBD-12).

    ``stack.env`` is the repository's own answer for every folder knob, with each value relative to the compose
    piece that reads it. The tool finds the piece that names each guard, resolves that value from the piece's
    own folder, and rebases it to the bundle's ``docker/`` folder. This keeps every folder derived from the
    stack — no second list of cert or sample paths, and no second ``config`` run (SBD-07).
    """
    stack = _stack_env_answers()
    pieces = [(path, path.read_text()) for path in _piece_files(UMBRELLA)]
    answers: dict[str, str] = {}
    for guard in sorted(_guarded_folder_names(flat)):
        if guard not in stack:
            raise BundleError(f"the stack guards {guard} but docker/stack.env holds no answer for it (SBD-12)")
        folders = [path.parent for path, text in pieces if f"${{{guard}:" in text]
        if not folders:
            raise BundleError(f"no compose piece names {guard}, so its folder cannot be anchored (SBD-12)")
        answers[guard] = _rebase(str((folders[0] / stack[guard]).resolve()))[0]
    return answers


def _rebase(raw: str) -> tuple[str, Path]:
    """Turn one host path from the resolved document into a bundle-relative path and the repository file.

    Returns (path relative to the bundle's ``docker/`` folder, repository source). A path outside the checkout
    has no home in the bundle, which fails the build instead of emitting an open bundle (SBD-03).
    """
    absolute = Path(raw)
    if not absolute.is_absolute():
        absolute = (WORKSPACE / BUNDLE_COMPOSE_DIR / raw).resolve()
    try:
        repo_relative = absolute.relative_to(WORKSPACE)
    except ValueError as error:
        raise BundleError(f"{raw} lies outside {WORKSPACE}, so the bundle cannot hold it (SBD-03)") from error
    return os.path.relpath(repo_relative, BUNDLE_COMPOSE_DIR), absolute


def _flatten_services(flat: dict) -> list[Path]:
    """Rewrite every host mount in the flat document in place and return the sources to copy.

    A named volume is left for the stack to create at start. Every baked host path becomes bundle-relative and
    enters the copy list. A guarded folder keeps its ``${VAR:?...}`` knob and gains ``type: bind`` so the
    operator's filled ``.env`` does not meet "undefined volume" (DD-690); its material does not travel through
    the copy list, because a certificate folder is filled by ``make-certs.sh`` (SBD-09) and the sample travels
    as the explicit ``data/atlas-sample`` copy (SBD-05). Any other shape the tool has not learned fails the
    build (SBD-03).
    """
    copies: list[Path] = []
    for name, service in flat.get("services", {}).items():
        if service.get("build"):
            raise BundleError(f"service {name} builds an image, which a published-image bundle cannot carry (SBD-06)")
        for entry in service.get("volumes") or ():
            if not isinstance(entry, dict) or not isinstance(entry.get("source"), str):
                raise BundleError(f"service {name} has a volume entry with no string source (DD-689)")
            source = entry["source"]
            guard = GUARDED_VARIABLE.match(source)
            if entry.get("type") == "volume" and not guard and "${" not in source:
                continue  # a named volume the stack creates at start
            if guard:
                entry["type"] = "bind"
                entry.setdefault("bind", {})
                continue  # the bundle's .env answers the knob; its material is filled or copied elsewhere
            bundle_relative, repo_source = _rebase(source)
            entry["source"] = bundle_relative
            repo_path = repo_source.relative_to(WORKSPACE).as_posix()
            if repo_path == "certs" or repo_path.endswith("/certs"):
                continue  # make-certs.sh fills the folder in place (SBD-04, SBD-09)
            if NEVER_COPIED.search(repo_path):
                raise BundleError(f"service {name} mounts {repo_path}, which the bundle never ships (SBD-04)")
            copies.append(repo_source)
    return copies


def image_variables(document_text: str) -> dict[str, str]:
    """The image variables the flat file names, variable -> its project (SBD-06, SBD-07).

    Read from the resolved document, so the bundle answers exactly the variables the stack asks for and the
    repository keeps no second list of image names.
    """
    out: dict[str, str] = {}
    for service in _compose_document(document_text).get("services", {}).values():
        match = IMAGE_VARIABLE.match(service.get("image") or "")
        if match:
            out[match.group(1)] = match.group(2)
    if not out:
        raise BundleError("the stack names no release image variable, so a bundle could not set one (SBD-06)")
    return dict(sorted(out.items()))


def _bundle_env(document_text: str, answers: dict[str, str], version: str) -> str:
    """The bundle's ``.env``: the 17.2 roster, the bundle-relative folders, and the release images.

    The folder section answers every guarded folder with the stack's own answer rebased into the bundle, so
    the operator sets no folder to start (SBD-05, SBD-12) and can still repoint one value (DD-687). Every
    secret is named by the roster and left empty for the operator to fill (SBD-04); the image variables carry
    the release tag (SBD-06).
    """
    roster = (WORKSPACE / "docker/.env.example").read_text().rstrip()
    folder_banner = "# --- Folders inside this bundle, set by the bundler (SBD-05, SBD-12, DD-690) ----------------"
    folder_note = "# Relative to docker/ (this file's folder). Change a value to point at your own material."
    folders = "\n".join(f"{name}={folder}" for name, folder in sorted(answers.items()))
    images = "\n".join(
        f"{variable}=ghcr.io/aureliusenterprise/{project}:{version}"
        for variable, project in image_variables(document_text).items()
    )
    image_banner = "# --- Images: the release build this bundle was made for (DD-685, SBD-06) ----------------"
    image_note = "# The compose keeps its :local default; these values override it at the operator's start."
    return f"{roster}\n\n{folder_banner}\n{folder_note}\n{folders}\n\n{image_banner}\n{image_note}\n{images}\n"


def _bundle_readme() -> str:
    return """# Aurelius Atlas standalone bundle

One Docker Compose stack: the Aurelius Atlas webapp and the Atlas server behind one nginx entry, on the
stack's own Elasticsearch, with Keycloak as the identity provider and the telemetry stack behind the same
port. It needs Docker Engine, a recent `docker compose` (v2.20 or newer), `bash`, and `openssl` (SBD-09),
and pulls the release images named in `docker/.env`; it builds nothing.

## Start

1. Make the certificates (from this folder):

   ```bash
   bash docker/bin/make-certs.sh
   ```

2. Open `docker/.env` and fill in the values left empty: the Elasticsearch passwords, the Keycloak bootstrap
   admin and database, the realm's client secrets, the scanner service users, and the telemetry ingest token.
   The step above already set the truststore password.

3. Start the stack (the first pull takes a few minutes):

   ```bash
   docker compose -f docker/docker-compose.yaml up -d
   ```

4. Open https://localhost:9000/ and sign in. Trust `docker/certs/ca.pem` to quiet the browser warning; add a
   person to the realm first (the realm holds no user).

## Stop

```bash
docker compose -f docker/docker-compose.yaml down -v
```

The `-v` discards the demo data; without it the stack resumes where it left off.

## The sample and the tenants

The always-on stack starts no import and provisions no tenant. Run either when you want it (from this
folder, with the stack up):

```bash
bash docker/bin/import-sample.sh      # imports the sample from docker/.env's SAMPLE_DIR
bash docker/bin/provision-tenants.sh  # provisions the tenant demo and the operator user
```

To add a tenant of your own, with its people and a sample if you name one, run `docker/bin/tenant.sh`. Each
person it makes gets a temporary password, printed once, which they change at the first sign-in:

```bash
bash docker/bin/tenant.sh samples                                # the samples you can name
bash docker/bin/tenant.sh add acme --sample small --users all    # acme, its three users, the small sample
```

## About these files

`docker/docker-compose.yaml` is the stack resolved into one file, so a setting is changed in one place. The
folder paths in `docker/.env` and in the compose file are relative to this bundle and run from any folder on
any machine. `docker/bin/` holds the scripts you run by hand: the certificate script above, the three here, and
`docker/bin/set-host.sh` for a browser host other than `localhost` (it asks you to clear the data first).
"""


#: The bundle-relative home of the webapp's browser config — the file the
#: compose mounts at the SPA's `/config.json` (SPC-02, DD-694). The bundler
#: stamps the docs version folder into it (SHC-03, DD-886).
WEBAPP_CONFIG = "apps/aurelius-atlas-webapp/docker/config.json"


def _stamp_docs_ref(output: Path, version: str) -> None:
    """Point the bundle's Documentation link at the docs of the release it ships (SHC-03, DD-886).

    The repository's own ``config.json`` carries no ``docsRef``, which is the
    trunk; a bundle is one release, so the tool writes the release tag in. The
    key is the whole write — the file's own values (hosts, realm, client) stay
    as committed. A release tag is also a docs folder name because the docs
    publish one per tag (DD-886), the same tag the image variables carry
    (SBD-06).
    """
    path = output / WEBAPP_CONFIG
    if not path.is_file():
        raise BundleError(f"the bundle holds no {WEBAPP_CONFIG}, so its docs link cannot be stamped (SHC-03)")
    config = json.loads(path.read_text())
    config["docsRef"] = version
    path.write_text(json.dumps(config, indent=4) + "\n")


def build_bundle(output: Path, version: str) -> Path:
    """Build the bundle in `output`, return the tarball written beside it, and self-check it.

    The folder `output` is rebuilt from scratch, so a run never carries a stale file over (SBD-01). It lives
    under the git-ignored `dist/`, which keeps `git status` clean after the target runs (SBD-01).
    """
    flat_text = _run_compose_config(interpolate=False)
    flat = _compose_document(flat_text)
    answers = _folder_answers(flat)
    assets = _flatten_services(flat)

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    sample = WORKSPACE / "data/atlas-sample"
    if not sample.is_dir():
        raise BundleError(f"the bundle needs {sample} (SBD-05), which the tree does not have")
    for source in _deduped([*(WORKSPACE / relative for relative in EXTRA_FILES), *assets, *sorted(sample.rglob("*"))]):
        _copy_asset(output, source)
    (output / BUNDLE_COMPOSE_DIR / "docker-compose.yaml").write_text(yaml.safe_dump(flat, sort_keys=False, width=120))
    (output / BUNDLE_COMPOSE_DIR / ".env").write_text(_bundle_env(flat_text, answers, version))
    (output / "README.md").write_text(_bundle_readme())
    _stamp_docs_ref(output, version)
    _self_check(output, version)
    return _tar(output, output)


def _deduped(sources: list[Path]) -> list[Path]:
    """The sources once each, deepest last, so a folder is not copied under itself (a folder bind and a file bind)."""
    out: list[Path] = []
    seen: set[Path] = set()
    for source in sorted(sources, key=lambda path: len(path.parts)):
        if source in seen or any(source != parent and parent in seen for parent in source.parents):
            continue
        seen.add(source)
        out.append(source)
    return out


def _copy_asset(output: Path, source: Path) -> None:
    """Copy one repository file or folder to its mirrored bundle path, dropping any secret inside it (SBD-04)."""
    relative = source.relative_to(WORKSPACE)
    if NEVER_COPIED.search(str(relative)):
        raise BundleError(f"the bundle names {relative}, which it never ships (SBD-04)")
    target = output / relative
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True, ignore=_ignore_secrets)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _ignore_secrets(_directory: str, names: list[str]) -> list[str]:
    """shutil.copytree ignore: drop secret names so a copied folder carries none (SBD-04)."""
    return [name for name in names if NEVER_BUNDLED.search(name)]


def _self_check(output: Path, version: str) -> None:
    """Assert the bundle is secret-free, holds no host path, and resolves to release images (SBD-03..SBD-08).

    The resolved ``compose config`` check fills a throwaway roster (every empty secret gets a value, exactly
    as the operator's start will) and runs the same daemon-free resolution a start performs. It catches the
    DD-690 volume/bind mistake, a leaked ``:local``, and a path that escaped the bundle (SBD-08).
    """
    _check_no_secret_files(output)
    _check_no_host_paths(output)
    _check_closed(output)
    _resolves_release(output, version)


def _check_no_secret_files(output: Path) -> None:
    """No certificate, key, truststore, or ``.env.enc`` sits anywhere in the bundle (SBD-04)."""
    for path in output.rglob("*"):
        relative = str(path.relative_to(output))
        if NEVER_BUNDLED.search(relative):
            raise BundleError(f"the bundle carries {relative}, which no bundle holds (SBD-04)")


def _check_no_host_paths(output: Path) -> None:
    """No shipped text names a path of the build machine: the flat file and .env hold relative paths (SBD-03)."""
    needle = str(WORKSPACE)
    candidates = [*output.rglob("*.yaml"), *output.rglob("*.yml"), *output.glob("**/.env"), output / "README.md"]
    offenders = [str(path.relative_to(output)) for path in candidates if needle in path.read_text(errors="ignore")]
    if offenders:
        raise BundleError(f"the bundle names the build folder in {offenders} (SBD-03)")


def _check_closed(output: Path) -> None:
    """Every host bind the flat file names exists inside the bundle, so a start finds its material (SBD-03).

    A guarded folder resolves through the bundle's own ``.env`` (DD-690). A certificate folder is exempt: the
    operator's ``make-certs.sh`` run creates it (SBD-09). Every other source must already sit in the tree.
    """
    flat = _compose_document((output / BUNDLE_COMPOSE_DIR / "docker-compose.yaml").read_text())
    answers = _env_lines(output / BUNDLE_COMPOSE_DIR / ".env")
    compose_dir = output / BUNDLE_COMPOSE_DIR
    for name, service in flat.get("services", {}).items():
        for entry in service.get("volumes") or ():
            if not isinstance(entry, dict) or entry.get("type") != "bind":
                continue
            source = entry.get("source")
            if not isinstance(source, str):
                continue
            guard = GUARDED_VARIABLE.match(source)
            raw = answers[guard.group(1)] if guard else source
            path = (compose_dir / raw).resolve()
            if not path.is_relative_to(output):
                raise BundleError(f"bundle service {name} mounts {raw}, which leaves the bundle (SBD-03)")
            if not path.exists() and path.name != "certs":
                raise BundleError(f"bundle service {name} mounts {raw}, which the bundle does not hold (SBD-03)")


def _resolves_release(output: Path, version: str) -> None:
    """Resolve the bundle with a filled roster: exit 0, no warning, no ``:local``, images at the release tag.

    The run gets a minimal environment on purpose (SBD-01): ``docker compose`` lets a shell variable override
    ``--env-file``, so a developer who happens to export ``SERVER_IMAGE`` for another task would otherwise
    resolve this check to their own tag instead of the bundle's. With the environment blanked, the only answers
    are the files the bundle ships, which is exactly what an operator's machine holds.
    """
    env = _env_lines(output / BUNDLE_COMPOSE_DIR / ".env")
    roster = output.parent / "resolve-roster.env"
    roster.write_text("\n".join(f"{name}={value or 'placeholder'}" for name, value in env.items()) + "\n")
    command = [
        "docker",
        "compose",
        "-p",
        SCRATCH_PROJECT,
        "-f",
        "docker/docker-compose.yaml",
        "--env-file",
        str(roster),
        "config",
    ]
    done = subprocess.run(command, capture_output=True, text=True, check=False, cwd=output, env=minimal_env())
    roster.unlink()
    if done.returncode != 0 or done.stderr.strip():
        raise BundleError(f"the bundle does not resolve cleanly: rc={done.returncode} {done.stderr.strip()} (SBD-08)")
    if ":local" in done.stdout:
        raise BundleError("the resolved bundle names a :local image (SBD-06)")
    flat_text = (output / BUNDLE_COMPOSE_DIR / "docker-compose.yaml").read_text()
    for project in image_variables(flat_text).values():
        if f"{project}:{version}" not in done.stdout:
            raise BundleError(f"the resolved bundle does not tag {project} with the release (SBD-06)")


def _env_lines(path: Path) -> dict[str, str]:
    """The assignments of one env file as a map, with comments and blanks dropped."""
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if line.lstrip().startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        out[name.strip()] = value.strip()
    return out


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

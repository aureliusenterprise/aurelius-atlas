"""The standalone release bundle (17.3, SBD-01..08, DD-682..690; 17.4, SPC-11, DD-699).

The bundle is ONE compose file: the repository stack resolved by ``docker compose config --no-interpolate``,
with every host path rebased into the bundle and every certificate and sample folder left as the guarded
variable the pieces chose (DD-689, DD-690). One test per rule id. ``docker compose`` is both the flattener
and the resolver, and it is daemon-free for both, so the suite builds a real bundle and checks it without a
daemon; without the CLI the suite skips rather than fake a flatten, exactly as the chart suite skips without
``helm``. The level 2 run of SBD-09 (a real daemon, the webapp through the proxy) is recorded in the pull
request rather than asserted here.

The bundle's own ``.env`` carries the roster of ``docker/.env.example`` with every secret left empty (SBD-04),
so a resolved ``config`` needs a filled roster on top of it. ``_filled_roster`` writes one from the names the
bundle's own file declares, which keeps this suite free of a second roster (SBD-07 applies to the suite too).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import WORKSPACE, standalone_compose

sys.path.insert(0, str(WORKSPACE / "tools"))

import standalone_bundle as bundler

#: The version these tests build for. Any release-shaped tag works; the tests assert it lands, not its value.
VERSION = "v9.9.9"

#: A throwaway project name for the in-bundle ``config`` runs, so a check never names the stack's project (SBD-10).
SCRATCH_PROJECT = "aurelius-atlas-bundle-check"


@pytest.fixture(scope="package", autouse=True)
def _require_compose_cli() -> None:
    """Every test here builds or resolves a real flat file, which needs the compose CLI (DD-689)."""
    if subprocess.run(["docker", "compose", "version"], capture_output=True, check=False).returncode != 0:
        pytest.skip("docker compose CLI not available (config --no-interpolate is the flattener this suite checks)")


@pytest.fixture(scope="package")
def bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One built bundle for the suite: built once, read by every rule (SBD-08 builds from the tree)."""
    output = tmp_path_factory.mktemp("bundle") / "standalone-bundle"
    bundler.build_bundle(output, VERSION)
    return output


@pytest.fixture(scope="package")
def flat_text(bundle: Path) -> str:
    """The bundle's one compose file, as shipped."""
    return (bundle / "docker/docker-compose.yaml").read_text()


@pytest.fixture(scope="package")
def flat(flat_text: str) -> dict[str, Any]:
    """The bundle's flat compose document, parsed."""
    loaded = yaml.safe_load(flat_text)
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture(scope="package")
def repo_stack() -> dict[str, Any]:
    """The repository stack as the conftest resolver flattens it (DD-682)."""
    return standalone_compose()


def _env_lines(path: Path) -> dict[str, str]:
    """The assignments of one env file as a map, with comments and blanks dropped."""
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if line.lstrip().startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        out[name.strip()] = value.strip()
    return out


def _filled_roster(bundle: Path) -> Path:
    """The bundle's own ``.env`` with the empty secrets filled: the file the person hands the stack (SBD-04).

    Filling only the empty names is exactly what the operator does at the start (SBD-09), so the resolved
    stack below is the one a start resolves, folders and images included.
    """
    env = _env_lines(bundle / "docker/.env")
    filled = {name: (value or "x") for name, value in env.items()}
    path = bundle.parent / "roster.env"
    path.write_text("\n".join(f"{name}={value}" for name, value in filled.items()) + "\n")
    return path


def _compose_config(root: Path, *, extra_env: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Resolve the bundle's flat file with ``docker compose config`` from inside ``root`` (SBD-08).

    The CLI is daemon-free for ``config``, which is why the interpolation checks run here. The whole process
    comes back, because one check reads the resolved document and another reads compose's warnings.
    """
    command = ["docker", "compose", "-p", SCRATCH_PROJECT, "-f", "docker/docker-compose.yaml"]
    if extra_env is not None:
        command += ["--env-file", str(extra_env)]
    command.append("config")
    # The shared minimal environment (compose_cli, DD-692), so a *_IMAGE a developer exports cannot bend a
    # resolved check (SBD-01): the answer must come from the files the bundle ships, as on the operator's machine.
    return subprocess.run(command, capture_output=True, text=True, check=False, cwd=root, env=bundler.minimal_env())


# --- SBD-01: the bundle is generated, never committed -------------------------------------------------------


@pytest.mark.covers(rules=["SBD-01"])
def test__the_target_writes_only_into_the_ignored_dist_folder() -> None:
    """The target's own default output lands under the git-ignored ``dist/``, so a build leaves ``git status``
    clean and no bundle file is ever a tracked file (SBD-01, DD-682).
    """  # noqa: D205 - one sentence
    result = subprocess.run(
        [sys.executable, "tools/standalone_bundle.py", "--version", VERSION, "--output", "dist/bundle-check"],
        capture_output=True,
        text=True,
        check=False,
        cwd=WORKSPACE,
    )
    assert result.returncode == 0, result.stderr
    assert (WORKSPACE / "dist/bundle-check.tar.gz").is_file()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=True,
        cwd=WORKSPACE,
    )
    assert "dist/" not in status.stdout, status.stdout


@pytest.mark.covers(rules=["SBD-01"])
def test__a_rebuild_replaces_the_tree_instead_of_adding_to_it(bundle: Path) -> None:
    """A second build of the same tree yields the same file set, so a stale file cannot ride along in a release
    artifact (SBD-01).
    """  # noqa: D205 - one sentence
    first = sorted(p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file())
    bundler.build_bundle(bundle, VERSION)
    second = sorted(p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file())
    assert first == second


# --- SBD-02: the stack travels as one flat, open document -----------------------------------------------------


@pytest.mark.covers(rules=["SBD-02"])
def test__the_flat_file_holds_every_service_of_the_repository_stack(
    flat: dict[str, Any], repo_stack: dict[str, Any]
) -> None:
    """Compose itself resolved the ``include`` tree and the ``extends`` chains, so the flat file holds the
    repository stack's service set, one copy of each named volume, and each service's own image (SBD-02, DD-689).
    """  # noqa: D205 - one sentence
    assert set(flat["services"]) == set(repo_stack["services"])
    for name, service in flat["services"].items():
        assert service.get("image") == repo_stack["services"][name].get("image"), name
    assert set(flat.get("volumes") or ()) == set(repo_stack.get("volumes") or ())


@pytest.mark.covers(rules=["SBD-02"])
def test__the_flat_file_is_one_resolved_document_with_open_settings(flat_text: str) -> None:
    """The shipped file is the resolved view: no ``include`` or ``extends`` is left to resolve, and every
    ``${VAR}`` the pieces wrote survives, so a setting is changed in one file (SBD-02, DD-689).
    """  # noqa: D205 - one sentence
    assert "include:" not in flat_text
    assert "extends:" not in flat_text
    assert "${" in flat_text


@pytest.mark.covers(rules=["SBD-02"])
def test__every_certificate_and_sample_folder_stays_a_variable(flat: dict[str, Any]) -> None:
    """The guarded folders travel as their ``${VAR:?...}`` knobs, not as paths baked on the build machine, so
    the operator answers them in ``.env`` and no value names a repository (SBD-02, SBD-12, DD-690).
    """  # noqa: D205 - one sentence
    folder_knobs = bundler._guarded_folder_names(flat)
    assert {"SERVER_CERTS_DIR", "GATEWAY_CERTS_DIR", "WEBAPP_CERTS_DIR", "EMBEDDER_CERTS_DIR"} <= folder_knobs
    assert "SAMPLE_DIR" in folder_knobs


@pytest.mark.covers(rules=["SBD-02"])
def test__the_flat_file_keeps_the_local_image_defaults(flat: dict[str, Any]) -> None:
    """Each service image keeps its ``${NAME_IMAGE:-...:local}`` spelling, so the bundle answers the variables
    instead of the file freezing a tag (SBD-02, SBD-06, DD-685).
    """  # noqa: D205 - one sentence
    images = [service.get("image") or "" for service in flat["services"].values()]
    aurelius = [image for image in images if "ghcr.io/aureliusenterprise/" in image]
    assert aurelius, "the stack names no Aurelius image, so this rule is vacuous"
    assert all(":local}" in image for image in aurelius)


# --- SBD-03: the bundle is closed -----------------------------------------------------------------------------


@pytest.mark.covers(rules=["SBD-03"])
def test__every_host_bind_of_the_flat_file_resolves_inside_the_bundle(bundle: Path, flat: dict[str, Any]) -> None:
    """The bundler's closure check passes on the built bundle: every bind, guarded or baked, resolves to
    material the bundle holds, with only the certificate folders left to ``make-certs.sh`` (SBD-03, DD-690).
    """  # noqa: D205 - one sentence
    binds = [
        entry
        for service in flat["services"].values()
        for entry in service.get("volumes") or ()
        if isinstance(entry, dict) and entry.get("type") == "bind"
    ]
    assert binds, "a stack with no bind to check makes this rule vacuous"
    bundler._check_closed(bundle)


@pytest.mark.covers(rules=["SBD-03"])
def test__no_shipped_text_names_the_build_folder(bundle: Path) -> None:
    """No compose file, ``.env``, or README in the bundle contains the checkout's path, so nothing ties the
    artifact to the machine that built it (SBD-03, DD-690).
    """  # noqa: D205 - one sentence
    bundler._check_no_host_paths(bundle)


@pytest.mark.covers(rules=["SBD-03"])
def test__a_bind_outside_the_tree_fails_the_build() -> None:
    """A service that mounts a host path the checkout does not contain fails the build instead of emitting an
    open bundle (SBD-03).
    """  # noqa: D205 - one sentence
    flat = {"services": {"one": {"volumes": [{"type": "bind", "source": "/etc/passwd", "target": "/in"}]}}}
    with pytest.raises(bundler.BundleError, match="SBD-03"):
        bundler._flatten_services(flat)


@pytest.mark.covers(rules=["SBD-03"])
def test__a_guard_the_stack_cannot_answer_fails_the_build() -> None:
    """A guarded folder the committed ``stack.env`` holds no answer for fails the build with the rule it breaks,
    rather than ship a knob the operator's ``.env`` could not answer (SBD-03, SBD-12, DD-687).
    """  # noqa: D205 - one sentence
    guarded = {"type": "volume", "source": "${SOME_UNANSWERED_DIR:?name it}", "target": "/dir"}
    flat = {"services": {"one": {"volumes": [guarded]}}}
    with pytest.raises(bundler.BundleError, match="SBD-12"):
        bundler._folder_answers(flat)


@pytest.mark.covers(rules=["SBD-03"])
def test__a_bind_that_leaves_or_lacks_material_fails_the_closure_check(tmp_path: Path) -> None:
    """The closure check fails a bundle whose bind walks out of it or names material the bundle never copied,
    which is what a real start would hit (SBD-03).
    """  # noqa: D205 - one sentence
    escape = tmp_path / "escape"
    (escape / "docker").mkdir(parents=True)
    (escape / "docker/docker-compose.yaml").write_text(
        "name: escape-check\nservices:\n  one:\n    image: example/one:1\n    volumes:\n"
        "      - type: bind\n        source: ../escape.txt\n        target: /in\n"
    )
    (escape / "docker/.env").write_text("")
    with pytest.raises(bundler.BundleError, match="SBD-03"):
        bundler._check_closed(escape)
    missing = tmp_path / "missing"
    (missing / "docker").mkdir(parents=True)
    (missing / "docker/docker-compose.yaml").write_text(
        "name: missing-check\nservices:\n  one:\n    image: example/one:1\n    volumes:\n"
        "      - type: bind\n        source: ./absent.conf\n        target: /in\n"
    )
    (missing / "docker/.env").write_text("")
    with pytest.raises(bundler.BundleError, match="SBD-03"):
        bundler._check_closed(missing)


@pytest.mark.covers(rules=["SBD-03"])
def test__a_service_that_builds_an_image_fails_the_build() -> None:
    """A published-image bundle cannot carry a build context, so a service that builds fails the build by name
    rather than drop the service (SBD-03, SBD-06).
    """  # noqa: D205 - one sentence
    with pytest.raises(bundler.BundleError, match="SBD-06"):
        bundler._flatten_services({"services": {"one": {"build": "./one"}}})


# --- SBD-04: no secret travels --------------------------------------------------------------------------------


@pytest.mark.covers(rules=["SBD-04"])
def test__the_bundle_holds_no_certificate_key_or_truststore(bundle: Path) -> None:
    """No ``certs`` folder, no private key, no certificate, no PKCS12 truststore, and no encrypted developer
    env sits anywhere in the tree (SBD-04, DD-684).
    """  # noqa: D205 - one sentence
    offenders = [
        p.relative_to(bundle).as_posix()
        for p in bundle.rglob("*")
        if bundler.NEVER_BUNDLED.search(str(p.relative_to(bundle)))
    ]
    assert offenders == []


@pytest.mark.covers(rules=["SBD-04"])
def test__the_bundles_one_env_names_every_setting_and_fills_no_secret(bundle: Path) -> None:
    """The bundle ships the 17.2 roster as its own ``.env``: every name the example declares is present and
    every secret-named value is empty, so the person fills secrets and nothing else (SBD-04).
    """  # noqa: D205 - one sentence
    env = _env_lines(bundle / "docker/.env")
    roster = _env_lines(WORKSPACE / "docker/.env.example")
    assert set(roster) <= set(env)
    filled = {
        name: value
        for name, value in env.items()
        if name.endswith(bundler.SECRET_SUFFIX) and not name.endswith("_IMAGE") and value
    }
    assert filled == {}


@pytest.mark.covers(rules=["SBD-04"])
def test__a_copied_folder_sheds_the_secrets_sitting_in_it(bundle: Path) -> None:
    """A repository folder the stack mounts may hold developer certificate material; the copy of that folder
    holds none, because the copy drops those names (SBD-04, DD-684).
    """  # noqa: D205 - one sentence
    shipped = {p.name for p in bundle.rglob("*")}
    assert "truststore.p12" not in shipped
    assert "ca.key" not in shipped


# --- SBD-05: the sample ships, named in the bundle's .env -----------------------------------------------------


@pytest.mark.covers(rules=["SBD-05"])
def test__the_sample_folder_travels_inside_the_bundle(bundle: Path) -> None:
    """Every file of ``data/atlas-sample`` sits at the same path inside the bundle, so the import reads the
    sample without the person naming a folder (SBD-05, DD-684).
    """  # noqa: D205 - one sentence

    def listed(root: Path) -> list[str]:
        return sorted(p.relative_to(root).as_posix() for p in (root / "data/atlas-sample").rglob("*") if p.is_file())

    repo = listed(WORKSPACE)
    shipped = listed(bundle)
    assert repo
    assert repo == shipped


@pytest.mark.covers(rules=["SBD-05"])
def test__the_bundles_env_names_the_sample_and_it_resolves_inside_the_bundle(bundle: Path) -> None:
    """The bundle's ``.env`` answers ``SAMPLE_DIR`` with a bundle-relative folder (SBD-05, DD-690) and the
    server's mount reads the mirrored sample inside the bundle.
    """  # noqa: D205 - one sentence
    env = _env_lines(bundle / "docker/.env")
    resolved = (bundle / "docker" / env["SAMPLE_DIR"]).resolve()
    assert resolved == (bundle / "data/atlas-sample").resolve()


@pytest.mark.covers(rules=["SBD-05"])
def test__the_person_can_point_the_sample_at_their_own_folder(bundle: Path) -> None:
    """The value is one plain assignment in the single ``.env`` file the person edits, so a personal folder
    replaces the shipped one with no other change (SBD-05, DD-687).
    """  # noqa: D205 - one sentence
    lines = [line for line in (bundle / "docker/.env").read_text().splitlines() if line.startswith("SAMPLE_DIR=")]
    assert len(lines) == 1


# --- SPC-11: the scripts folder travels -----------------------------------------------------------------------


@pytest.mark.covers(rules=["SPC-11"])
def test__the_bundle_holds_the_scripts_folder_whole(bundle: Path) -> None:
    """The bundle ships every file of ``docker/bin/``, executable as in the checkout, so a bundle holds the
    scripts its own README names (SPC-11, DD-699). The README's three commands are the bundle's own scripts.
    """  # noqa: D205 - one sentence
    shipped = sorted(p.name for p in (bundle / "docker/bin").iterdir() if p.is_file())
    repo = sorted(p.name for p in (WORKSPACE / "docker/bin").iterdir() if p.is_file())
    assert shipped == repo == ["import-sample.sh", "make-certs.sh", "provision-tenants.sh", "set-host.sh"]
    for name in shipped:
        assert os.access(bundle / "docker/bin" / name, os.X_OK), name
    readme = (bundle / "README.md").read_text()
    for name in shipped:
        assert f"docker/bin/{name}" in readme, name
    # The README starts with the certificate script at the shipped path, not the retired one (SPC-11).
    assert "bash docker/bin/make-certs.sh" in readme
    assert not (bundle / "docker/make-certs.sh").exists()


# --- SBD-06: the images name the release, never :local --------------------------------------------------------


@pytest.mark.covers(rules=["SBD-06"])
def test__a_bundle_built_without_a_version_fails(tmp_path: Path) -> None:
    """``--version`` is required and release-shaped: a build that cannot name the release images it points at
    fails instead of emitting ``:local`` references (SBD-06, DD-685).
    """  # noqa: D205 - one sentence
    with pytest.raises(SystemExit):
        bundler.main(["--output", str(tmp_path / "no-version")])
    with pytest.raises(SystemExit):
        bundler.main(["--version", "latest", "--output", str(tmp_path / "bad-version")])


@pytest.mark.covers(rules=["SBD-06"])
def test__the_bundles_env_sets_every_image_variable_to_the_release(bundle: Path, flat_text: str) -> None:
    """The variables carry the tag of the build that made this bundle, read from the flat file itself, while
    the compose keeps its ``:local`` default untouched (SBD-06, DD-685, DD-686).
    """  # noqa: D205 - one sentence
    env = _env_lines(bundle / "docker/.env")
    variables = bundler.image_variables(flat_text)
    assert variables, "the stack names no image variable, so this rule is vacuous"
    for variable, project in variables.items():
        assert env[variable] == f"ghcr.io/aureliusenterprise/{project}:{VERSION}", variable


@pytest.mark.covers(rules=["SBD-06"])
def test__the_resolved_stack_names_no_local_image(bundle: Path, flat_text: str) -> None:
    """Resolved with its own ``.env`` and a filled roster, the whole stack resolves with zero ``:local``
    references and every Aurelius image at the release tag (SBD-06, SBD-08).
    """  # noqa: D205 - one sentence
    done = _compose_config(bundle, extra_env=_filled_roster(bundle))
    assert done.returncode == 0, done.stderr
    assert ":local" not in done.stdout
    for project in bundler.image_variables(flat_text).values():
        assert f"{project}:{VERSION}" in done.stdout


# --- SBD-07: one implementation, reading the stack ------------------------------------------------------------


@pytest.mark.covers(rules=["SBD-07"])
def test__the_tool_keeps_no_second_list_of_services_mounts_or_images() -> None:
    """The bundler's source names no service, no mounted file, and no project image: compose resolves the
    stack and the tool reads what comes back, so a new piece needs no change here (SBD-07, DD-689).
    """  # noqa: D205 - one sentence
    source = (WORKSPACE / "tools/standalone_bundle.py").read_text()
    for name in standalone_compose()["services"]:
        assert f'"{name}"' not in source, f"the tool names the service {name}"
    for mounted in ("nginx.conf", "otel-collector.yaml", "coredump-noop.jar", "aurelius-atlas.json", "master.json"):
        assert mounted not in source, f"the tool names the mounted file {mounted}"


@pytest.mark.covers(rules=["SBD-07"])
def test__the_image_variables_come_from_the_compose_files(flat_text: str, repo_stack: dict[str, Any]) -> None:
    """Deriving the variables from the flat file yields exactly the set the repository's pieces spell in their
    image lines, so the bundle answers what the stack asks for and nothing else (SBD-07).
    """  # noqa: D205 - one sentence
    spelled = {
        match.group(1)
        for service in repo_stack["services"].values()
        if (match := bundler.IMAGE_VARIABLE.match(service.get("image") or ""))
    }
    assert set(bundler.image_variables(flat_text)) == spelled


# --- SBD-08: the checks the repository runs on every pull request ---------------------------------------------


@pytest.mark.covers(rules=["SBD-08"])
def test__the_bundlers_self_check_passes_on_the_built_bundle(bundle: Path) -> None:
    """The bundler's own gate (closed, secret-free, host-path-free, images tagged) passes on the bundle the
    suite builds from the tree, which is the check every pull request runs (SBD-08).
    """  # noqa: D205 - one sentence
    bundler._self_check(bundle, VERSION)


@pytest.mark.covers(rules=["SBD-08"])
def test__the_bundle_resolves_cleanly_with_its_own_one_env(bundle: Path) -> None:
    """``docker compose config`` resolves the bundle with only the files the bundle ships: exit 0 and no
    warning on stderr, which is the same resolution a start performs (SBD-08, SBD-09).
    """  # noqa: D205 - one sentence
    done = _compose_config(bundle, extra_env=_filled_roster(bundle))
    assert done.stderr == "", done.stderr
    assert done.returncode == 0, done.stderr


@pytest.mark.covers(rules=["SBD-08"])
def test__the_repository_stack_still_names_its_local_images(repo_stack: dict[str, Any], flat_text: str) -> None:
    """Building a bundle changes no repository compose file: the stack the e2e suites extend still resolves
    with its ``:local`` defaults, and its image variables are the set the bundle answers (SBD-08, SBD-10).
    """  # noqa: D205 - one sentence
    defaults = {
        match.group(1)
        for service in repo_stack["services"].values()
        if (match := bundler.IMAGE_VARIABLE.match(service.get("image") or ""))
    }
    assert defaults == set(bundler.image_variables(flat_text))


@pytest.mark.covers(rules=["SBD-08"])
def test__the_umbrella_still_holds_the_pieces_the_flat_file_flattens() -> None:
    """The repository umbrella keeps its ``include`` tree and its ``stack.env`` answers, so the flat file is a
    generated view and the e2e stacks keep extending the same pieces in place (SBD-08, SBD-10).
    """  # noqa: D205 - one sentence
    umbrella = (WORKSPACE / "docker/docker-compose.yaml").read_text()
    assert "include:" in umbrella
    assert "stack.env" in umbrella

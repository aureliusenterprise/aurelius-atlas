"""The standalone release bundle (17.3, SBD-01..08, DD-682..688).

One test per rule id, and no Docker daemon: the bundle is built from the working tree into a temporary
folder and checked as a tree (closed, secret-free, its own ``.env`` resolved free of ``:local``, and its
flattened service set equal to the repository stack's). ``docker compose config`` is the resolver used for
the interpolation checks because it is the same resolution a start performs and it needs no daemon; without
the CLI the interpolation tests skip rather than weaken, exactly as the chart suite skips without ``helm``.
The level 2 run of SBD-08 (a real daemon, the webapp through the proxy) is recorded in the pull request
rather than asserted here.

The bundle's own ``.env`` carries the roster of ``docker/.env.example`` with every secret left empty (SBD-04),
so a resolved ``config`` needs a filled roster on top of it. ``_filled_roster`` writes one from the names the
example file itself declares, which keeps this suite free of a second roster (SBD-07 applies to the suite too).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from conftest import WORKSPACE, compose_load, merge_stack, standalone_compose

sys.path.insert(0, str(WORKSPACE / "tools"))

import standalone_bundle as bundler

#: The version these tests build for. Any release-shaped tag works; the tests assert it lands, not its value.
VERSION = "v9.9.9"

#: One compose project name for the in-bundle ``config`` runs: a scratch name, so a resolved config never
#: touches the repository stack's project (SBD-10) and the daemon stays out of it entirely.
SCRATCH_PROJECT = "aurelius-atlas-bundle-check"


@pytest.fixture(scope="package")
def bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One built bundle for the suite: built once, read by every rule (SBD-08 builds from the tree)."""
    output = tmp_path_factory.mktemp("bundle") / "standalone-bundle"
    bundler.build_bundle(output, VERSION)
    return output


@pytest.fixture(scope="package")
def bundle_services(bundle: Path) -> dict[str, Any]:
    """The bundle's own flattened service set, read the way the repository stack's is read."""
    return merge_stack(bundle, bundle / "docker/docker-compose.yaml")["services"]


@pytest.fixture(scope="package")
def repo_services() -> dict[str, Any]:
    """The repository stack's flattened service set (the conftest resolver, DD-682)."""
    return standalone_compose()["services"]


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

    The bundle's ``.env`` names every setting and leaves every secret empty on purpose, and it carries the six
    image variables. Filling only the empty names is exactly what the operator does at the start (SBD-09), so
    the resolved stack below is the one a start resolves, images included.
    """
    env = _env_lines(bundle / "docker/.env")
    filled = {name: (value or "x") for name, value in env.items()}
    path = bundle.parent / "roster.env"
    path.write_text("\n".join(f"{name}={value}" for name, value in filled.items()) + "\n")
    return path


def _compose_config(root: Path, *, extra_env: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Resolve the stack with ``docker compose config`` from inside ``root``, with its own ``.env``.

    The CLI is daemon-free for ``config``, which is why SBD-08's interpolation checks run here. The finished
    process comes back whole, because one check reads the resolved YAML and another reads compose's warnings.
    """
    if subprocess.run(["docker", "compose", "version"], capture_output=True, check=False).returncode != 0:
        pytest.skip("docker compose CLI not available (config is the resolver these checks need)")
    command = ["docker", "compose", "-p", SCRATCH_PROJECT, "-f", "docker/docker-compose.yaml"]
    if extra_env is not None:
        command += ["--env-file", str(extra_env)]
    command.append("config")
    return subprocess.run(command, capture_output=True, text=True, check=False, cwd=root)


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


# --- SBD-02: the compose structure travels --------------------------------------------------------------------


@pytest.mark.covers(rules=["SBD-02"])
def test__the_bundle_holds_every_service_the_repository_stack_has(
    bundle_services: dict[str, Any], repo_services: dict[str, Any]
) -> None:
    """The umbrella, the pieces it includes, and the infra bases the three pieces extend all travel, so the
    bundle's flattened service set is the repository stack's and holds each service once (SBD-02, DD-683).
    """  # noqa: D205 - one sentence
    assert set(bundle_services) == set(repo_services)


@pytest.mark.covers(rules=["SBD-02"])
def test__each_service_definition_travels_unchanged(
    bundle_services: dict[str, Any], repo_services: dict[str, Any]
) -> None:
    """The copies are byte-identical: no definition moves, gains a default, or loses a mount on the way into
    the bundle, which is what keeps one source of truth (SBD-02, SBD-10, DD-688).
    """  # noqa: D205 - one sentence
    for name, service in bundle_services.items():
        assert service == repo_services[name], name


@pytest.mark.covers(rules=["SBD-02"])
def test__the_compose_copies_are_byte_identical_to_the_tracked_files(bundle: Path) -> None:
    """Every compose file in the bundle matches the repository's, including the infra bases (SBD-02)."""
    for file in bundler.compose_files(bundler.UMBRELLA):
        shipped = bundle / file.relative_to(WORKSPACE)
        assert shipped.read_bytes() == file.read_bytes(), file


# --- SBD-03: the bundle is closed -----------------------------------------------------------------------------


@pytest.mark.covers(rules=["SBD-03"])
def test__every_literal_bind_resolves_inside_the_bundle(bundle: Path) -> None:
    """Every relative host path the merged stack names points at a file the bundle holds: the config files,
    scripts, themes, realm import and folders the pieces mount (SBD-03).
    """  # noqa: D205 - one sentence
    binds = bundler._literal_binds(bundle, bundle / "docker/docker-compose.yaml")
    assert binds, "a stack with no bind to check makes this rule vacuous"
    for name, source in binds:
        assert source.is_relative_to(bundle), f"{name}: {source} leaves the bundle"
        assert source.exists(), f"{name}: {source} is missing from the bundle"


@pytest.mark.covers(rules=["SBD-03"])
def test__a_bind_the_tool_cannot_copy_fails_the_build(tmp_path: Path) -> None:
    """A piece that mounts a file above its own tree fails the build with the rule it breaks, instead of
    shipping a bundle that starts broken (SBD-03).
    """  # noqa: D205 - one sentence
    root = tmp_path / "tree"
    (root / "docker").mkdir(parents=True)
    (tmp_path / "escape.txt").write_text("above the tree\n")
    umbrella = root / "docker/docker-compose.yaml"
    umbrella.write_text(
        "name: escape-check\nservices:\n    one:\n        image: example/one:1\n        volumes:\n"
        "            - ../../escape.txt:/in/one:ro\n"
    )
    with pytest.raises(SystemExit) as raised:
        bundler._copy_plan(root, umbrella)
    assert "SBD-03" in str(raised.value)


@pytest.mark.covers(rules=["SBD-03"])
def test__a_bind_to_a_file_the_tree_lacks_fails_the_build(tmp_path: Path) -> None:
    """A piece that mounts a file the tree does not hold fails the build rather than copy nothing for it
    (SBD-03).
    """  # noqa: D205 - one sentence
    root = tmp_path / "tree"
    (root / "docker").mkdir(parents=True)
    umbrella = root / "docker/docker-compose.yaml"
    umbrella.write_text(
        "name: missing-check\nservices:\n    one:\n        image: example/one:1\n        volumes:\n"
        "            - ./absent.conf:/etc/one.conf:ro\n"
    )
    with pytest.raises(SystemExit) as raised:
        bundler._copy_plan(root, umbrella)
    assert "SBD-03" in str(raised.value)


@pytest.mark.covers(rules=["SBD-03"])
def test__a_service_that_builds_an_image_fails_the_build(tmp_path: Path) -> None:
    """A published-image bundle cannot carry a build context, so a service that builds fails the build by name
    rather than drop the service (SBD-03, SBD-06).
    """  # noqa: D205 - one sentence
    root = tmp_path / "tree"
    (root / "docker").mkdir(parents=True)
    (root / "docker/docker-compose.yaml").write_text("name: build-check\nservices:\n    one:\n        build: ./one\n")
    with pytest.raises(SystemExit) as raised:
        bundler._literal_binds(root, root / "docker/docker-compose.yaml")
    assert "SBD-06" in str(raised.value)


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
    """A repository folder the stack mounts may hold developer certificate material; the mirror of that folder
    holds none, because the copy drops those names (SBD-04).
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
    repo = sorted(
        p.relative_to(WORKSPACE).as_posix() for p in (WORKSPACE / "data/atlas-sample").rglob("*") if p.is_file()
    )
    shipped = sorted(p.relative_to(bundle).as_posix() for p in (bundle / "data/atlas-sample").rglob("*") if p.is_file())
    assert repo
    assert repo == shipped


@pytest.mark.covers(rules=["SBD-05"])
def test__the_bundles_env_names_the_sample_and_it_points_inside_the_bundle(bundle: Path) -> None:
    """The bundle's ``.env`` names ``SAMPLE_DIR`` (SBD-05) and the answer the server piece resolves from it
    lands on the mirrored sample folder inside the bundle.
    """  # noqa: D205 - one sentence
    env = _env_lines(bundle / "docker/.env")
    assert env[bundler.SAMPLE_VARIABLE] == bundler._stack_answer(bundler.SAMPLE_VARIABLE)
    resolved = (bundle / "apps/aurelius-atlas-server/docker" / env[bundler.SAMPLE_VARIABLE]).resolve()
    assert resolved == (bundle / "data/atlas-sample").resolve()


@pytest.mark.covers(rules=["SBD-05"])
def test__the_person_can_point_the_sample_at_their_own_folder(bundle: Path) -> None:
    """The value is a plain assignment in the one ``.env`` file the person edits, so a personal folder replaces
    the shipped one with no other change (SBD-05, DD-687).
    """  # noqa: D205 - one sentence
    env = (bundle / "docker/.env").read_text()
    lines = [line for line in env.splitlines() if line.startswith(f"{bundler.SAMPLE_VARIABLE}=")]
    assert len(lines) == 1, env


# --- SBD-06: the six images name the release, never :local ----------------------------------------------------


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
def test__the_bundles_env_sets_every_image_variable_to_the_release(bundle: Path) -> None:
    """The six variables carry the tag of the build that made this bundle, and the compose copies keep their
    ``:local`` default untouched (SBD-06, DD-685, DD-686).
    """  # noqa: D205 - one sentence
    env = _env_lines(bundle / "docker/.env")
    variables = bundler.image_variables()
    assert variables, "the stack names no image variable, so this rule is vacuous"
    for variable, project in variables.items():
        assert env[variable] == f"ghcr.io/aureliusenterprise/{project}:{VERSION}", variable
    for name, service in merge_stack(bundle, bundle / "docker/docker-compose.yaml")["services"].items():
        image = service.get("image") or ""
        if "ghcr.io/aureliusenterprise/" in image:
            assert ":local}" in image, f"{name}: the copy lost its default ({image})"


@pytest.mark.covers(rules=["SBD-06"])
def test__the_resolved_stack_names_no_local_image(bundle: Path) -> None:
    """Resolved with its own ``.env`` and a filled roster, the whole stack resolves with zero ``:local``
    references: nothing in it builds or pulls a local tag (SBD-06, SBD-08).
    """  # noqa: D205 - one sentence
    done = _compose_config(bundle, extra_env=_filled_roster(bundle))
    assert done.returncode == 0, done.stderr
    assert ":local" not in done.stdout
    for project in bundler.image_variables().values():
        assert f"{project}:{VERSION}" in done.stdout


# --- SBD-07: one implementation, reading the stack ------------------------------------------------------------


@pytest.mark.covers(rules=["SBD-07"])
def test__the_tool_keeps_no_second_list_of_services_mounts_or_images() -> None:
    """The bundler's source names no service, no mounted file, and no project image: it reads them from the
    stack's own compose files (SBD-07). The image variables and the copy plan come from the merge, so a new
    piece needs no change here.
    """  # noqa: D205 - one sentence
    source = (WORKSPACE / "tools/standalone_bundle.py").read_text()
    for name in standalone_compose()["services"]:
        assert f'"{name}"' not in source, f"the tool names the service {name}"
    for mounted in ("nginx.conf", "otel-collector.yaml", "coredump-noop.jar", "aurelius-atlas.json", "master.json"):
        assert mounted not in source, f"the tool names the mounted file {mounted}"


@pytest.mark.covers(rules=["SBD-07"])
def test__the_image_variables_come_from_the_compose_files(bundle: Path) -> None:
    """Deriving the variables from the merged stack yields the set the pieces actually ask for, and reading
    them from the bundle gives the same answer (SBD-07).
    """  # noqa: D205 - one sentence
    derived = bundler.image_variables()
    in_bundle = bundler.image_variables(bundle, bundle / "docker/docker-compose.yaml")
    assert derived == in_bundle
    spelled = {
        match.group(1)
        for service in standalone_compose()["services"].values()
        if (match := bundler.IMAGE_VARIABLE.match(service.get("image") or ""))
    }
    assert set(derived) == spelled


@pytest.mark.covers(rules=["SBD-07"])
def test__every_bundled_file_comes_from_the_copy_plan(bundle: Path) -> None:
    """Every file in the tree is either a plan entry, a file inside a folder the stack mounts, or one of the
    two files the tool writes itself (the README and the one ``.env``). Nothing is hand-copied outside the
    plan the compose files derive (SBD-07).
    """  # noqa: D205 - one sentence
    targets = {str(target) for target in bundler._copy_plan().values()}
    written = {"README.md", "docker/.env"}
    for path in bundle.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(bundle).as_posix()
        covered = relative in targets or any(relative.startswith(f"{target}/") for target in targets)
        assert covered or relative in written, f"{relative} sits in the bundle but in no plan entry"


# --- SBD-08: the checks the repository runs on every pull request ---------------------------------------------


@pytest.mark.covers(rules=["SBD-08"])
def test__the_bundlers_self_check_passes_on_the_built_bundle(bundle: Path) -> None:
    """The bundler's own offline gate (closed, secret-free, images tagged) passes on the bundle the suite
    builds from the tree, which is the check every pull request runs (SBD-08).
    """  # noqa: D205 - one sentence
    bundler._self_check(bundle, VERSION)


@pytest.mark.covers(rules=["SBD-08"])
def test__the_bundle_resolves_cleanly_with_its_own_one_env(bundle: Path) -> None:
    """``docker compose config`` resolves the bundle's umbrella with only the files the bundle ships: exit 0
    and no warning on stderr, which is the same resolution a start performs (SBD-08, SBD-09).
    """  # noqa: D205 - one sentence
    done = _compose_config(bundle, extra_env=_filled_roster(bundle))
    assert done.stderr == "", done.stderr
    assert done.returncode == 0, done.stderr


@pytest.mark.covers(rules=["SBD-08"])
def test__the_repository_stack_still_resolves_the_same_way(repo_services: dict[str, Any]) -> None:
    """Building a bundle changes no repository compose file: the stack the e2e suites extend still flattens to
    the same service set with its ``:local`` defaults intact (SBD-08, SBD-10).
    """  # noqa: D205 - one sentence
    assert repo_services, "the repository stack resolved to nothing"
    defaults = {
        match.group(1)
        for service in repo_services.values()
        if (match := bundler.IMAGE_VARIABLE.match(service.get("image") or ""))
    }
    assert defaults == set(bundler.image_variables())


@pytest.mark.covers(rules=["SBD-08"])
def test__the_umbrella_compose_still_carries_the_stack_comment() -> None:
    """The repository umbrella keeps naming the pieces it includes, so the bundle's mirror stays a copy and the
    e2e stacks keep extending the same pieces in place (SBD-08, SBD-10).
    """  # noqa: D205 - one sentence
    umbrella = compose_load(WORKSPACE / "docker/docker-compose.yaml")
    declared = {(WORKSPACE / "docker" / entry["path"]).resolve() for entry in umbrella["include"]}
    files = {file.resolve() for file in bundler.compose_files(bundler.UMBRELLA)}
    assert declared <= files

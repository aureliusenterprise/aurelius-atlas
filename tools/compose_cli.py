"""The `docker compose` CLI, called the way the repository's tools call it (DD-693).

The repository resolves its standalone stack by asking compose itself (DD-689): `config` needs no
daemon and it knows the language of the files — `include`, `extends`, and the `!reset`/`!override`
tags — so no Python code re-implements them. Two rules make every run here reproducible:

- The environment carries only what the Docker CLI needs to reach the daemon. Compose lets a shell
  variable beat an `--env-file`, so a developer's exported `SERVER_IMAGE` or `COMPOSE_PROFILES`
  would otherwise change what the command answers (DD-692).
- The env file is explicit: the caller passes one, or passes none, so the developer's own
  `docker/.env` never answers a variable silently.

Keep compose semantics out of this module. A caller that needs the document parses the text; a
caller that needs a shape normalises the document itself. This module only runs the command.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import yaml

#: The repository root, the folder whose tree the stack's relative paths read from.
WORKSPACE = Path(__file__).resolve().parents[1]

#: The standalone stack's folder and umbrella (ADR 065).
STACK = WORKSPACE / "docker"
UMBRELLA = STACK / "docker-compose.yaml"

#: The only environment variables a `docker compose` run of this repository may see: what the Docker
#: CLI needs to reach the daemon, and nothing the stack reads (DD-692).
COMPOSE_ENV_ALLOWLIST = (
    "PATH",
    "HOME",
    "USER",
    "LANG",
    "TMPDIR",
    "XDG_RUNTIME_DIR",
    "NODE_EXTRA_CA_CERTS",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "DOCKER_HOST",
    "DOCKER_CONFIG",
    "DOCKER_CONTEXT",
    "DOCKER_TLS_VERIFY",
    "DOCKER_CERT_PATH",
)


class ComposeError(RuntimeError):
    """`docker compose` failed; the message carries its stderr."""


class Tagged:
    """A compose `!reset` (delete) or `!override` (replace) marker over its value.

    A reader that walks the tree or asserts on one piece as written needs the marker as data; the
    merge the marker asks for is `config`'s job and reaches a caller through `compose_config`.
    """

    def __init__(self, kind: str, value: Any) -> None:  # noqa: ANN401 - a YAML node's value
        self.kind = kind
        self.value = value


class _TagLoader(yaml.SafeLoader):
    """SafeLoader that reads compose's `!reset`/`!override` as `Tagged` markers."""


def _tagged(kind: str) -> Any:  # noqa: ANN401 - returns a constructor; typed loosely by PyYAML
    def build(loader: _TagLoader, node: yaml.Node) -> Tagged:
        if isinstance(node, yaml.SequenceNode):
            return Tagged(kind, loader.construct_sequence(node, deep=True))
        if isinstance(node, yaml.MappingNode):
            return Tagged(kind, loader.construct_mapping(node, deep=True))
        assert isinstance(node, yaml.ScalarNode), f"!{kind} over {type(node)}"
        return Tagged(kind, loader.construct_scalar(node) or None)

    return build


_TagLoader.add_constructor("!reset", _tagged("reset"))
_TagLoader.add_constructor("!override", _tagged("override"))


def load_piece(path: Path) -> dict[str, Any]:
    """One compose file as written, with compose's tags read as `Tagged` markers.

    This is not a stack resolver: it answers one file, no merge. A caller that needs the merged
    stack runs `compose_config` and parses the answer.
    """
    loaded = yaml.load(path.read_text(), Loader=_TagLoader)  # noqa: S506 - _TagLoader extends SafeLoader
    assert isinstance(loaded, dict), f"{path} is not a compose mapping"
    return loaded


def minimal_env() -> dict[str, str]:
    """A clean environment for `docker compose`: daemon access only, so no shell variable edits the stack."""
    return {name: value for name in COMPOSE_ENV_ALLOWLIST if (value := os.environ.get(name)) is not None}


def compose_config(
    umbrella: Path = UMBRELLA,
    *,
    interpolate: bool = True,
    env_file: Path | None = None,
    project: str | None = None,
    cwd: Path = WORKSPACE,
) -> str:
    """Run `docker compose config` on `umbrella` and return the resolved document text.

    The run needs no daemon. `interpolate=False` keeps every `${VAR}` the pieces wrote; `env_file=None`
    passes `/dev/null`, so no env file answers a variable; `project` overrides the project name only for
    the caller's own run and never lands in a shipped file.
    """
    command = ["docker", "compose"]
    if project:
        command += ["-p", project]
    command += ["-f", str(umbrella), "--env-file", str(env_file) if env_file else os.devnull, "config"]
    if not interpolate:
        command.append("--no-interpolate")
    done = subprocess.run(command, capture_output=True, text=True, check=False, env=minimal_env(), cwd=cwd)
    if done.returncode != 0:
        raise ComposeError(f"`docker compose config` on {umbrella} failed: {done.stderr.strip()}")
    return done.stdout

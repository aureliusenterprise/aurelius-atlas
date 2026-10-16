"""Resolve ``inline:`` markers in an OpenMetadata ingestion config.

OpenMetadata's ingestion SSLManager materialises TLS settings (``sslConfig``
fields) as file *content*: it writes each value to a temp file and passes
that path to the driver. Certificates, however, are generated per
developer (``nx certgen``, gitignored ``certs/`` dirs) and can never be
committed. The scan configs therefore reference them with the marker
``inline:/certs/<file>``; this script runs inside the ingestion container
(where the project's ``certs/`` dir is bind-mounted at ``/certs``), replaces
every ``inline:<path>`` value with the content of that file, and writes the
rendered config out for ``metadata ingest``.

Values without the marker — including ``${VAR}`` placeholders, which the
metadata CLI expands from the environment — are passed through untouched.

The OpenLineage connector's Kafka ``sslConfig`` is the one place where the
schema is a fixed map of ``ssl.*`` keys whose values must be certificate
*content*. Rather than a per-config marker, ``--inline-paths KEY`` reads every
string under the dotted ``KEY`` (e.g.
``source.serviceConnection.config.brokerConfig.sslConfig``) as a file path and
substitutes that file's content — the same materialisation SSLManager would
otherwise expect you to paste.

Usage: python3 render_inline.py [--inline-paths DOTTED.KEY] <config-in> <config-out>
"""

import argparse
from pathlib import Path
from typing import Any

import yaml


def resolve(node: Any) -> Any:  # noqa: ANN401 - generic YAML tree
    """Replace ``inline:<path>`` string values with that file's content."""
    if isinstance(node, dict):
        return {key: resolve(value) for key, value in node.items()}
    if isinstance(node, list):
        return [resolve(item) for item in node]
    if isinstance(node, str) and node.startswith("inline:"):
        with Path(node.removeprefix("inline:")).open(encoding="utf-8") as cert_file:
            return cert_file.read()
    return node


def resolve_paths(node: Any, dotted_key: str) -> Any:  # noqa: ANN401 - generic YAML tree
    """Read every string under ``dotted_key`` as a file and substitute its content."""
    keys = dotted_key.split(".")

    _inline_at(node, keys)
    return node


def _inline_at(current: Any, keys: list[str]) -> None:  # noqa: ANN401 - generic YAML tree
    """Descend ``keys`` and inline every string once the dotted key is consumed."""
    if not isinstance(current, dict):
        return
    if not keys:
        for key, path in current.items():
            if isinstance(path, str):
                current[key] = Path(path).read_text(encoding="utf-8")
        return
    child = current.get(keys[0])
    if child is not None:
        _inline_at(child, keys[1:])


def main() -> None:
    """Render a scan/ingestion config from argv to argv."""
    parser = argparse.ArgumentParser(
        description="Resolve inline: markers / --inline-paths in an OpenMetadata ingestion config"
    )
    parser.add_argument(
        "--inline-paths",
        default=None,
        metavar="DOTTED.KEY",
        help="read every string under this dotted YAML key as a file path and inline its content",
    )
    parser.add_argument("config_in")
    parser.add_argument("config_out")
    args = parser.parse_args()

    src, dst = args.config_in, args.config_out
    with Path(src).open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    if args.inline_paths:
        config = resolve_paths(config, args.inline_paths)
    with Path(dst).open("w", encoding="utf-8") as rendered_file:
        yaml.safe_dump(resolve(config), rendered_file)


if __name__ == "__main__":
    main()

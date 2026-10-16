"""Print the OpenMetadata version the governance stack runs.

The server image (``dev/governance/docker-compose.yaml``), the ingestion image
(``dev/governance/integrations/docker-compose.yaml``) and the ingestion image
the ``openmetadata-ingest`` target pulls (``tools/plugins/openmetadata.ts``)
must agree: the ingestion client refuses to talk to the server across major
versions. Rather than three literals kept in sync by hand, they all resolve
``OPENMETADATA_VERSION`` from the governance env file, which is the committed
source of truth (``dev/governance/.env.enc``, decrypted to ``.env``).

Resolution order (first hit wins):

1. ``OPENMETADATA_VERSION`` in the process environment
2. ``dev/governance/.env`` (the decrypted dev defaults)
3. the built-in fallback below

The fallback exists so a graph build on a fresh clone (before ``nx decrypt``)
still produces a runnable target; the target itself runs after ``decrypt``, so
at execution time the env file is authoritative.

Usage (stdlib only — runs on the host and inside openmetadata/ingestion):

    python3 tools/openmetadata/om_version.py [ENV_FILE]   # prints e.g. 2.0.4
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

FALLBACK_VERSION = "2.0.4"
"""Used only when neither the environment nor a decrypted env file is present
(e.g. ``nx`` graph inference on a fresh clone, before ``nx decrypt``)."""

_ENV_KEY = "OPENMETADATA_VERSION"

_DOTENV_LINE = re.compile(r"^([A-Za-z_]\w*)=(.*)$")


def resolve_version(env_file: str | None = None) -> str:
    """Return the pinned OpenMetadata version from env, dotenv file, or fallback."""
    from_env = os.environ.get(_ENV_KEY, "")
    if from_env:
        return from_env
    path = Path(env_file) if env_file else Path(__file__).resolve().parents[2] / "dev/governance/.env"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return FALLBACK_VERSION
    for line in text.splitlines():
        match = _DOTENV_LINE.match(line.strip())
        if match and match.group(1) == _ENV_KEY:
            value = match.group(2).strip()
            if len(value) > 1 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            if value:
                return value
    return FALLBACK_VERSION


def main() -> None:
    """Print the resolved version; optional argv[1] overrides the env file path."""
    sys.stdout.write(resolve_version(sys.argv[1] if len(sys.argv) > 1 else None))


if __name__ == "__main__":
    main()

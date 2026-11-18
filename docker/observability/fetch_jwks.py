"""The stack's JWKS copy (DD-675): the signing keys of the realm `aurelius-atlas`.

The collector validates the stack's tokens from a file (its oidc extension's
``public_keys_file``), because the issuer's URL is the proxy's browser address, which no
container can dial in-network. This one shot fetches the realm's published keys once, after
Keycloak is healthy, and writes them to the shared volume the collector mounts at ``/jwks``.

Env: ``JWKS_URL`` is the realm's certs endpoint on Keycloak's plaintext listener, and
``JWKS_FILE`` is where to write it. Keycloak generates the realm's key on its first boot and
keeps it in its database, so the file is rewritten at every stack start.
"""

# ruff: noqa: INP001, T201 - a script mounted into a container; its output is its log
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

RETRIES = 10
PAUSE_SECONDS = 3


def _fetch(url: str) -> str:
    """The JWKS document, retried: a healthy Keycloak serves the realm shortly after import."""
    last: Exception | None = None
    for _ in range(RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 - fixed internal URL
                body = response.read().decode()
            json.loads(body)  # the file must be a valid JWKS, not a half-written answer
        except Exception as error:  # noqa: BLE001 - any failure retries until the budget is spent
            last = error
            time.sleep(PAUSE_SECONDS)
        else:
            return body
    reason = f"could not fetch {url}: {last}"
    raise SystemExit(reason)


def main() -> None:
    """Write the realm's JWKS to the volume, atomically."""
    url = os.environ["JWKS_URL"]
    target = Path(os.environ["JWKS_FILE"])
    body = _fetch(url)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(body)
    temp.replace(target)
    print(f"wrote {target} ({len(body)} bytes)", flush=True)


if __name__ == "__main__":
    sys.exit(main())

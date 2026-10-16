"""Mint a short-lived OpenMetadata access token via Keycloak client_credentials.

The ingestion containers (and the lineage-registration tooling) never store
an OpenMetadata PAT: they authenticate with the ``openmetadata-bot``
service-account client in the Keycloak ``openmetadata`` realm and pass the
resulting ``id_token`` as the OM bearer token. Keycloak signs it with the
realm keys the OM server already validates, and the client's hardcoded
``email=ingestion-bot@open-metadata.org`` claim makes OM resolve the token
to the seeded ``ingestion-bot`` bot user — OM derives usernames from the
email local-part by default (see
dev/keycloak/import/openmetadata-realm.json and dev/governance/AGENTS.md;
do NOT set AUTHENTICATION_JWT_PRINCIPAL_CLAIMS_MAPPING, it breaks browser
login for every human session).

Configuration (env vars win; otherwise read from the dotenv file):

    KEYCLOAK_BOT_TOKEN_URL   token endpoint (host: keycloak.localhost:8080;
                             in-container on the keycloak network: keycloak:8080)
    OIDC_BOT_CLIENT_ID       the service-account client ("openmetadata-bot")
    OIDC_BOT_CLIENT_SECRET   its secret (dev/governance/.env.enc)

Usage (stdlib only — runs on the host and inside openmetadata/ingestion):

    python3 tools/openmetadata/kc_token.py [ENV_FILE]   # prints the id_token

With no env vars set, falls back to ``dev/governance/.env`` relative to this
file (the decrypted dev defaults). Prints the id_token on stdout; on failure
logs to stderr and exits non-zero.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# (token URL, client id, client secret) — env var names, in order
_ENV_KEYS = ("KEYCLOAK_BOT_TOKEN_URL", "OIDC_BOT_CLIENT_ID", "OIDC_BOT_CLIENT_SECRET")

_DOTENV_LINE = re.compile(r"^([A-Za-z_]\w*)=(.*)$")


def _dotenv_value(text: str, key: str) -> str:
    """Extract one key from dotenv text (unquoting only; no expansion)."""
    for line in text.splitlines():
        match = _DOTENV_LINE.match(line.strip())
        if match and match.group(1) == key:
            value = match.group(2).strip()
            if len(value) > 1 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            return value
    return ""


def _config(argv_env_file: str | None = None) -> tuple[str, str, str]:
    """Resolve (token_url, client_id, client_secret) from env or dotenv file."""
    resolved = [os.environ.get(name, "") for name in _ENV_KEYS]
    if all(resolved):
        return resolved[0], resolved[1], resolved[2]
    env_file = Path(argv_env_file) if argv_env_file else Path(__file__).resolve().parents[2] / "dev/governance/.env"
    try:
        text = env_file.read_text(encoding="utf-8")
    except OSError:
        text = ""
    values = [(env or _dotenv_value(text, name)) for env, name in zip(resolved, _ENV_KEYS, strict=True)]
    return values[0], values[1], values[2]


def fetch_id_token(token_url: str, client_id: str, client_secret: str, timeout: float = 10.0) -> str:
    """Exchange client credentials for the Keycloak-issued OM id_token.

    Raises on transport/HTTP errors or a token response without id_token.
    """
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "openid",
        }
    ).encode()
    # Only http(s) endpoints are valid here; the URL comes from project env/config.
    if not token_url.startswith(("http://", "https://")):
        msg = "token endpoint must be an http(s) URL"
        raise ValueError(msg)
    request = urllib.request.Request(  # noqa: S310
        token_url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = json.load(response)
    id_token = payload.get("id_token")
    if not id_token:
        msg = "Keycloak token response has no id_token (is 'scope=openid' honoured?)"
        raise KeyError(msg)
    return str(id_token)


def main(argv: list[str]) -> int:
    """CLI entry point: mint the token and write it to stdout."""
    env_file = argv[0] if argv else None
    token_url, client_id, client_secret = _config(env_file)
    if not (token_url and client_id and client_secret):
        logging.error(
            "kc_token: set %s, or provide a dotenv with them (dev/governance/.env by default)", ", ".join(_ENV_KEYS)
        )
        return 1
    try:
        token = fetch_id_token(token_url, client_id, client_secret)
    except Exception:
        logging.exception("kc_token: token request failed")
        return 1
    sys.stdout.write(token)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    raise SystemExit(main(sys.argv[1:]))

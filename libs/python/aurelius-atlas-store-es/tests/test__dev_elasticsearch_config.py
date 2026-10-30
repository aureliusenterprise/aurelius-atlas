"""ESD-03 (increment 0.2): credential hygiene of ``dev/elasticsearch``, as a unit test.

This was an e2e test on the dev store; it never touched the running cluster —
it inspects committed files, so it belongs in the unit suite (DD-223). The
``test`` target decrypts the dev project's ``.env`` first (project.json): the
plaintext sweep needs the decrypted file present to skip it by name.
"""

import re
from pathlib import Path

import pytest
from dotenv import dotenv_values

WORKSPACE = Path(__file__).resolve().parents[4]
DEV_ELASTICSEARCH = WORKSPACE / "dev" / "elasticsearch"


@pytest.mark.covers(rules=["ESD-03"])
def test__dev_elasticsearch_password_is_only_in_the_encrypted_env() -> None:
    """The password is stored encrypted, reaches the container by interpolation, and is in no other file."""
    encrypted = (DEV_ELASTICSEARCH / ".env.enc").read_text()
    assert re.search(r"^ELASTICSEARCH_PASSWORD=ENC\[", encrypted, re.MULTILINE)
    assert "${ELASTICSEARCH_PASSWORD:?}" in (DEV_ELASTICSEARCH / "docker-compose.yaml").read_text()

    # The decrypted .env (the test target's decrypt dependency) is the one
    # plaintext copy the rules allow; certs/ is skipped — the password is
    # inside the PKCS12 material's reach and not a plaintext leak.
    dev_env = dotenv_values(DEV_ELASTICSEARCH / ".env")
    password = dev_env["ELASTICSEARCH_PASSWORD"]
    assert password is not None
    plaintext = [
        path
        for path in DEV_ELASTICSEARCH.rglob("*")
        if path.is_file() and path.name != ".env" and "certs" not in path.parts and password in path.read_text()
    ]
    assert plaintext == []

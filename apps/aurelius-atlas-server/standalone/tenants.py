"""The standalone stack's tenants: the ``tenants`` service of the profile ``tenancy`` (ADR 063, series 15).

It provisions the tenant ``demo`` with the sample ``TENANT_SAMPLE`` from ``SAMPLE_DIR`` and the tenant ``meyn``
without one, through the server's own command, which keeps their organizations in the realm atlas too (TRM-02),
and makes each tenant's ``<tenant>_atlas`` its administrator there (TRM-06).
A tenant already provisioned is left as it is, so the service runs at every start. Then it gives the realm's
``operator`` a user of the same name in the store, with the role ``aurelius_atlas_store_admin``: every privilege
on every index, for running the platform (ADR 063's direct store access). It runs in the server image.
"""

# ruff: noqa: INP001, T201 - a script mounted into a container; its output is its log

import json
import os
import sys
from pathlib import Path

from aurelius_atlas_server.provisioning import main
from elasticsearch import Elasticsearch

STORE_ADMIN_ROLE = "aurelius_atlas_store_admin"
"""The operator's role in the store: the cluster managed and every index, every tenant's among them."""


def provision() -> None:
    """Provision demo with the sample and meyn without one, each with its ``<tenant>_atlas`` as its administrator
    in the realm (TRM-06, DD-602); an active tenant is left as it is but its realm.
    """  # noqa: D205 - one sentence
    sample = Path(os.environ.get("SAMPLE_DIR", "/sample")) / os.environ.get("TENANT_SAMPLE", "sample_data.zip")
    for argv in (
        ["provision", "demo", "--existing-ok", "--sample", str(sample), "--admin", "demo_atlas"],
        ["provision", "meyn", "--existing-ok", "--admin", "meyn_atlas"],
        ["list"],
    ):
        if main(argv) != 0:
            sys.exit(1)


def store_operator() -> None:
    """The user ``operator`` in the store, an admin of every index (ADR 063's operators' store access)."""
    store = Elasticsearch(
        json.loads(os.environ["AURELIUS_ATLAS_SERVER_ELASTICSEARCH_HOSTS"]),
        basic_auth=("elastic", os.environ["AURELIUS_ATLAS_SERVER_ELASTICSEARCH_PASSWORD"]),
        ca_certs=os.environ["AURELIUS_ATLAS_SERVER_ELASTICSEARCH_CA_CERTS"],
    )
    store.security.put_role(
        name=STORE_ADMIN_ROLE,
        cluster=["manage", "monitor"],
        indices=[{"names": ["*"], "privileges": ["all"], "allow_restricted_indices": False}],
    )
    store.security.put_user(
        username="operator",
        password=os.environ["OPERATOR_PASSWORD"],
        roles=[STORE_ADMIN_ROLE],
        full_name="Platform Operator",
    )
    print(f"The store's user operator holds {STORE_ADMIN_ROLE}")


if __name__ == "__main__":
    provision()
    store_operator()

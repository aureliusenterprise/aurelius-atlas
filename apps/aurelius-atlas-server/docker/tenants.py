"""The standalone stack's tenants: the ``tenants`` service of the profile ``tenancy`` (ADR 063, series 15).

It provisions the tenant ``demo`` with the sample ``TENANT_SAMPLE`` from ``SAMPLE_DIR`` and the tenant ``meyn``
without one, through the server's own command, which keeps their organizations in the realm aurelius-atlas too
(TRM-02). Each tenant gets its own users, made through the server's own code and not in the realm file (DD-700,
TAD-13): ``<tenant>_atlas`` with every role, its administrator (TRM-06), ``<tenant>_steward`` reading and writing,
and ``<tenant>_scientist`` reading, each a member of its tenant alone, with the password
``<TENANT>_USER_<ROLE>_PASSWORD``. A user already there keeps its password; a tenant without those passwords gets
no users. Then it gives the platform an ``operator`` user of its own in the store, with the role
``aurelius_atlas_store_admin``: every privilege on every index, for running the platform (ADR 063's direct store
access). It runs in the server image.
"""

# ruff: noqa: INP001, T201 - a script mounted into a container; its output is its log

import asyncio
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from aurelius_atlas_server.provisioning import main, realm_of
from aurelius_atlas_server.realm_tenants import RealmError, RealmTenants
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_server.tenant_people import Role, ensure_person, standard_email, standard_username
from elasticsearch import Elasticsearch

STORE_ADMIN_ROLE = "aurelius_atlas_store_admin"
"""The operator's role in the store: the cluster managed and every index, every tenant's among them."""


def provision() -> None:
    """Provision demo with the sample and meyn without one, their organizations and users included (TRM-02,
    DD-700); an active tenant is left as it is but its realm and its missing users.
    """  # noqa: D205 - one sentence
    sample = Path(os.environ.get("SAMPLE_DIR", "/sample")) / os.environ.get("TENANT_SAMPLE", "sample_data.zip")
    for alias, extra in (("demo", ["--sample", str(sample)]), ("meyn", [])):
        if main(["provision", alias, "--existing-ok", *extra]) != 0:
            sys.exit(1)
        if asyncio.run(with_realm(alias)) and main(["admin", alias, "add", f"{alias}_atlas"]) != 0:
            sys.exit(1)
    # Each tenant's Grafana organization, data sources, dashboards and members, and the platform's (TGF-13).
    if main(["grafana", "sync"]) != 0 or main(["list"]) != 0:
        sys.exit(1)


async def with_realm(alias: str) -> bool:
    """The tenant's users, through the provisioning client; whether its administrator is there."""
    realm = realm_of(ServerSettings())  # pyright: ignore[reportCallIssue] - the settings come from the environment
    if realm is None:
        print(f"No provisioning client: {alias} gets no users")
        return False
    try:
        return f"{alias}_atlas" in await tenant_users(realm, alias, os.environ)
    finally:
        await realm.admin.close()


async def tenant_users(realm: RealmTenants, alias: str, environment: Mapping[str, str]) -> list[str]:
    """Make the tenant's three users through the server's own code, with their permanent passwords from
    ``<TENANT>_USER_<ROLE>_PASSWORD`` (TAD-13, DD-700); the usernames that are the tenant's members now.

    A user already in the realm keeps its password and is put in the tenant's groups again (TAD-06); a role
    without its password variable gets no user, and one the realm refuses, as for a password its policy rejects,
    is logged and left out, the others made all the same.
    """  # noqa: D205 - one sentence
    org = await realm.organization(alias)
    if org is None:
        msg = f"the tenant {alias} has no organization"
        raise RealmError(msg)
    made: list[str] = []
    for role in Role:
        username = standard_username(alias, role)
        password = environment.get(f"{alias.upper().replace('-', '_')}_USER_{role.value.upper()}_PASSWORD", "")
        if not password:
            print(f"{username}: no password set, not made")
            continue
        try:
            person = await ensure_person(
                realm, org, username, role, email=standard_email(alias, role), password=password
            )
        except RealmError as refused:
            print(f"{username}: not made: {refused}")
            continue
        print(f"{username}: {'made' if person.made else 'there already'}")
        made.append(username)
    return made


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

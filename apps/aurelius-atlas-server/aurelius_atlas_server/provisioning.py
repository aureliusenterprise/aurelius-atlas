"""``python -m aurelius_atlas_server.provisioning``: provision, trust, list or remove tenants, keep the operators in
step, name a tenant's administrators, and add a tenant with its people (TPR-01 to TPR-06, TRM-01 to TRM-10,
TAD-01 to TAD-11).

The command reads the server's settings from the same environment, so it runs from the server's image: by hand,
or as a Job of the chart (15.4). A tenant is provisioned with the server's own start sequence and its sample
imported by the core's import service, as ``admin/import`` imports one (DD-573). With the provisioning client's
secret, the realm is kept in step too: the tenant's organization, its operators and administrators (DD-600).
"""  # noqa: D205 - one sentence

import argparse
import asyncio
import socket
import sys
import time
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path

from aurelius_atlas_core.audits_writer import AuditsWriter
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.import_service import ImportService
from aurelius_atlas_core.request_context import current_user
from aurelius_atlas_model.impexp import AtlasImportResult, OperationStatus
from aurelius_atlas_store_es import ElasticsearchStore

from aurelius_atlas_server.grafana_tenants import GrafanaAdmin, GrafanaError, GrafanaTenants
from aurelius_atlas_server.grafana_tenants import Person as GrafanaPerson
from aurelius_atlas_server.realm_tenants import KeycloakAdmin, RealmError, RealmOrganization, RealmTenants
from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_server.tenancy import ALIAS
from aurelius_atlas_server.tenant_people import Person, Role, ensure_person, standard_email, standard_username
from aurelius_atlas_server.tenant_stores import open_stores, store_aliases, tenant_prefix
from aurelius_atlas_server.tenants import StoredTenant, TenantsIndex, TenantState

__all__ = ["PROG", "Provisioner", "ProvisioningError", "main", "parser", "run"]

PROG = "python -m aurelius_atlas_server.provisioning"

NO_REALM = "The realm is left as it is: tenancy_admin_client_secret is not set"
"""What the command says once when it can't keep the realm in step (TRM-01, DD-603)."""

NO_GRAFANA = "Grafana is left as it is: grafana_url or grafana_admin_password is not set"
"""What the command says once when it can't keep Grafana in step (TGF-11)."""

REMOVAL_WAITS = 2
"""How many of the servers' refresh intervals removal waits: their next read, then their workers' stop (DD-577)."""

IMPORTED = frozenset({OperationStatus.SUCCESS, OperationStatus.PARTIAL_SUCCESS})
"""The import results a provisioning accepts, as the standalone sample import does."""


class ProvisioningError(Exception):
    """A command refused, with the reason it prints."""


def parser() -> argparse.ArgumentParser:
    """The command's arguments: ``provision``, ``trust``, ``list``, ``remove``, ``operators`` or ``admin``."""
    commands = argparse.ArgumentParser(prog=PROG, description="Provision, trust, list or remove tenants.")
    choices = commands.add_subparsers(dest="command", required=True)
    provisioning = choices.add_parser("provision", help="create a tenant's indices and load its models")
    provisioning.add_argument("alias", help="the tenant's Keycloak organization alias")
    provisioning.add_argument("--sample", type=Path, help="an Apache Atlas export ZIP to import into the tenant")
    provisioning.add_argument(
        "--no-operator-trust", action="store_true", help="record that the tenant doesn't trust the operators"
    )
    provisioning.add_argument(
        "--existing-ok", action="store_true", help="leave a tenant already active as it is, and exit 0"
    )
    provisioning.add_argument(
        "--admin", action="append", default=[], dest="admins", metavar="USERNAME", help="a tenant administrator"
    )
    trusting = choices.add_parser("trust", help="record whether a tenant trusts the operators")
    trusting.add_argument("alias")
    trusting.add_argument("trust", choices=["on", "off"])
    choices.add_parser("list", help="the recorded tenants: alias, state, trust and sample")
    removing = choices.add_parser("remove", help="delete a tenant's indices, organization and record")
    removing.add_argument("alias")
    choices.add_parser("operators", help="bring the operators' membership of every tenant in step")
    administering = choices.add_parser("admin", help="add or remove a tenant administrator")
    administering.add_argument("alias")
    administering.add_argument("change", choices=["add", "remove"])
    administering.add_argument("username")
    adding = choices.add_parser("add", help="add a tenant with its people, and a sample if named (TAD-01)")
    adding.add_argument("alias", help="the tenant's Keycloak organization alias")
    adding.add_argument("--sample", metavar="NAME", help="a sample of the sample folder, without .zip")
    adding.add_argument(
        "--users", choices=["atlas", "all"], default="atlas", help="atlas: <tenant>_atlas alone; all: the three"
    )
    people = choices.add_parser("user", help="add a person to a tenant, or take them out (TAD-07, TAD-09)")
    people.add_argument("alias")
    people.add_argument("change", choices=["add", "remove"])
    people.add_argument("username")
    people.add_argument("--role", choices=[role.value for role in Role], default=Role.SCIENTIST.value)
    people.add_argument("--email", help="the person's email; <username>@example.com unless given")
    choices.add_parser("samples", help="the samples of the sample folder (TAD-10)")
    grafana = choices.add_parser("grafana", help="bring every tenant's Grafana organization in step (TGF-10)")
    grafana.add_argument("action", choices=["sync"])
    return commands


async def run(  # noqa: PLR0913 - the command, its settings, and where it writes and waits
    args: argparse.Namespace,
    settings: ServerSettings,
    out: Callable[[str], None],
    *,
    store: ElasticsearchStore | None = None,
    realm: RealmTenants | None = None,
    sleep: Callable[[float], Awaitable[object]] = asyncio.sleep,
    user: str | None = None,
    grafana: GrafanaTenants | None = None,
) -> None:
    """Carry out the parsed command against the store and, with the client's secret, the realm, writing what it
    did to ``out``; ``realm`` replaces the one the settings make.

    Raises:
        ProvisioningError: When the command refuses, or the realm refuses a call (TPR-02, TPR-05, TPR-06, TRM-10).
    """  # noqa: D205 - one sentence
    realm = realm if realm is not None else realm_of(settings)
    try:
        async with store if store is not None else ElasticsearchStore(settings.store_settings()) as opened:
            tenants = TenantsIndex(opened)
            await tenants.prepare()
            who = user if user is not None else current_user()
            grafana = grafana if grafana is not None else grafana_of(settings, opened)
            provisioner = Provisioner(
                settings, opened, tenants, out=out, sleep=sleep, who=who, realm=realm, grafana=grafana
            )
            await _dispatch(args, provisioner)
    except (RealmError, GrafanaError) as error:
        raise ProvisioningError(str(error)) from error
    finally:
        if realm is not None:
            await realm.admin.close()
        if grafana is not None:
            await grafana.grafana.close()


async def _dispatch(args: argparse.Namespace, provisioner: Provisioner) -> None:
    """Run the parsed command."""
    if args.command == "provision":
        sample = None if args.sample is None else await asyncio.to_thread(_read_sample, args.sample)
        await provisioner.provision(
            args.alias,
            sample=sample,
            trusts_operators=not args.no_operator_trust,
            existing_ok=args.existing_ok,
            admins=args.admins,
        )
    elif args.command == "trust":
        await provisioner.trust(args.alias, trusts=args.trust == "on")
    elif args.command == "list":
        await provisioner.list()
    elif args.command == "operators":
        await provisioner.operators()
    elif args.command == "admin":
        await provisioner.admin(args.alias, args.username, add=args.change == "add")
    elif args.command in {"add", "user", "samples", "grafana"}:
        await _dispatch_people(args, provisioner)
    else:
        await provisioner.remove(args.alias)


async def _dispatch_people(args: argparse.Namespace, provisioner: Provisioner) -> None:
    """Run a command of 15.7's or 15.9's: a tenant with its people, one person, the samples, or Grafana."""
    if args.command == "add":
        await provisioner.add(args.alias, sample=args.sample, everyone=args.users == "all")
    elif args.command == "user" and args.change == "add":
        await provisioner.user_add(args.alias, args.username, Role(args.role), email=args.email)
    elif args.command == "user":
        await provisioner.user_remove(args.alias, args.username)
    elif args.command == "samples":
        provisioner.samples()
    else:
        await provisioner.grafana_sync()


def realm_of(settings: ServerSettings) -> RealmTenants | None:
    """The realm's tenants as the provisioning client reaches them, or None without its secret (TRM-01)."""
    if settings.tenancy_admin_client_secret is None:
        return None
    admin = KeycloakAdmin(
        str(settings.auth_server_url),
        settings.auth_realm,
        settings.tenancy_admin_client_id,
        settings.tenancy_admin_client_secret.get_secret_value(),
        http=KeycloakAdmin.http(None if settings.auth_ca_file is None else str(settings.auth_ca_file)),
    )
    return RealmTenants(
        admin,
        operator_organization=settings.tenancy_operator_organization,
        operator_role=settings.tenancy_operator_role,
    )


def grafana_of(settings: ServerSettings, store: ElasticsearchStore) -> GrafanaTenants | None:
    """The tenants' Grafana as its local administrator reaches it, or None without its address and password
    (TGF-11, TGF-12).
    """  # noqa: D205 - one sentence
    if settings.grafana_url is None or settings.grafana_admin_password is None:
        return None
    admin = GrafanaAdmin(
        settings.grafana_url,
        settings.grafana_admin_user,
        settings.grafana_admin_password.get_secret_value(),
        http=GrafanaAdmin.http(),
    )
    return GrafanaTenants(
        admin,
        store.client,
        store_url=str(settings.elasticsearch_hosts[0]).rstrip("/"),
        ca_pem=Path(settings.elasticsearch_ca_certs).read_text(),
    )


class Provisioner:
    """The commands on the tenants of ``store``, recorded in ``tenants`` as ``who``; ``out`` hears what was done."""

    def __init__(  # noqa: PLR0913 - the store, its records, and where the commands write and wait
        self,
        settings: ServerSettings,
        store: ElasticsearchStore,
        tenants: TenantsIndex,
        *,
        out: Callable[[str], None],
        sleep: Callable[[float], Awaitable[object]],
        who: str,
        realm: RealmTenants | None = None,
        grafana: GrafanaTenants | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._tenants = tenants
        self._out = out
        self._sleep = sleep
        self._who = who
        self._realm = realm
        self._operators: frozenset[str] | None = None
        self._said_no_realm = False
        self._grafana = grafana
        self._said_no_grafana = False

    async def provision(
        self,
        alias: str,
        *,
        sample: tuple[str, bytes] | None,
        trusts_operators: bool,
        existing_ok: bool = False,
        admins: Sequence[str] = (),
    ) -> None:
        """Record the tenant ``provisioning``, open its store set, import the sample (its file name and content),
        bring its realm in step with ``admins`` its administrators, record it ``active`` (TPR-02 to TPR-04,
        TRM-02, TRM-03); with ``existing_ok``, leave a tenant already ``active`` as it is but its realm (WPT-07).

        Raises:
            ProvisioningError: For an alias that isn't index-safe, the operator organization's, a tenant already
                ``active`` without ``existing_ok`` or ``removing``, or a sample whose import failed.
        """  # noqa: D205 - one sentence
        _check_alias(alias, self._settings)
        existing = await self._tenants.get(alias)
        if existing is not None and existing.state is TenantState.ACTIVE and existing_ok:
            await self._in_step(await self._with_admins(existing, admins))
            self._out(f"{alias} is already provisioned")
            return
        if existing is not None and existing.state is not TenantState.PROVISIONING:
            msg = f"tenant {alias} is {existing.state.value}"
            raise ProvisioningError(msg)
        now = _now()
        record = StoredTenant(
            alias=alias,
            state=TenantState.PROVISIONING,
            trusts_operators=trusts_operators,
            sample=None if sample is None else sample[0],
            created_at=now if existing is None else existing.created_at,
            updated_at=now,
            updated_by=self._who,
            operator_members=[] if existing is None else existing.operator_members,
            administrators=[] if existing is None else existing.administrators,
        )
        record = await self._with_admins(record, admins)
        await self._tenants.put(record)
        prefix = tenant_prefix(alias)
        settings = self._settings
        opened = await open_stores(
            self._store,
            prefix,
            models_dirs=settings.model_dirs,
            embedding_dimensions=settings.embedding_dimensions if settings.embedding_url is not None else None,
            typedef_refresh_seconds=settings.typedef_refresh_seconds,
        )
        if sample is not None:
            name, content = sample
            writer = EntityWriter(opened.entity_store, user=self._who, notifier=opened.notifier)
            audits = AuditsWriter(opened.entity_store, cluster_name=settings.cluster_name, user=self._who)
            importer = ImportService(opened.entity_store, opened.typedef_store, writer, audits=audits)
            result = await importer.run(content, None, self._who, socket.gethostname(), "")
            _check_import(result, name)
        record = await self._in_step(record)
        await self._tenants.put(record.model_copy(update={"state": TenantState.ACTIVE, "updated_at": _now()}))
        self._out(f"Provisioned {alias}: indices {prefix}-*, {'sample ' + sample[0] if sample else 'no sample'}")

    async def trust(self, alias: str, *, trusts: bool) -> None:
        """Record whether a recorded tenant trusts the operators (TPR-03).

        Raises:
            ProvisioningError: For a tenant with no record.
        """
        record = await self._recorded(alias)
        record = record.model_copy(update={"trusts_operators": trusts, "updated_at": _now(), "updated_by": self._who})
        await self._tenants.put(record)
        if record.state is TenantState.ACTIVE:
            await self._in_step(record)
        self._out(f"{alias} {'trusts' if trusts else 'does not trust'} the operators")

    async def operators(self) -> None:
        """Bring every ``active`` tenant's operators in step (TRM-05)."""
        if self._realm is None:
            self._no_realm()
            return
        for tenant in await self._tenants.list():
            if tenant.state is TenantState.ACTIVE:
                await self._in_step(tenant, report=True)
        await self.grafana_sync()

    async def admin(self, alias: str, username: str, *, add: bool) -> None:
        """Add or remove one of the tenant's administrators, and their rights in the realm (TRM-06, TRM-07).

        Raises:
            ProvisioningError: Without the realm, for a tenant with no record, or a user the realm doesn't have.
        """
        if self._realm is None:
            msg = "a tenant's administrators are kept in the realm: tenancy_admin_client_secret is not set"
            raise ProvisioningError(msg)
        record = await self._recorded(alias)
        user = await self._realm.user_id(username)
        admins = set(record.administrators) | {user} if add else set(record.administrators) - {user}
        record = record.model_copy(
            update={"administrators": sorted(admins), "updated_at": _now(), "updated_by": self._who}
        )
        await self._tenants.put(record)
        if record.state is TenantState.ACTIVE:
            await self._in_step(record)
        self._out(f"{username} {'administers' if add else 'no longer administers'} {alias}")

    async def add(self, alias: str, *, sample: str | None, everyone: bool) -> None:
        """Provision the tenant as ``provision --existing-ok`` does, the sample named imported into a new one, make
        its standard users and ``<tenant>_atlas`` its administrator, then write the summary (TAD-01 to TAD-06,
        TAD-08).

        Raises:
            ProvisioningError: Before anything is done, for an alias ``provision`` refuses, a sample the sample
                folder doesn't have or no realm; else for the step that failed (TAD-11).
        """  # noqa: D205 - one sentence
        _check_alias(alias, self._settings)
        realm = self._people_realm()
        content = None if sample is None else await asyncio.to_thread(self._sample, sample)
        existing = await self._tenants.get(alias)
        new = existing is None or existing.state is not TenantState.ACTIVE
        await self.provision(alias, sample=content if new else None, trusts_operators=True, existing_ok=True)
        org = await self._organization(realm, alias)
        roles = list(Role) if everyone else [Role.ATLAS]
        people = [
            await ensure_person(realm, org, standard_username(alias, role), role, email=standard_email(alias, role))
            for role in roles
        ]
        await self.admin(alias, standard_username(alias, Role.ATLAS), add=True)
        await self._grafana_tenant(alias)
        if sample is None:
            loaded = "no sample"
        elif new:
            loaded = f"sample {sample}"
        else:
            loaded = f"no sample: {alias} was provisioned already, so {sample} is not loaded"
        self._summary(alias, loaded, people)

    async def user_add(self, alias: str, username: str, role: Role, *, email: str | None) -> None:
        """Add one person to an ``active`` tenant: found or made, a member in the groups of their role (TAD-07).

        Raises:
            ProvisioningError: Without the realm, or for a tenant that isn't ``active``.
        """
        realm = self._people_realm()
        record = await self._recorded(alias)
        if record.state is not TenantState.ACTIVE:
            msg = f"tenant {alias} is {record.state.value}"
            raise ProvisioningError(msg)
        org = await self._organization(realm, alias)
        person = await ensure_person(realm, org, username, role, email=email or f"{username}@example.com")
        await self._grafana_tenant(alias)
        self._summary(alias, None, [person])

    async def user_remove(self, alias: str, username: str) -> None:
        """Take a person out of the tenant: their membership, groups and administration there (TAD-09).

        Raises:
            ProvisioningError: Without the realm, for a tenant with no record, or a user the realm doesn't have.
        """
        realm = self._people_realm()
        record = await self._recorded(alias)
        user = await realm.user_id(username)
        if user in record.administrators:
            await self.admin(alias, username, add=False)
        await realm.remove_member(await self._organization(realm, alias), user)
        await self._grafana_tenant(alias)
        self._out(f"{username} is no longer a member of {alias}")

    async def grafana_sync(self) -> None:
        """Bring every ``active`` tenant's Grafana organization in step with the realm, the platform's organization
        with the operators, and delete the Grafana users the realm gives no tenant (TGF-09, TGF-10, TGF-14).
        """  # noqa: D205 - one sentence
        if self._grafana is None:
            self._no_grafana()
            return
        realm = self._people_realm()
        keep: set[str] = set()
        for tenant in await self._tenants.list():
            if tenant.state is TenantState.ACTIVE:
                keep |= {person.login for person in await self._grafana_tenant(tenant.alias)}
        operators = [GrafanaPerson(*await realm.username_and_email(user)) for user in sorted(await realm.operators())]
        await self._grafana.sync_platform(operators)
        keep |= {person.login for person in operators}
        deleted = await self._grafana.cleanup(keep)
        self._out(f"Grafana: {len(operators)} operators in the platform's organization, {len(deleted)} users deleted")

    async def _grafana_tenant(self, alias: str) -> list[GrafanaPerson]:
        """The tenant's Grafana organization, data sources, dashboards and members in step with the realm; its
        members (TGF-04 to TGF-08).
        """  # noqa: D205 - one sentence
        if self._grafana is None:
            self._no_grafana()
            return []
        realm = self._people_realm()
        org = await self._organization(realm, alias)
        members = [GrafanaPerson(*await realm.username_and_email(user)) for user in sorted(await realm.members(org))]
        grafana_org = await self._grafana.ensure_tenant(alias)
        added, removed = await self._grafana.sync_members(grafana_org, members)
        self._out(f"Grafana {alias}: organization {grafana_org}, {added} members added, {removed} removed")
        return members

    def _no_grafana(self) -> None:
        """Say once that Grafana is left as it is (TGF-11)."""
        if not self._said_no_grafana:
            self._said_no_grafana = True
            self._out(NO_GRAFANA)

    def samples(self) -> None:
        """Write the samples of the sample folder, one name per line (TAD-10)."""
        for name in self._sample_names():
            self._out(name)

    def _people_realm(self) -> RealmTenants:
        """The realm, which keeps a tenant's people.

        Raises:
            ProvisioningError: Without the provisioning client's secret.
        """
        if self._realm is None:
            msg = "a tenant's people are kept in the realm: tenancy_admin_client_secret is not set"
            raise ProvisioningError(msg)
        return self._realm

    @staticmethod
    async def _organization(realm: RealmTenants, alias: str) -> RealmOrganization:
        """The tenant's organization.

        Raises:
            ProvisioningError: When the realm has none, as before the tenant is provisioned.
        """
        org = await realm.organization(alias)
        if org is None:
            msg = f"the realm has no organization {alias}"
            raise ProvisioningError(msg)
        return org

    def _sample_names(self) -> list[str]:
        """The samples of the sample folder, by name, sorted."""
        folder = self._settings.sample_dir
        if folder is None or not folder.is_dir():
            return []
        return sorted(path.stem for path in folder.glob("*.zip") if path.is_file())

    def _sample(self, name: str) -> tuple[str, bytes]:
        """The sample's file name and content.

        Raises:
            ProvisioningError: For a name no sample has, listing the samples there (TAD-02).
        """
        names = self._sample_names()
        if name not in names:
            offered = ", ".join(names) if names else "none"
            msg = f"no sample {name}: the sample folder holds {offered}"
            raise ProvisioningError(msg)
        assert self._settings.sample_dir is not None  # noqa: S101 - a name was found in it
        return _read_sample(self._settings.sample_dir / f"{name}.zip")

    def _summary(self, alias: str, loaded: str | None, people: Sequence[Person]) -> None:
        """Write the tenant, the sample or why none, and each person: made with their password, or existing
        (TAD-08). A password is written here and nowhere else (TAD-05).
        """  # noqa: D205 - one sentence
        self._out(f"Tenant {alias}" + ("" if loaded is None else f": {loaded}"))
        for person in people:
            if person.made and person.password is not None:
                state = f"made, temporary password {person.password}"
            elif person.made:
                state = "made"
            else:
                state = "existed, password unchanged"
            self._out(f"  {person.username} ({person.role.value}): {state}")

    async def list(self) -> None:
        """Write each recorded tenant: alias, state, trust and sample (TPR-06)."""
        for tenant in await self._tenants.list():
            trust = "trusts operators" if tenant.trusts_operators else "no operator trust"
            self._out(f"{tenant.alias}\t{tenant.state.value}\t{trust}\t{tenant.sample or '-'}")

    async def remove(self, alias: str) -> None:
        """Record the tenant ``removing``, wait twice the servers' refresh, so that every server has read it and
        stopped the tenant's workers, delete the indices behind its aliases and its record (TPR-05, WPT-05, DD-574,
        DD-577).

        Raises:
            ProvisioningError: For the operator organization or a tenant with no record.
        """  # noqa: D205 - one sentence
        if alias == self._settings.tenancy_operator_organization:
            msg = f"{alias} is the operator organization, whose indices are the default ones"
            raise ProvisioningError(msg)
        record = await self._recorded(alias)
        removing = {"state": TenantState.REMOVING, "updated_at": _now(), "updated_by": self._who}
        await self._tenants.put(record.model_copy(update=removing))
        await self._sleep(REMOVAL_WAITS * self._settings.tenancy_refresh_seconds)
        client = self._store.client
        deleted: list[str] = []
        for name in store_aliases(tenant_prefix(alias)):
            if await client.indices.exists_alias(name=name):
                indices = sorted((await client.indices.get(index=name)).body)
                await client.indices.delete(index=",".join(indices))
                deleted += indices
        if self._realm is not None:
            await self._realm.delete(alias)
        else:
            self._no_realm()
        if self._grafana is not None:
            await self._grafana.remove_tenant(alias)
        await self._tenants.delete(alias)
        self._out(f"Removed {alias}: {len(deleted)} indices deleted")

    async def _in_step(self, record: StoredTenant, *, report: bool = False) -> StoredTenant:
        """The record after its realm is brought in step, saved as it changes; as it was without the realm."""
        if self._realm is None:
            self._no_realm()
            return record
        if self._operators is None:
            self._operators = await self._realm.operators()
        record, taken = await self._realm.in_step(record, self._operators, self._tenants.put)
        if report or taken.added or taken.removed:
            self._out(f"Realm {record.alias}: {len(taken.added)} operators added, {len(taken.removed)} removed")
        return record

    async def _with_admins(self, record: StoredTenant, admins: Sequence[str]) -> StoredTenant:
        """The record with the named administrators added.

        Raises:
            ProvisioningError: When administrators are named without the realm.
        """
        if not admins:
            return record
        if self._realm is None:
            msg = "a tenant's administrators are kept in the realm: tenancy_admin_client_secret is not set"
            raise ProvisioningError(msg)
        named = {await self._realm.user_id(username) for username in admins}
        return record.model_copy(update={"administrators": sorted(set(record.administrators) | named)})

    def _no_realm(self) -> None:
        """Say once that the realm is left as it is (TRM-01)."""
        if not self._said_no_realm:
            self._said_no_realm = True
            self._out(NO_REALM)

    async def _recorded(self, alias: str) -> StoredTenant:
        """The tenant's record.

        Raises:
            ProvisioningError: When there is none.
        """
        record = await self._tenants.get(alias)
        if record is None:
            msg = f"no tenant {alias} is recorded"
            raise ProvisioningError(msg)
        return record


def _read_sample(path: Path) -> tuple[str, bytes]:
    """The sample's file name and content.

    Raises:
        ProvisioningError: When no file is at the path.
    """
    if not path.is_file():
        msg = f"no export ZIP at {path}"
        raise ProvisioningError(msg)
    return path.name, path.read_bytes()


def _check_alias(alias: str, settings: ServerSettings) -> None:
    """Refuse an alias that isn't index-safe or is the operator organization's (TPR-02, DD-565)."""
    if ALIAS.fullmatch(alias) is None:
        msg = f"{alias!r} is no tenant alias: a lowercase letter or digit, then up to 62 of them or '-'"
        raise ProvisioningError(msg)
    if alias == settings.tenancy_operator_organization:
        msg = f"{alias} is the operator organization, which is always provisioned"
        raise ProvisioningError(msg)


def _check_import(result: AtlasImportResult, name: str) -> None:
    """Refuse a sample import that neither succeeded nor partly succeeded."""
    if result.operation_status not in IMPORTED:
        msg = f"the import of {name} ended {result.operation_status.value}"
        raise ProvisioningError(msg)


def _now() -> int:
    """Now, in epoch milliseconds."""
    return int(time.time() * 1000)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command; 0 when it did what was asked, 1 when it refused (TPR-06)."""
    args = parser().parse_args(argv)
    settings = ServerSettings()  # pyright: ignore[reportCallIssue] - read from the environment
    try:
        asyncio.run(run(args, settings, print))
    except ProvisioningError as error:
        print(f"{PROG}: {error}", file=sys.stderr)  # noqa: T201 - the command's error output
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

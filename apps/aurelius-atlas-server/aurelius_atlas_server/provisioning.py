"""``python -m aurelius_atlas_server.provisioning``: provision, trust, list or remove tenants (TPR-01 to TPR-06).

The command reads the server's settings from the same environment, so it runs from the server's image: by hand,
or as a Job of the chart (15.4). A tenant is provisioned with the server's own start sequence and its sample
imported by the core's import service, as ``admin/import`` imports one (DD-573).
"""

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

from aurelius_atlas_server.settings import ServerSettings
from aurelius_atlas_server.tenancy import ALIAS
from aurelius_atlas_server.tenant_stores import open_stores, store_aliases, tenant_prefix
from aurelius_atlas_server.tenants import StoredTenant, TenantsIndex, TenantState

__all__ = ["PROG", "Provisioner", "ProvisioningError", "main", "parser", "run"]

PROG = "python -m aurelius_atlas_server.provisioning"

IMPORTED = frozenset({OperationStatus.SUCCESS, OperationStatus.PARTIAL_SUCCESS})
"""The import results a provisioning accepts, as the standalone sample import does."""


class ProvisioningError(Exception):
    """A command refused, with the reason it prints."""


def parser() -> argparse.ArgumentParser:
    """The command's arguments: ``provision``, ``trust``, ``list`` or ``remove``."""
    commands = argparse.ArgumentParser(prog=PROG, description="Provision, trust, list or remove tenants.")
    choices = commands.add_subparsers(dest="command", required=True)
    provisioning = choices.add_parser("provision", help="create a tenant's indices and load its models")
    provisioning.add_argument("alias", help="the tenant's Keycloak organization alias")
    provisioning.add_argument("--sample", type=Path, help="an Apache Atlas export ZIP to import into the tenant")
    provisioning.add_argument(
        "--no-operator-trust", action="store_true", help="record that the tenant doesn't trust the operators"
    )
    trusting = choices.add_parser("trust", help="record whether a tenant trusts the operators")
    trusting.add_argument("alias")
    trusting.add_argument("trust", choices=["on", "off"])
    choices.add_parser("list", help="the recorded tenants: alias, state, trust and sample")
    removing = choices.add_parser("remove", help="delete a tenant's indices and its record")
    removing.add_argument("alias")
    return commands


async def run(  # noqa: PLR0913 - the command, its settings, and where it writes and waits
    args: argparse.Namespace,
    settings: ServerSettings,
    out: Callable[[str], None],
    *,
    store: ElasticsearchStore | None = None,
    sleep: Callable[[float], Awaitable[object]] = asyncio.sleep,
    user: str | None = None,
) -> None:
    """Carry out the parsed command against the store, writing what it did to ``out``.

    Raises:
        ProvisioningError: When the command refuses (TPR-02, TPR-05, TPR-06).
    """
    async with store if store is not None else ElasticsearchStore(settings.store_settings()) as opened:
        tenants = TenantsIndex(opened)
        await tenants.prepare()
        provisioner = Provisioner(
            settings, opened, tenants, out=out, sleep=sleep, who=user if user is not None else current_user()
        )
        if args.command == "provision":
            sample = None if args.sample is None else await asyncio.to_thread(_read_sample, args.sample)
            await provisioner.provision(args.alias, sample=sample, trusts_operators=not args.no_operator_trust)
        elif args.command == "trust":
            await provisioner.trust(args.alias, trusts=args.trust == "on")
        elif args.command == "list":
            await provisioner.list()
        else:
            await provisioner.remove(args.alias)


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
    ) -> None:
        self._settings = settings
        self._store = store
        self._tenants = tenants
        self._out = out
        self._sleep = sleep
        self._who = who

    async def provision(self, alias: str, *, sample: tuple[str, bytes] | None, trusts_operators: bool) -> None:
        """Record the tenant ``provisioning``, open its store set, import the sample (its file name and content),
        record it ``active`` (TPR-02 to TPR-04).

        Raises:
            ProvisioningError: For an alias that isn't index-safe, the operator organization's, a tenant already
                ``active`` or ``removing``, or a sample whose import failed.
        """  # noqa: D205 - one sentence
        _check_alias(alias, self._settings)
        existing = await self._tenants.get(alias)
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
        )
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
        await self._tenants.put(record.model_copy(update={"state": TenantState.ACTIVE, "updated_at": _now()}))
        self._out(f"Provisioned {alias}: indices {prefix}-*, {'sample ' + sample[0] if sample else 'no sample'}")

    async def trust(self, alias: str, *, trusts: bool) -> None:
        """Record whether a recorded tenant trusts the operators (TPR-03).

        Raises:
            ProvisioningError: For a tenant with no record.
        """
        record = await self._recorded(alias)
        await self._tenants.put(
            record.model_copy(update={"trusts_operators": trusts, "updated_at": _now(), "updated_by": self._who})
        )
        self._out(f"{alias} {'trusts' if trusts else 'does not trust'} the operators")

    async def list(self) -> None:
        """Write each recorded tenant: alias, state, trust and sample (TPR-06)."""
        for tenant in await self._tenants.list():
            trust = "trusts operators" if tenant.trusts_operators else "no operator trust"
            self._out(f"{tenant.alias}\t{tenant.state.value}\t{trust}\t{tenant.sample or '-'}")

    async def remove(self, alias: str) -> None:
        """Record the tenant ``removing``, wait out the servers' refresh, delete the indices behind its aliases and
        its record (TPR-05, DD-574).

        Raises:
            ProvisioningError: For the operator organization or a tenant with no record.
        """  # noqa: D205 - one sentence
        if alias == self._settings.tenancy_operator_organization:
            msg = f"{alias} is the operator organization, whose indices are the default ones"
            raise ProvisioningError(msg)
        record = await self._recorded(alias)
        removing = {"state": TenantState.REMOVING, "updated_at": _now(), "updated_by": self._who}
        await self._tenants.put(record.model_copy(update=removing))
        await self._sleep(self._settings.tenancy_refresh_seconds)
        client = self._store.client
        deleted: list[str] = []
        for name in store_aliases(tenant_prefix(alias)):
            if await client.indices.exists_alias(name=name):
                indices = sorted((await client.indices.get(index=name)).body)
                await client.indices.delete(index=",".join(indices))
                deleted += indices
        await self._tenants.delete(alias)
        self._out(f"Removed {alias}: {len(deleted)} indices deleted")

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

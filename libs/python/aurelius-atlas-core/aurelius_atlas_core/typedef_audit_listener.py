"""``TypeDefAuditListener``: an admin audit of each typedef change, one per kind of change (ADA-03).

``BufferedTypeDefAuditListener`` is the same for the models loaded at the start: it keeps each change's
entries and writes them all in one write (DD-316).
"""

from collections.abc import Sequence

from aurelius_atlas_model import codec
from aurelius_atlas_model.atlas_audit import AtlasAuditEntry, AuditOperation
from aurelius_atlas_model.typedef import AtlasBaseTypeDef, TypeCategory

from aurelius_atlas_core.atlas_audit_service import AtlasAuditService
from aurelius_atlas_core.typedef_change_listener import ChangedTypeDefs


class TypeDefAuditListener:
    """``TypeDefAuditListener``: the created, updated and deleted definitions each audited through ``audits``."""

    def __init__(self, audits: AtlasAuditService) -> None:
        self._audits = audits

    async def on_change(self, changed: ChangedTypeDefs) -> None:
        """``onChange``: an entry of each kind of the change, written as it is made (ADA-03)."""
        for operation, params, result, count in _audit_entries(changed):
            await self._audits.add(operation, params, result, count)


class BufferedTypeDefAuditListener(TypeDefAuditListener):
    """``TypeDefAuditListener`` held at the server's start, its entries written at the end in one write (DD-316).

    One write per change costs the store a refresh each (DD-237), minutes for Atlas's whole catalogue at the
    start, long enough for the container health check to give up. Every change is still told its entries, so
    the start's audit holds every definition the way a request's holds its own (ADA-03). After
    :meth:`flush`, the listener writes each later change as its parent does.
    """

    def __init__(self, audits: AtlasAuditService) -> None:
        super().__init__(audits)
        self._pending: list[AtlasAuditEntry] = []
        self._flushed = False

    async def on_change(self, changed: ChangedTypeDefs) -> None:
        """Keep ``changed``'s entries until :meth:`flush`, then write each change as it is made (ADA-03).

        The entry names the change's own time, as Atlas's does, though the write waits.
        """
        if self._flushed:
            await super().on_change(changed)
            return
        for operation, params, result, count in _audit_entries(changed):
            if (entry := self._audits.entry(operation, params, result, count)) is not None:
                self._pending.append(entry)

    async def flush(self) -> None:
        """Write every kept entry in one write, oldest first, and let later changes through (DD-316)."""
        entries, self._flushed, self._pending = self._pending, True, []
        await self._audits.add_all(entries)


def _audit_entries(changed: ChangedTypeDefs) -> list[tuple[AuditOperation, str, str, int]]:
    """The entry of each kind of the change: its parameters, result and count (ADA-03).

    The kinds are the parameters, the definitions by kind the result. An updated definition also created is
    left out, and the updated ones are taken once each, by name.
    """
    created = {str(typedef.name) for typedef in changed.created}
    updated: dict[str, AtlasBaseTypeDef] = {}
    for typedef in changed.updated:
        if str(typedef.name) not in created:
            updated.setdefault(str(typedef.name), typedef)
    return [
        entry
        for typedefs, operation in (
            (changed.created, AuditOperation.TYPE_DEF_CREATE),
            ([updated[name] for name in sorted(updated)], AuditOperation.TYPE_DEF_UPDATE),
            (changed.deleted, AuditOperation.TYPE_DEF_DELETE),
        )
        if (entry := _audit_entry(typedefs, operation)) is not None
    ]


def _audit_entry(
    typedefs: Sequence[AtlasBaseTypeDef], operation: AuditOperation
) -> tuple[AuditOperation, str, str, int] | None:
    """The operation, parameters, result and count of the definitions. None for no definitions."""
    if not typedefs:
        return None
    by_kind: dict[TypeCategory, list[AtlasBaseTypeDef]] = {}
    for typedef in typedefs:
        by_kind.setdefault(typedef.category, []).append(typedef)
    result = {kind.value: [typedef.to_json() for typedef in found] for kind, found in by_kind.items()}
    params = ",".join(kind.value for kind in by_kind)
    return operation, params, codec.dumps(result).decode(), len(typedefs)

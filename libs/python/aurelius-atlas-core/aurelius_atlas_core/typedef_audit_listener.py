"""``TypeDefAuditListener``: an admin audit of each typedef change, one per kind of change (ADA-03)."""

from aurelius_atlas_model import codec
from aurelius_atlas_model.atlas_audit import AuditOperation
from aurelius_atlas_model.typedef import AtlasBaseTypeDef, TypeCategory

from aurelius_atlas_core.atlas_audit_service import AtlasAuditService
from aurelius_atlas_core.typedef_change_listener import ChangedTypeDefs


class TypeDefAuditListener:
    """``TypeDefAuditListener``: the created, updated and deleted definitions each audited through ``audits``."""

    def __init__(self, audits: AtlasAuditService) -> None:
        self._audits = audits

    async def on_change(self, changed: ChangedTypeDefs) -> None:
        """``onChange``: ``TYPE_DEF_CREATE``, ``TYPE_DEF_UPDATE`` and ``TYPE_DEF_DELETE`` of what the change did; an
        updated definition also created is left out, and the updated ones are taken once each, by name (ADA-03).
        """  # noqa: D205 - one sentence
        created = {str(typedef.name) for typedef in changed.created}
        updated: dict[str, AtlasBaseTypeDef] = {}
        for typedef in changed.updated:
            if str(typedef.name) not in created:
                updated.setdefault(str(typedef.name), typedef)
        await self._audit(changed.created, AuditOperation.TYPE_DEF_CREATE)
        await self._audit([updated[name] for name in sorted(updated)], AuditOperation.TYPE_DEF_UPDATE)
        await self._audit(changed.deleted, AuditOperation.TYPE_DEF_DELETE)

    async def _audit(self, typedefs: list[AtlasBaseTypeDef], operation: AuditOperation) -> None:
        """``createAuditEntry``: the kinds as the parameters, the definitions by kind as the result, their count."""
        if not typedefs:
            return
        by_kind: dict[TypeCategory, list[AtlasBaseTypeDef]] = {}
        for typedef in typedefs:
            by_kind.setdefault(typedef.category, []).append(typedef)
        result = {kind.value: [typedef.to_json() for typedef in found] for kind, found in by_kind.items()}
        params = ",".join(kind.value for kind in by_kind)
        await self._audits.add(operation, params, codec.dumps(result).decode(), len(typedefs))

"""The admin audits through the client library, on the dev store (ADA-02, ADA-04, ADA-05, CL-11).

A purge audited and detailed, found by a search: the same routes the dashboard's admin screen rides,
answered through the typed client (CL-11) — the typed twin of the raw scenario calls.
"""

import uuid

import pytest
from aurelius_atlas_model.atlas_audit import AuditSearchParameters
from aurelius_atlas_model.discovery import Condition, FilterCriteria, Operator
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityWithExtInfo, EntityOperation
from aurelius_atlas_model.typedef import AtlasEntityDef, AtlasTypesDef
from aurelius_atlas_server_client import AtlasClient


def _typed_entity(type_name: str, qualified_name: str, name: str) -> AtlasEntityWithExtInfo:
    """The create body of one entity of ``type_name`` (ADA-02's seed)."""
    return AtlasEntityWithExtInfo(
        entity=AtlasEntity(type_name=type_name, attributes={"qualifiedName": qualified_name, "name": name})
    )


# impact=severe, likelihood=low (the spine path moves rarely between increments)
@pytest.mark.high
@pytest.mark.covers(
    "aurelius_atlas_server_client.client.AdminApi.audits",
    "aurelius_atlas_server_client.client.AdminApi.audit_details",
    "aurelius_atlas_server_client.client.AdminApi.purge",
    "aurelius_atlas_server.routes.admin.get_atlas_audits",
    "aurelius_atlas_server.routes.admin.get_audit_details",
    rules=["ADA-02", "ADA-04", "ADA-05", "CLW-11"],
)
async def test__a_purge_is_found_among_the_admin_audits_with_its_entity(api: AtlasClient) -> None:
    """The purge's entry, found by its parameters, details the purged entity."""
    run = uuid.uuid4().hex
    name = f"e2e_ada_{run}"
    await api.types.create_typedefs(AtlasTypesDef(entity_defs=[AtlasEntityDef(name=name, super_types=["DataSet"])]))
    created = await api.entity.create_or_update(_typed_entity(name, f"q_{run}", run))
    header = created.get_first_entity_by_operation(EntityOperation.CREATE)
    assert header is not None
    assert header.guid is not None
    guid = header.guid
    await api.entity.delete_by_guid(guid)
    await api.admin.purge([guid])

    criterion = FilterCriteria(attribute_name="params", operator=Operator.EQ, attribute_value=f"[{guid}]")
    asked = AuditSearchParameters(audit_filters=FilterCriteria(condition=Condition.AND, criterion=[criterion]), limit=5)
    found = await api.admin.audits(asked)
    [entry] = found
    details = await api.admin.audit_details(entry.guid)

    assert (entry.operation, entry.result, entry.result_count) == ("PURGE", guid, 1)
    assert [header.guid for header in details] == [guid]

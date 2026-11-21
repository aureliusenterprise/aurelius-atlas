"""The m4i metamodel the running server bootstraps, read through the client library (HCA-10, PME-05).

The dev store starts empty of the m4i types, so the server loads them itself at start-up. A new catalogue
answers every hierarchy child end as ``SINGLE``, the three without a parent group at type version ``1.1`` and
the six parent choices at ``1.2`` with their ``mutuallyExclusive`` constraint — each type read through
``types.typedef_by_name``, parsed into its category's model (CL-11).
"""

import pytest
from aurelius_atlas_model.typedef import AtlasRelationshipDef, AtlasRelationshipEndDef, TypeCategory
from aurelius_atlas_server_client import AtlasClient

HIERARCHIES = {
    "m4i_data_entity_attribute_assignment": "dataEntity",
    "m4i_system_parent_assignment": "parentSystem",
    "m4i_system_process_assignment": "system",
}
"""Each hierarchy relationship without a parent group and the child-end attribute that names its parent
(HCA-01)."""

PARENT_GROUPS = {
    "m4i_data_entity_assignment": ("dataDomain", "m4i_data_entity_parent"),
    "m4i_parent_entity_assignment": ("parentEntity", "m4i_data_entity_parent"),
    "m4i_field_assignment": ("datasets", "m4i_field_parent"),
    "m4i_field_parent_assignment": ("parentField", "m4i_field_parent"),
    "m4i_dataset_assignment": ("collections", "m4i_dataset_parent"),
    "m4i_dataset_parent_assignment": ("parentDataset", "m4i_dataset_parent"),
}
"""Each relationship with a parent group: the child-end attribute and the group its constraint names
(PME-04, PME-05, DCP-01)."""


def _ends(definition: AtlasRelationshipDef) -> dict[str, AtlasRelationshipEndDef]:
    """The relationship's two ends by attribute name, typed (HCA-01)."""
    ends: dict[str, AtlasRelationshipEndDef] = {}
    for end in (definition.end_def1, definition.end_def2):
        assert end is not None
        assert end.name is not None
        ends[end.name] = end
    return ends


# impact=severe, likelihood=low (a wrong child cardinality breaks every hierarchy write)
@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_server_client.client.TypesApi.typedef_by_name",
    "aurelius_atlas_server.routes.types.get_typedef_by_name",
    rules=["HCA-10", "CL-11"],
)
async def test__the_bootstrapped_metamodel_gives_every_hierarchy_child_one_parent(api: AtlasClient) -> None:
    """Every hierarchy child end the running server bootstraps is ``SINGLE`` at version ``1.1``."""
    for name, child in HIERARCHIES.items():
        definition = await api.types.typedef_by_name(name)
        assert isinstance(definition, AtlasRelationshipDef), name
        assert definition.category is TypeCategory.RELATIONSHIP, name
        assert definition.type_version == "1.1", name

        ends = _ends(definition)
        assert ends[child].cardinality == "SINGLE", name
        assert [end.cardinality for attribute, end in ends.items() if attribute != child] == ["SET"], name
        assert not any(end.constraints for end in ends.values()), name


# impact=severe, likelihood=low (a missing group lets an entity hold two parents again)
@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_server_client.client.TypesApi.typedef_by_name",
    "aurelius_atlas_server.routes.types.get_typedef_by_name",
    rules=["PME-04", "PME-05", "DCP-01", "CL-11"],
)
async def test__the_bootstrapped_metamodel_names_the_parent_groups(api: AtlasClient) -> None:
    """Each of the six parent-choice ends answers ``SINGLE`` at version ``1.2`` with its group."""
    for name, (child, group) in PARENT_GROUPS.items():
        definition = await api.types.typedef_by_name(name)
        assert isinstance(definition, AtlasRelationshipDef), name
        assert definition.type_version == "1.2", name

        ends = _ends(definition)
        assert ends[child].cardinality == "SINGLE", name
        assert [end.cardinality for attribute, end in ends.items() if attribute != child] == ["SET"], name
        constraint = next(iter(ends[child].constraints or []))
        assert (constraint.type, constraint.params) == ("mutuallyExclusive", {"group": group}), name

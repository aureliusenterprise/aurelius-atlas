"""The m4i metamodel the running server bootstraps, read over the API (HCA-10).

The dev store starts empty of the m4i types, so the server loads them itself at start-up. A new catalogue
answers every hierarchy child end as ``SINGLE`` at type version ``1.1``.
"""

import httpx2 as httpx
import pytest

TYPED = "/api/atlas/v2/types/typedef/name"

HIERARCHIES = {
    "m4i_data_entity_assignment": "dataDomain",
    "m4i_parent_entity_assignment": "parentEntity",
    "m4i_data_entity_attribute_assignment": "dataEntity",
    "m4i_field_assignment": "datasets",
    "m4i_field_parent_assignment": "parentField",
    "m4i_system_parent_assignment": "parentSystem",
    "m4i_system_process_assignment": "system",
    "m4i_dataset_parent_assignment": "parentDataset",
}
"""Each hierarchy relationship and the child-end attribute that names its parent (HCA-01)."""


# impact=severe, likelihood=low (a wrong child cardinality breaks every hierarchy write)
@pytest.mark.critical
@pytest.mark.covers("aurelius_atlas_server.routes.types.get_typedef_by_name", rules=["HCA-10"])
async def test__the_bootstrapped_metamodel_gives_every_hierarchy_child_one_parent(client: httpx.AsyncClient) -> None:
    """Every hierarchy child end the running server bootstraps is ``SINGLE`` at version ``1.1``."""
    for name, child in HIERARCHIES.items():
        definition = (await client.get(f"{TYPED}/{name}")).json()

        assert definition["typeVersion"] == "1.1", name
        ends = {end["name"]: end for end in [definition["endDef1"], definition["endDef2"]]}
        assert ends[child]["cardinality"] == "SINGLE", name
        assert [end["cardinality"] for end in ends.values() if end["name"] != child] == ["SET"], name

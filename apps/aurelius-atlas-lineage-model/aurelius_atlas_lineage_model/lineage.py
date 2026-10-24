"""The flattening and the fixed rules document (LM-02..LM-04), on the client library's models.

The lineage body models — ``LineageInfo``, ``EntityHeaderLite``, ``LineageRelation``,
``Direction`` — moved to ``aurelius-atlas-server-client`` by increment 8.4 (DD-203,
CL-12): they are the ``v2/lineage/{guid}`` contract of the Atlas API. This module
re-exports them so the app's import path stays, and keeps what the app *is*: the
flattening (``flatten_relations``, ``PROCESS_TYPES``) and the fixed rules document
(``LINEAGE_RULES``) the legacy chain posted — 8.2's logic, not a contract.

The reference is the Aurelius source: ``fmt_lineage_relation``, the ``rules``
dict and ``process_types`` in
``backend/m4i-lineage-model/m4i_lineage_model/lineage_model.py``.
Per DD-198 the models are pydantic (the upstream JSON is parsed at the
boundary), the rows are plain dicts, and no pandas is involved.
"""

from typing import Any

from aurelius_atlas_server_client.lineage import Direction, EntityHeaderLite, LineageInfo, LineageRelation

from aurelius_atlas_lineage_model.errors import UpstreamError

__all__ = [
    "LINEAGE_RULES",
    "PROCESS_TYPES",
    "Direction",
    "EntityHeaderLite",
    "LineageInfo",
    "LineageRelation",
    "UpstreamError",
    "flatten_relations",
]

PROCESS_TYPES: frozenset[str] = frozenset(
    {
        "m4i_generic_process",
        "m4i_api_operation_process",
        "m4i_connector_process",
        "m4i_ingress_controller_process",
        "m4i_ingress_object_process",
        "m4i_kubernetes_service_process",
        "m4i_microservice_process",
    }
)
"""The legacy ``process_types`` list, ported verbatim (LM-03): a lineage endpoint
whose type name is in this family is a process, every other type an entity."""


def _endpoint_slots(prefix: str, header: EntityHeaderLite | None) -> dict[str, Any]:
    """The four ``*_entity_*``/``*_process_*`` slots of one relation endpoint (LM-02).

    A process fills its ``*_process_*`` slots and nulls its ``*_entity_*`` ones;
    every other type is the mirror. A missing header is the legacy's ``KeyError``:
    an upstream that names a guid its own map does not carry is a gateway
    failure (LM-07), not a row of nulls.
    """
    if header is None:
        raise UpstreamError(502, "lineage references an entity the upstream did not describe")
    is_process = header.type_name in PROCESS_TYPES
    slots = {"id": header.guid, "name": header.display_text, "type": header.type_name}
    kind = "process" if is_process else "entity"
    other = "entity" if is_process else "process"
    return {
        **{f"{prefix}_{kind}_{slot}": value for slot, value in slots.items()},
        **{f"{prefix}_{other}_{slot}": None for slot in slots},
    }


def flatten_relations(info: LineageInfo) -> list[dict[str, Any]]:
    """One 12-column archimate row per lineage relation, in upstream order (LM-02)."""
    rows: list[dict[str, Any]] = []
    for relation in info.relations:
        source = info.guid_entity_map.get(relation.from_entity_id)
        target = info.guid_entity_map.get(relation.to_entity_id)
        rows.append(
            {"id": relation.relationship_id, **_endpoint_slots("from", source), **_endpoint_slots("to", target)}
        )
    return rows


LINEAGE_RULES: dict[str, Any] = {
    "elements": [
        {
            "id": "5e18c7eb-f4f5-4587-a159-3ac3412080cf",
            "alias": "Element rule for column from_entity_id",
            "description": "This rule generates a new element for every from_entity_id in the dataset",
            "concept_type": "lineage_dataset",
            "id_type": "dynamic",
            "id_key": "from_entity_id",
            "concept_name_key": "from_entity_name",
            "concept_name_prefix": None,
            "concept_label_key": None,
            "concept_label_prefix": None,
            "mapping": [{"key": "Type name", "value": "from_entity_type"}],
            "include": True,
            "type": "element",
        },
        {
            "id": "90903dfd-6f1e-4f5f-a174-264524d9e3cc",
            "alias": "Element rule for column to_process_id",
            "description": "This rule generates a new element for every to_process_id in the dataset",
            "concept_type": "lineage_process",
            "id_type": "dynamic",
            "id_key": "to_process_id",
            "concept_name_key": "to_process_name",
            "concept_name_prefix": None,
            "concept_label_key": None,
            "concept_label_prefix": None,
            "mapping": [{"key": "Type name", "value": "to_process_type"}],
            "include": True,
            "type": "element",
        },
        {
            "id": "457c347e-0689-4b65-92db-2f8e23c4fb5f",
            "alias": "Element rule for column from_process_id",
            "description": "This rule generates a new element for every from_process_id in the dataset",
            "concept_type": "lineage_process",
            "id_type": "dynamic",
            "id_key": "from_process_id",
            "concept_name_key": "from_process_name",
            "concept_name_prefix": None,
            "concept_label_key": None,
            "concept_label_prefix": None,
            "mapping": [{"key": "Type name", "value": "from_process_type"}],
            "include": True,
            "type": "element",
        },
        {
            "id": "b85e49ca-9d5a-465b-ada2-7640f370b10a",
            "alias": "Element rule for column to_entity_id",
            "description": "This rule generates a new element for every to_entity_id in the dataset",
            "concept_type": "lineage_dataset",
            "id_type": "dynamic",
            "id_key": "to_entity_id",
            "concept_name_key": "to_entity_name",
            "concept_name_prefix": None,
            "concept_label_key": None,
            "concept_label_prefix": None,
            "mapping": [{"key": "Type name", "value": "to_entity_type"}],
            "include": True,
            "type": "element",
        },
    ],
    "relations": [
        {
            "id": "57aa2001-a458-4cb7-8460-aa4a35ea9b9a",
            "type": "relation",
            "alias": "Relationship rule between from_entity_id and to_process_id",
            "description": "This rule generates a new relationship between from_entity_id and to_process_id",
            "include": True,
            "relationship_type": "lr",
            "id_type": "dynamic",
            "id_key": "id",
            "id_value": ["from_entity_id", "to_process_id"],
            "relationship_name_type": "dynamic",
            "relationship_name_key": "",
            "relationship_label_type": "dynamic",
            "relationship_label_key": "",
            "target": "90903dfd-6f1e-4f5f-a174-264524d9e3cc",
            "source": "5e18c7eb-f4f5-4587-a159-3ac3412080cf",
        },
        {
            "id": "6a57fd4e-243f-4021-a8c5-9a92f212f97a",
            "type": "relation",
            "alias": "Relationship rule between from_process_id and to_entity_id",
            "description": "This rule generates a new relationship between from_process_id and to_entity_id",
            "include": True,
            "relationship_type": "lr",
            "id_type": "dynamic",
            "id_key": "id",
            "id_value": ["from_process_id", "to_entity_id"],
            "relationship_name_type": "dynamic",
            "relationship_name_key": "",
            "relationship_label_type": "dynamic",
            "relationship_label_key": "",
            "target": "b85e49ca-9d5a-465b-ada2-7640f370b10a",
            "source": "457c347e-0689-4b65-92db-2f8e23c4fb5f",
        },
    ],
    "views": [
        {
            "id": "view_6008d024-5a7b-4581-b664-f463ece7a40b",
            "type": "view",
            "alias": "View rule for lineage overview",
            "description": "This rule generates the lineage overview",
            "include": True,
            "id_type": "static",
            "id_key": None,
            "id_value": "lineage_view",
            "view_name_type": "static",
            "view_name_key": None,
            "view_name_value": "Lineage",
            "view_layout": "archimate_process",
            "view_nodes": [
                {"rule": "457c347e-0689-4b65-92db-2f8e23c4fb5f"},
                {"rule": "b85e49ca-9d5a-465b-ada2-7640f370b10a"},
                {"rule": "5e18c7eb-f4f5-4587-a159-3ac3412080cf"},
                {"rule": "90903dfd-6f1e-4f5f-a174-264524d9e3cc"},
            ],
            "view_edges": [],
        }
    ],
}
"""The fixed extraction rules of the legacy service, ported verbatim (LM-04).

The lineage chain's `rules` document for data2model ``/extract`` (the legacy
wrapped it as ``{"rules": …}`` and splatted it into the body): four element
rules (the entity/process id columns), two ``lr`` relation rules, and one
static ``lineage_view``/``Lineage`` view with the archimate_process layout.
The ids are the legacy's — the webapp's saved model references depend on them.
"""

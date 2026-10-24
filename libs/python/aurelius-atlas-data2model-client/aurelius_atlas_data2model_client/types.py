"""The Archimate 3.0 concept types a rule may name (DTM-11), ported from ``m4i-analytics``.

The legacy ``ElementType`` / ``RelationshipType`` enums (``metamodel/Concepts.py``) are
tables of data; the port keeps the two columns the extractor needs — the ar3 ``@xsi_type``
tag, and for elements the layer that organises them (``ArchimateModel.organize``) and for
relationships the type attributes the ar3 writer emits — and drops the enum machinery.

The tables are the request contract's validation domain (DTM-11), so they live with the
contract in this library (CL-20, DD-203); the ar3 writer's layout constants stayed in the
app's engine.
"""

ELEMENT_TYPE_LAYERS: dict[str, str] = {
    # The ar3 tag of each element type, to its Archimate layer (legacy ElementType).
    "ar3_AndJunction": "Other",
    "ar3_ApplicationCollaboration": "Application",
    "ar3_ApplicationComponent": "Application",
    "ar3_ApplicationEvent": "Application",
    "ar3_ApplicationFunction": "Application",
    "ar3_ApplicationInteraction": "Application",
    "ar3_ApplicationInterface": "Application",
    "ar3_ApplicationProcess": "Application",
    "ar3_ApplicationService": "Application",
    "ar3_Artifact": "Technology",
    "ar3_Assessment": "Motivation",
    "ar3_BusinessActor": "Business",
    "ar3_BusinessCollaboration": "Business",
    "ar3_BusinessEvent": "Business",
    "ar3_BusinessFunction": "Business",
    "ar3_BusinessInteraction": "Business",
    "ar3_BusinessInterface": "Business",
    "ar3_BusinessObject": "Business",
    "ar3_BusinessProcess": "Business",
    "ar3_BusinessRole": "Business",
    "ar3_BusinessService": "Business",
    "ar3_Capability": "Strategy",
    "ar3_CommunicationNetwork": "Technology",
    "ar3_Constraint": "Motivation",
    "ar3_Contract": "Business",
    "ar3_CourseOfAction": "Strategy",
    "ar3_DataObject": "Application",
    "ar3_Deliverable": "Implementation & Migration",
    "ar3_Device": "Technology",
    "ar3_DistributionNetwork": "Physical",
    "ar3_Driver": "Motivation",
    "ar3_Equipment": "Physical",
    "ar3_Facility": "Physical",
    "ar3_Gap": "Implementation & Migration",
    "ar3_Goal": "Motivation",
    "ar3_Grouping": "Composite",
    "ar3_ImplementationEvent": "Implementation & Migration",
    "ar3_Junction": "Other",
    "ar3_Location": "Composite",
    "ar3_Material": "Physical",
    "ar3_Meaning": "Motivation",
    "ar3_Node": "Technology",
    "ar3_OrJunction": "Other",
    "ar3_Outcome": "Motivation",
    "ar3_Path": "Technology",
    "ar3_Plateau": "Implementation & Migration",
    "ar3_Principle": "Motivation",
    "ar3_Product": "Business",
    "ar3_Representation": "Business",
    "ar3_Requirement": "Motivation",
    "ar3_Resource": "Strategy",
    "ar3_Stakeholder": "Motivation",
    "ar3_SystemSoftware": "Technology",
    "ar3_TechnologyCollaboration": "Technology",
    "ar3_TechnologyEvent": "Technology",
    "ar3_TechnologyFunction": "Technology",
    "ar3_TechnologyInteraction": "Technology",
    "ar3_TechnologyInterface": "Technology",
    "ar3_TechnologyProcess": "Technology",
    "ar3_TechnologyService": "Technology",
    "ar3_Unknown": "Other",
    "ar3_Value": "Motivation",
    "ar3_ValueStream": "Strategy",
    "ar3_WorkPackage": "Implementation & Migration",
    "lineage_dataset": "Other",
    "lineage_process": "Other",
}
"""Element type tag → layer; the tags a rule's ``concept_type`` may name (the lineage chain uses the last pair)."""

RELATIONSHIP_SHORTHANDS: dict[str, tuple[str, dict[str, str]]] = {
    # The shorthand of each relationship type (legacy RelationshipType), to its ar3 tag and attributes.
    "a": ("ar3_Access", {}),
    "aa": ("ar3_Access", {"accessType": "Access"}),
    "ar": ("ar3_Access", {"accessType": "Read"}),
    "aw": ("ar3_Access", {"accessType": "Write"}),
    "arw": ("ar3_Access", {"accessType": "ReadWrite"}),
    "g": ("ar3_Aggregation", {}),
    "i": ("ar3_Assignment", {}),
    "o": ("ar3_Association", {}),
    "do": ("ar3_Association", {"isDirected": "true"}),
    "c": ("ar3_Composition", {}),
    "f": ("ar3_Flow", {}),
    "n": ("ar3_Influence", {}),
    "lr": ("lineage_relation", {}),
    "r": ("ar3_Realization", {}),
    "v": ("ar3_Serving", {}),
    "s": ("ar3_Specialization", {}),
    "t": ("ar3_Triggering", {}),
}
"""Relationship shorthand → (ar3 tag, ar3 attributes).

The shorthands a rule's ``relationship_type`` may name.
"""

LAYOUT_NAMES = frozenset({"archimate_process", "archimate_hierarchical"})
"""The view layouts the legacy registry knew (``m4i-graphviz-layouts``).

A view with any other layout is ignored (DTM-06).
"""

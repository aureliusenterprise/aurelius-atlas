"""The ar3 writer's layout constants (DTM-08, DTM-09) — the extraction engine's own (DD-114).

The contract's validation tables (``ELEMENT_TYPE_LAYERS``, ``RELATIONSHIP_SHORTHANDS``,
``LAYOUT_NAMES``) moved to ``aurelius-atlas-data2model-client`` with the rule models
in increment 8.4; the numbers the ar3 writer lays a view out stayed with the engine.
"""

NODE_WIDTH = 120
"""The ar3 node width (``generate_view``'s ``node_width``)."""

NODE_HEIGHT = 55
"""The ar3 node height (``generate_view``'s ``node_height``)."""

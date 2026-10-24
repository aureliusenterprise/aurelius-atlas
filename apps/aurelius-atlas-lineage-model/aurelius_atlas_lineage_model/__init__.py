"""The Aurelius Atlas lineage-model API (increment 8.2, ADR 055).

An entity guid in, the lineage graph's archimate model out — the flattening
proxy the legacy lineage screen called, ported from ``m4i-lineage-model``:
Atlas lineage in, archimate rows out, handed to data2model ``/extract``
(8.1) with the caller's token.
"""

from aurelius_atlas_lineage_model.app import create_app
from aurelius_atlas_lineage_model.settings import LineageModelSettings

__all__ = ["LineageModelSettings", "create_app"]

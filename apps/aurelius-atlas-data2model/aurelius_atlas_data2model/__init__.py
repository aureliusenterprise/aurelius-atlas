"""The Aurelius Atlas data2model API (increment 8.1, ADR 055).

Tabular data plus element/relation/view rules in, an archimate3 model string
out — the model-extraction API the legacy lineage graph drew on, ported from
``m4i-data2model`` without pandas (DD-198).
"""

from aurelius_atlas_data2model.app import create_app
from aurelius_atlas_data2model.settings import Data2ModelSettings

__all__ = ["Data2ModelSettings", "create_app"]

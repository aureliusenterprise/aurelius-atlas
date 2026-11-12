"""The Aurelius Atlas validate-entity API (increment 8.3, ADR 055; 12.7, ADR 061).

An entity draft in, the governance verdicts out — the validation endpoint the
legacy editor called, ported from ``m4i-validate-entity``. The legacy service
was a mock (DV-67); since 12.7 the app reads the ACTIVE governance rules from
the catalogue and runs them over the draft (VEV-01..06, DV-153): the answer is
the draft's real verdicts, with the workspace's auth and observability.
"""

from aurelius_atlas_validate_entity.app import create_app
from aurelius_atlas_validate_entity.settings import ValidateEntitySettings

__all__ = ["ValidateEntitySettings", "create_app"]

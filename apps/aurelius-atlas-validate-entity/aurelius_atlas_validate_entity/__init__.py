"""The Aurelius Atlas validate-entity API (increment 8.3, ADR 055).

An entity in, the fixed governance-quality mock out — the validation
endpoint the legacy editor called, ported from ``m4i-validate-entity``.
The legacy service is a mock (DV-14): the body is ignored and the answer is
a constant; the port keeps that browser contract, with the workspace's auth
and observability.
"""

from aurelius_atlas_validate_entity.app import create_app
from aurelius_atlas_validate_entity.settings import ValidateEntitySettings

__all__ = ["ValidateEntitySettings", "create_app"]

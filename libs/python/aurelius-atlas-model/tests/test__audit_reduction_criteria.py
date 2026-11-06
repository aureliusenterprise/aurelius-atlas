"""The aging criteria (AGE-01), as Apache Atlas 2.4.0's ``AuditReductionCriteria`` reads them."""

import pytest
from aurelius_atlas_model.audit_reduction import AtlasAuditAgingType, AuditReductionCriteria


@pytest.mark.covers(rules=["AGE-01"])
def test__the_criteria_read_atlas_json() -> None:
    """Java's names, ``TTL`` in capitals; nulls read as Java's defaults; the three aging types."""
    criteria = AuditReductionCriteria.model_validate(
        {
            "auditAgingEnabled": True,
            "ignoreDefaultAgeoutTTL": True,
            "defaultAgeoutTTLInDays": None,
            "customAgeoutTTLInDays": 9,
            "sweepoutActionTypes": "TAG_*",
        }
    )

    assert (criteria.audit_aging_enabled, criteria.ignore_default_ageout_ttl) == (True, True)
    assert (criteria.default_ageout_ttl_in_days, criteria.custom_ageout_ttl_in_days) == (0, 9)
    assert criteria.sub_types_included
    assert criteria.to_json()["customAgeoutTTLInDays"] == 9
    assert [aging.value for aging in AtlasAuditAgingType] == ["DEFAULT", "CUSTOM", "SWEEP"]

"""The caller's tenant (VET-01): the one organization its token names, read as the server reads it (TEN-02)."""

import pytest
from aurelius_atlas_validate_entity.tenancy import tenant_of


@pytest.mark.covers("aurelius_atlas_validate_entity.tenancy.tenant_of", rules=["VET-01"])
@pytest.mark.parametrize(
    ("claims", "tenant"),
    [
        ({"organization": ["demo"]}, "demo"),
        ({"organization": {"demo": {"groups": ["/atlas-read"]}}}, "demo"),
        ({}, None),
        ({"organization": []}, None),
        ({"organization": ["demo", "meyn"]}, None),
        ({"organization": "demo"}, None),
    ],
    ids=["list", "object", "no-claim", "empty", "several", "other-shape"],
)
def test__the_tenant_is_the_one_organization_the_token_names(claims: dict[str, object], tenant: str | None) -> None:
    """One organization, as a list or an object, is the tenant; none, several or another shape is no tenant."""
    assert tenant_of(claims) == tenant

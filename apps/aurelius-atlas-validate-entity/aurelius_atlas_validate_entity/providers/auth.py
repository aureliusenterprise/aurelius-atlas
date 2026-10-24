"""The auth factory: the app's Keycloak verifier (VE-03, DD-197)."""

import httpx2 as httpx
from aurelius_atlas_auth import AuthConfig, KeycloakAuth

from aurelius_atlas_validate_entity.settings import ValidateEntitySettings


def build_auth(settings: ValidateEntitySettings, http: httpx.Client | None = None) -> KeycloakAuth:
    """The app's token verifier, mapped from the settings (VE-03).

    The shared ``aurelius-atlas-auth`` library does the verification (DD-197);
    the issuer's JWKS is its own guarded call (AUX-02). The route takes the
    verifier from the composition root, so tests inject a fake-issuer one
    here; the library's ``http`` seam stays open for tests that stand in for
    the issuer calls (DD-200's seam, DD-209).
    """
    return KeycloakAuth(
        AuthConfig(
            server_url=str(settings.auth_server_url),
            realm=settings.auth_realm,
            audience=settings.auth_audience,
            ca_file=str(settings.auth_ca_file) if settings.auth_ca_file else None,
        ),
        http=http,
    )

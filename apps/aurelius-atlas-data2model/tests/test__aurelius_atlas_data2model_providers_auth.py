"""Unit tests for the auth factory: the verifier the settings describe (DTM-10, DD-108)."""

from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_data2model.providers.auth import build_auth
from aurelius_atlas_data2model.settings import Data2ModelSettings


@pytest.mark.covers("aurelius_atlas_data2model.providers.auth.build_auth", rules=["DTM-10"])
def test__the_verifier_is_the_issuer_the_settings_name(settings: Data2ModelSettings) -> None:
    """The verifier points at the settings' issuer, realm and audience (the app has no issuer of its own)."""
    auth = build_auth(settings)
    try:
        assert auth.base_url == "http://issuer.test/realms/master"
        assert auth.config.audience == "aurelius-atlas-data2model"
        assert auth.config.ca_file is None  # unset means the system trust store
    finally:
        auth.close()


@pytest.mark.covers("aurelius_atlas_data2model.providers.auth.build_auth", rules=["DTM-10"])
def test__the_ca_reaches_the_verifier(settings: Data2ModelSettings, tmp_path: Path) -> None:
    """A configured issuer CA travels to the verifier (the dev deployment's TLS issuer)."""
    ca = tmp_path / "ca.pem"
    ca.write_text("ca\n")
    with_ca = settings.model_copy(update={"auth_ca_file": ca})

    auth = build_auth(with_ca, http=httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(404))))
    try:
        assert auth.config.ca_file == str(ca)
    finally:
        auth.close()

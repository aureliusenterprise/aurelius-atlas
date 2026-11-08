"""Unit tests for the auth factory: the verifier the settings describe (LM-08, DD-197)."""

from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_lineage_model.providers.auth import build_auth
from aurelius_atlas_lineage_model.settings import LineageModelSettings


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.auth.build_auth", rules=["LM-08"])
def test__the_verifier_is_the_issuer_the_settings_name(settings: LineageModelSettings) -> None:
    """The verifier points at the settings' issuer, realm and audience (the app has no issuer of its own)."""
    auth = build_auth(settings)
    try:
        assert auth.base_url == "http://issuer.test/realms/master"
        assert auth.config.audience == "aurelius-atlas-lineage-model"
        assert auth.config.ca_file is None  # unset means the system trust store
    finally:
        auth.close()


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.auth.build_auth", rules=["LM-08"])
def test__the_extra_audiences_reach_the_verifier(settings: LineageModelSettings) -> None:
    """The settings' extra audiences join the verifier's accepted set (DD-385, AUT-10).

    The app's own client stays the audience — the union holds both, which is
    what lets the deployment keep its service identity and still take the
    browser's token the chain forwards (LM-04).
    """
    with_extra = settings.model_copy(update={"auth_extra_audiences": ["aurelius"]})

    auth = build_auth(with_extra, http=httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(404))))
    try:
        assert auth.config.audience == "aurelius-atlas-lineage-model"
        assert auth.config.audiences == {"aurelius-atlas-lineage-model", "aurelius"}
    finally:
        auth.close()


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.auth.build_auth", rules=["LM-08"])
def test__the_ca_reaches_the_verifier(settings: LineageModelSettings, tmp_path: Path) -> None:
    """A configured issuer CA travels to the verifier (the dev deployment's TLS issuer)."""
    ca = tmp_path / "ca.pem"
    ca.write_text("ca\n")
    with_ca = settings.model_copy(update={"auth_ca_file": ca})

    auth = build_auth(with_ca, http=httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(404))))
    try:
        assert auth.config.ca_file == str(ca)
    finally:
        auth.close()

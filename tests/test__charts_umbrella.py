"""Chart-contract suite for the umbrella's trust + credentials (CHT-19, 10.2).

The two joins the umbrella owns: the issuer every Certificate references
(DD-243) and the generated credentials the stateful workloads consume
(DD-244/DD-254). The component charts' own shapes are asserted at their own
renders (``test__charts_elasticsearch``/``test__charts_keycloak``); here the
umbrella composes them with the issuer and secrets under the CI test values.
"""

import base64
from typing import Any

import pytest
from conftest import UMBRELLA_CHART, find, find_all, helm_render, names

TEST_VALUES = (UMBRELLA_CHART / "tests/values.test.yaml",)


@pytest.mark.covers(rules=["CHT-19"])
def test__create_issuer_renders_the_ca_chain(umbrella_docs: list[dict[str, Any]]) -> None:
    """CreateIssuer renders bootstrap Issuer + CA Certificate + CA Issuer (DD-259).

    One CA for every leaf: the bare self-signed ClusterIssuer this replaced
    gave each Certificate its own private root, so no consumer could verify
    a peer. The chain is namespaced — a ClusterIssuer cannot read the CA
    Secret the chart writes into the app namespace. cert-manager itself is
    a cluster prerequisite, never installed here.
    """
    bootstrap = find(umbrella_docs, "Issuer", "aurelius-atlas-selfsigned-bootstrap")
    assert bootstrap["spec"] == {"selfSigned": {}}
    assert bootstrap["metadata"]["namespace"] == "atlas"
    root = find(umbrella_docs, "Certificate", "aurelius-atlas-selfsigned-ca")
    assert root["spec"]["isCA"] is True
    assert root["spec"]["secretName"] == "aurelius-atlas-selfsigned-ca"
    assert root["spec"]["issuerRef"]["name"] == "aurelius-atlas-selfsigned-bootstrap"
    assert root["spec"]["issuerRef"]["kind"] == "Issuer"
    ca = find(umbrella_docs, "Issuer", "aurelius-atlas-selfsigned")
    assert ca["spec"] == {"ca": {"secretName": "aurelius-atlas-selfsigned-ca"}}
    assert "ClusterIssuer" not in {d["kind"] for d in umbrella_docs}
    assert not (names(umbrella_docs, "Deployment") & {"cert-manager"})


@pytest.mark.covers(rules=["CHT-19"])
def test__bring_your_own_issuer_installs_the_external_ca() -> None:
    """CreateIssuer off renders no issuer chain; caBundle becomes the CA Secret."""
    docs = helm_render(
        UMBRELLA_CHART,
        value_files=TEST_VALUES,
        sets=("global.trust.createIssuer=false", "global.trust.caBundle=-----FAKE-CA-PEM-----"),
    )
    assert not {"Issuer", "ClusterIssuer"} & {d["kind"] for d in docs}
    assert not {c["metadata"]["name"] for c in find_all(docs, "Certificate")} & {"aurelius-atlas-selfsigned-ca"}
    ca = find(docs, "Secret", "aurelius-atlas-selfsigned-ca")
    assert base64.b64decode(ca["data"]["ca.crt"]).decode() == "-----FAKE-CA-PEM-----"


@pytest.mark.covers(rules=["CHT-19"])
def test__certificates_reference_the_umbrella_issuer(umbrella_docs: list[dict[str, Any]]) -> None:
    """Every workload Certificate points at the umbrella's CA Issuer (DD-243/259)."""
    certs = find_all(umbrella_docs, "Certificate")
    assert {c["metadata"]["name"] for c in certs} == {
        "aurelius-atlas-selfsigned-ca",
        "atlas-elasticsearch",
        "atlas-keycloak",
        "atlas-keycloak-postgres",
    }
    for cert in certs:
        if cert["metadata"]["name"] == "aurelius-atlas-selfsigned-ca":
            continue  # the root signs against the bootstrap, by chain design
        assert cert["spec"]["issuerRef"]["name"] == "aurelius-atlas-selfsigned"
        assert cert["spec"]["issuerRef"]["kind"] == "Issuer"


@pytest.mark.covers(rules=["CHT-19"])
def test__five_generated_secrets_with_expected_keys(umbrella_docs: list[dict[str, Any]]) -> None:
    """The five secrets 10.2's workloads consume, with the keys they read."""
    secrets = {s["metadata"]["name"]: s for s in find_all(umbrella_docs, "Secret")}
    expected = {
        "atlas-elasticsearch": {"elastic-password"},
        "atlas-keycloak-admin": {"user", "password"},
        "atlas-keycloak-database": {"user", "password"},
        "atlas-keycloak-users": {"writer-password", "reader-password"},
        "atlas-otel-clients": {"OTEL_INGEST_CLIENT_SECRET"},
    }
    assert expected.keys() <= secrets.keys()
    for name, keys in expected.items():
        assert set(secrets[name]["data"]) == keys, name
    # Generated credentials are 32 random chars (b64 >= 44); the usernames are
    # short values by design, so only the secret-bearing keys are length-checked.
    for name in ("atlas-elasticsearch", "atlas-keycloak-users", "atlas-otel-clients"):
        assert all(len(v) >= 44 for v in secrets[name]["data"].values()), name
    for name in ("atlas-keycloak-admin", "atlas-keycloak-database"):
        assert len(secrets[name]["data"]["password"]) >= 44, name


@pytest.mark.covers(rules=["CHT-19"])
def test__supplied_values_win_over_generation() -> None:
    """A credential supplied in values appears verbatim, not regenerated."""
    docs = helm_render(
        UMBRELLA_CHART,
        value_files=TEST_VALUES,
        sets=("secrets.elasticsearch.password=supplied-pw",),
    )
    secret = find(docs, "Secret", "atlas-elasticsearch")
    assert secret["data"]["elastic-password"] == "c3VwcGxpZWQtcHc="


@pytest.mark.covers(rules=["CHT-19"])
def test__secrets_gate_with_their_consumers() -> None:
    """Disabling a consumer chart stops generating its credentials."""
    docs = helm_render(
        UMBRELLA_CHART,
        value_files=TEST_VALUES,
        sets=("atlas-keycloak.enabled=false",),
    )
    secret_names = names(docs, "Secret")
    assert not {n for n in secret_names if n.startswith("atlas-keycloak") or n.endswith("otel-clients")}
    assert "atlas-elasticsearch" in secret_names

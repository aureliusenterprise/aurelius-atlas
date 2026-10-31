"""Chart-contract suite for the umbrella's trust + credentials (CHT-19, 10.2).

The two joins the umbrella owns: the issuer every Certificate references
(DD-243) and the generated credentials the stateful workloads consume
(DD-244/DD-254). The component charts' own shapes are asserted at their own
renders (``test__charts_elasticsearch``/``test__charts_keycloak``); here the
umbrella composes them with the issuer and secrets under the CI test values.
"""

import base64
import json
import re
from typing import Any

import pytest
import yaml
from conftest import (
    OTEL_CLIENT_IDS,
    PINNED,
    UMBRELLA_CHART,
    container,
    env_map,
    find,
    find_all,
    helm_render,
    names,
)

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
        "atlas-server",
        "atlas-webapp",  # the listener leaf the BackendTLSPolicy validates (DD-270)
        "atlas-data2model",
        "atlas-lineage-model",
        "atlas-validate-entity",
        "atlas-observability",  # the collector's cluster-names-only leaf (CHT-36)
        "atlas-edge-tls",  # the browser-facing edge leaf (CHT-29)
    }
    for cert in certs:
        if cert["metadata"]["name"] == "aurelius-atlas-selfsigned-ca":
            continue  # the root signs against the bootstrap, by chain design
        assert cert["spec"]["issuerRef"]["name"] == "aurelius-atlas-selfsigned"
        assert cert["spec"]["issuerRef"]["kind"] == "Issuer"


@pytest.mark.covers(rules=["CHT-19", "CHT-80", "CHT-88"])
def test__generated_secrets_with_expected_keys(umbrella_docs: list[dict[str, Any]]) -> None:
    """The secrets 10.2's workloads consume, with the keys they read.

    The demo-user Secret is the master realm's (CHT-80): the stock render —
    the hardened aurelius-atlas realm — generates no demo passwords.
    CHT-88 (DD-277): the otel-clients Secret is realm-shaped — one key per
    client id on the prod realm, each independently generated; master keeps
    the single shared OTEL_INGEST_CLIENT_SECRET key.
    """
    secrets = {s["metadata"]["name"]: s for s in find_all(umbrella_docs, "Secret")}
    expected = {
        "atlas-elasticsearch": {"elastic-password"},
        "atlas-keycloak-admin": {"user", "password"},
        "atlas-keycloak-database": {"user", "password"},
        "atlas-otel-clients": set(OTEL_CLIENT_IDS),  # CHT-88: realm-shaped keys
        "atlas-grafana-oauth": {"client-secret"},  # CHT-83: feeds the realm import and Grafana
    }
    assert "atlas-keycloak-users" not in secrets
    assert expected.keys() <= secrets.keys()
    for name, keys in expected.items():
        assert set(secrets[name]["data"]) == keys, name
    # Generated credentials are 32 random chars (b64 >= 44); the usernames are
    # short values by design, so only the secret-bearing keys are length-checked.
    for name in ("atlas-elasticsearch", "atlas-otel-clients"):
        assert all(len(v) >= 44 for v in secrets[name]["data"].values()), name
    for name in ("atlas-keycloak-admin", "atlas-keycloak-database"):
        assert len(secrets[name]["data"]["password"]) >= 44, name
    # The per-client values are independently random (DD-277's rotation rule):
    # no two keys may share a generated value.
    values = list(secrets["atlas-otel-clients"]["data"].values())
    assert len(set(values)) == len(values)

    master_docs = helm_render(
        UMBRELLA_CHART,
        value_files=(UMBRELLA_CHART / "tests/values.test.yaml",),
        sets=("atlas-keycloak.realm.name=master",),
    )
    master_secrets = {s["metadata"]["name"]: s for s in find_all(master_docs, "Secret")}
    users = master_secrets["atlas-keycloak-users"]
    assert set(users["data"]) == {"writer-password", "reader-password"}
    assert all(len(v) >= 44 for v in users["data"].values())
    # master's asset shares one placeholder: the Secret keeps the one key.
    assert set(master_secrets["atlas-otel-clients"]["data"]) == {"OTEL_INGEST_CLIENT_SECRET"}
    # The master realm has no grafana client (CHT-81); the stock render's
    # grafana-oauth rides the observability chart, so master keeps it (its
    # Grafana still logs in) — a master-only install with obs off is the
    # case with no consumer (test__grafana_oauth_secret_gates_on_consumers).
    assert "atlas-grafana-oauth" in master_secrets


@pytest.mark.covers(rules=["CHT-88"])
def test__otel_client_secret_keys_match_the_asset_roster(umbrella_docs: list[dict[str, Any]]) -> None:
    """The roster-drift guard (CHT-88): Secret keys == asset placeholders == KC envs.

    The Secret, the imported asset's placeholders (CHT-87), and the
    StatefulSet's import envs (CHT-89) are three copies of one roster; an
    added or renamed otel client that misses one of them fails this test.
    """
    secret = find(umbrella_docs, "Secret", "atlas-otel-clients")
    assert set(secret["data"]) == set(OTEL_CLIENT_IDS)

    asset = json.loads(find(umbrella_docs, "ConfigMap", "atlas-keycloak-realm")["data"]["aurelius-atlas.json"])
    asset_ids = {c["clientId"] for c in asset["clients"] if c["clientId"].startswith("otel-")}
    assert asset_ids == set(OTEL_CLIENT_IDS)

    ss = find(umbrella_docs, "StatefulSet", "atlas-keycloak")
    envs = env_map(container(ss, "keycloak"))
    joined = set()
    for name, env in envs.items():
        ref = env.get("valueFrom", {}).get("secretKeyRef")
        if name.endswith("_CLIENT_SECRET") and ref and ref["name"] == "atlas-otel-clients":
            joined.add(ref["key"])
    assert joined == set(OTEL_CLIENT_IDS)


@pytest.mark.covers(rules=["CHT-88"])
def test__per_client_values_override_leaves_the_others_generated() -> None:
    """Supplying one client's secret changes only that key (CHT-88, DD-277).

    The rotation story: rotate one leaked producer credential without
    disturbing the other six.
    """
    docs = helm_render(
        UMBRELLA_CHART,
        value_files=TEST_VALUES,
        sets=("secrets.otelClients.clients.otel-postgres=supplied-pg",),
    )
    secret = find(docs, "Secret", "atlas-otel-clients")
    assert set(secret["data"]) == set(OTEL_CLIENT_IDS)
    assert secret["data"]["otel-postgres"] == "c3VwcGxpZWQtcGc="  # b64("supplied-pg")
    others = {k: v for k, v in secret["data"].items() if k != "otel-postgres"}
    assert all(len(v) >= 44 for v in others.values())


@pytest.mark.covers(rules=["CHT-83"])
def test__grafana_oauth_secret_gates_on_consumers() -> None:
    """<release>-grafana-oauth generates for either consumer (CHT-83, DD-275).

    The observability chart's Grafana joins it; a non-master keycloak install
    feeds the realm import. With both consumers gone (obs disabled, keycloak
    on master), nothing generates — CHT-80's unused-credential rule.
    """
    docs = helm_render(
        UMBRELLA_CHART,
        value_files=TEST_VALUES,
        sets=("atlas-observability.enabled=false",),
    )
    # Keycloak still imports the prod realm: the import placeholder needs it.
    assert "atlas-grafana-oauth" in names(docs, "Secret")

    docs = helm_render(
        UMBRELLA_CHART,
        value_files=TEST_VALUES,
        sets=("atlas-observability.enabled=false", "atlas-keycloak.realm.name=master"),
    )
    assert "atlas-grafana-oauth" not in names(docs, "Secret")

    docs = helm_render(
        UMBRELLA_CHART,
        value_files=TEST_VALUES,
        sets=("secrets.grafanaOauth.clientSecret=supplied-oauth",),
    )
    secret = find(docs, "Secret", "atlas-grafana-oauth")
    assert secret["data"]["client-secret"] == "c3VwcGxpZWQtb2F1dGg="  # b64("supplied-oauth")


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


@pytest.mark.covers(rules=["CHT-19", "CHT-40"])
def test__grafana_admin_secret_gates_on_observability(umbrella_docs: list[dict[str, Any]]) -> None:
    """<release>-grafana-admin gates on the observability chart (CHT-19/40, DD-267).

    Generated under the CHT-19 pattern, key pair user/password, and the
    secret stops when the chart is disabled.
    """
    secret = find(umbrella_docs, "Secret", "atlas-grafana-admin")
    assert set(secret["data"]) == {"user", "password"}
    assert len(base64.b64decode(secret["data"]["password"])) == 32

    docs = helm_render(
        UMBRELLA_CHART,
        value_files=TEST_VALUES,
        sets=("atlas-observability.enabled=false",),
    )
    assert "atlas-grafana-admin" not in names(docs, "Secret")


@pytest.mark.covers(rules=["CHT-42"])
def test__stock_install_is_a_self_observing_system(umbrella_docs: list[dict[str, Any]]) -> None:
    """The stock install is a self-observing system (CHT-42, ADR 016).

    The umbrella's enablement makes the stock render carry every telemetry
    join: the server + aux per-service legs, Keycloak's legacy leg, the
    collector's issuer-wait, and both puller Deployments.
    """
    deployments = names(umbrella_docs, "Deployment")
    assert {"atlas-elasticsearch-metrics-puller", "atlas-keycloak-metrics-puller"} <= deployments
    assert {"atlas-observability", "atlas-observability-prometheus", "atlas-observability-grafana"} <= deployments

    server = find(umbrella_docs, "Deployment", "atlas-server")
    server_envs = {e["name"] for e in container(server, "server")["env"]}
    assert "AURELIUS_ATLAS_SERVER_OTEL_ENDPOINT" in server_envs
    keycloak = find(umbrella_docs, "StatefulSet", "atlas-keycloak")
    keycloak_envs = {e["name"] for e in container(keycloak, "keycloak")["env"]}
    assert {"OTEL_EXPORTER_OTLP_ENDPOINT", "QUARKUS_OTEL_EXPORTER_OTLP_TRUST_CERT_CERTS"} <= keycloak_envs


@pytest.mark.covers(rules=["CHT-60"])
def test__namespace_default_deny_renders_once(umbrella_docs: list[dict[str, Any]]) -> None:
    """One deny-all-ingress policy selects every pod and allows nothing (CHT-60).

    The namespace contract lives here, not in the component charts: a
    component's networkPolicy.enabled=false must never open the whole
    namespace by removing a deny it never owned.
    """
    deny = find(umbrella_docs, "NetworkPolicy", "atlas-deny-all-ingress")
    assert deny["spec"]["podSelector"] == {}
    assert deny["spec"]["policyTypes"] == ["Ingress"]
    assert "ingress" not in deny["spec"]
    assert "egress" not in deny["spec"]
    # Exactly one deny in the render — the component charts never render one.
    denies = [d for d in umbrella_docs if d["kind"] == "NetworkPolicy" and d["spec"]["podSelector"] == {}]
    assert len(denies) == 1


def _umbrella_scope(policy_names: set[str]) -> set[str]:
    """The policies the umbrella itself owns: the deny-all and the edge allows."""
    return {n for n in policy_names if n == "atlas-deny-all-ingress" or n.startswith("atlas-edge-")}


@pytest.mark.covers(rules=["CHT-72", "CHT-73"])
def test__network_policy_off_drops_umbrella_scope(umbrella_docs: list[dict[str, Any]]) -> None:
    """Umbrella networkPolicy.enabled=false drops exactly its own policies (CHT-72).

    The umbrella's switch owns the deny-all and the edge allows; the
    component charts keep their own (each chart's switch is tested there —
    the split is the point, and no switch re-renders anything else).
    CHT-73: every rendered policy is Ingress-only — egress is unrestricted
    by design (a cluster-policy decision, not a chart one).
    """
    policies = [d for d in umbrella_docs if d["kind"] == "NetworkPolicy"]
    assert policies, "the stock render must carry policies"
    for policy in policies:
        assert policy["spec"]["policyTypes"] == ["Ingress"], policy["metadata"]["name"]
        assert "egress" not in policy["spec"], policy["metadata"]["name"]

    docs = helm_render(
        UMBRELLA_CHART,
        value_files=TEST_VALUES,
        sets=("networkPolicy.enabled=false",),
    )
    after = names(docs, "NetworkPolicy")
    umbrella_before = _umbrella_scope(names(umbrella_docs, "NetworkPolicy"))
    assert _umbrella_scope(after) == set()
    assert after == names(umbrella_docs, "NetworkPolicy") - umbrella_before

    def inventory(render: list[dict[str, Any]]) -> list[str]:
        return sorted(
            f"{d['kind']}/{d['metadata']['name']}"
            for d in render
            if d["kind"] != "NetworkPolicy" or d["metadata"]["name"] not in umbrella_before
        )

    assert inventory(docs) == inventory(umbrella_docs)


@pytest.mark.covers(rules=["CHT-74"])
def test__every_consumer_names_the_imported_realm(umbrella_docs: list[dict[str, Any]]) -> None:
    """One realm fact, every join (CHT-74).

    The realm the Keycloak chart imports is the realm every realm-bearing
    value names: rather than enumerate the env slots, the pin is that every
    ``/realms/<x>`` URL and the SPA's bare realm in the composed render name
    the imported one. A consumer drifting from global.realm fails here.
    """
    realm_cm = find(umbrella_docs, "ConfigMap", "atlas-keycloak-realm")
    (realm_file,) = realm_cm["data"].keys()
    realm = json.loads(realm_cm["data"][realm_file])["realm"]
    assert realm == "aurelius-atlas" == realm_file.removesuffix(".json")

    webapp = find(umbrella_docs, "ConfigMap", "atlas-webapp-config")
    assert yaml.safe_load(webapp["data"]["config.json"])["keycloak"]["realm"] == realm

    named = set()
    for doc in umbrella_docs:
        text = yaml.dump(doc)
        for match in re.finditer(r"/realms/([^/\"'\s\\]+)", text):
            named.add(match.group(1))
    assert named == {realm}


def _render_images(docs: list[dict[str, Any]]) -> set[str]:
    """Every container/initContainer image across every workload document."""
    images: set[str] = set()
    for doc in docs:
        spec = doc.get("spec") or {}
        template = spec.get("template") if isinstance(spec, dict) else None
        pod = template.get("spec") if isinstance(template, dict) else None
        if not isinstance(pod, dict):
            continue
        for c in pod.get("containers", []) + pod.get("initContainers", []):
            images.add(c["image"])
    return images


@pytest.mark.covers(rules=["CHT-97"])
def test__every_image_is_tagged_aurelius_or_pinned_third_party(umbrella_docs: list[dict[str, Any]]) -> None:
    """The stock stack renders no unpinned image (CHT-97).

    The CI-side twin of the scheduled registry check (CHT-96): each image is
    either an Aurelius tag reference (``ghcr.io/aureliusenterprise/<name>:``
    — the shape CHT-94 keeps for own images) or a pinned
    third-party reference (``<known repo>@sha256:<64 hex>`` from the
    committed set, CHT-93). A third-party image that lost its digest, or a
    new repo nobody pinned, fails here.
    """
    aurelius = re.compile(r"^ghcr\.io/aureliusenterprise/[a-z0-9-]+:[A-Za-z0-9._-]+$")
    pinned = re.compile(r"^([a-z0-9./-]+)@sha256:([0-9a-f]{64})$")
    images = _render_images(umbrella_docs)
    assert images, "the render carries no workload images"
    seen_repos: set[str] = set()
    for image in sorted(images):
        if aurelius.match(image):
            continue
        match = pinned.match(image)
        assert match, f"unpinned image reference: {image}"
        repo, digest = match.groups()
        assert PINNED.get(repo) == f"sha256:{digest}", f"digest does not match the committed pin: {image}"
        seen_repos.add(repo)
    assert seen_repos == set(PINNED), f"the stack stopped rendering: {set(PINNED) - seen_repos}"


@pytest.mark.covers(rules=["CHT-94"])
def test__aurelius_images_render_by_tag_in_the_repo(umbrella_docs: list[dict[str, Any]]) -> None:
    """Aurelius images render tag-shaped, everywhere (CHT-94).

    Own images are not digest-pinned: their tags are written only by the
    signed publish chain and the chart artifact is itself immutable and
    signed, so no render — committed or packaged — carries an ``@sha256:``
    on a ghcr.io/aureliusenterprise image.
    """
    for image in sorted(_render_images(umbrella_docs)):
        if image.startswith("ghcr.io/aureliusenterprise/"):
            assert "@sha256:" not in image, image

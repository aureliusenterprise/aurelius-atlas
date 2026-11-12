"""Chart-contract suite for the quality-scanner CronJob chart (CHT-114..117, 12.3).

The batch shape asserted at the render: one CronJob and nothing serving
(CHT-115), the identity joins the job mints its client credentials with
(CHT-116), the optional trust CA and the passthrough blocks (CHT-117), and
the standalone rule — the umbrella never carries a scanner workload
(CHT-114, DD-508). kafka-scanner and db-scanner re-prove the shared rules in
their own suites; the audience default and the registration absence
(CHT-118..120) ride the server, keycloak, and umbrella suites.
"""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import (
    SCANNER_CHARTS,
    WORKSPACE,
    env_map,
    env_value,
    find,
    helm_render,
    helm_render_fails,
    names,
)

CHART = SCANNER_CHARTS["quality-scanner"]
TEST_VALUES = (CHART / "tests/values.test.yaml",)
CLIENT_ID = "aurelius-atlas-quality-scanner"
PREFIX = "AURELIUS_ATLAS_QUALITY_SCANNER_"


@pytest.fixture(scope="session")
def scanner_docs() -> list[dict[str, Any]]:
    """The chart under its CI test values (the required guards answered)."""
    return helm_render(CHART, value_files=TEST_VALUES)


@pytest.mark.covers(rules=["CHT-114"])
def test__chart_stays_out_of_the_umbrella() -> None:
    """No umbrella dependency names a scanner chart (CHT-114, DD-508).

    The scanners deploy to customer environments on their own release cycle;
    the umbrella's dependency list is the single place the two trees join,
    so that list is what must never grow a scanner entry.
    """
    manifest = yaml.safe_load((WORKSPACE / "helm/Chart.yaml").read_text())
    deps = {d["name"] for d in manifest.get("dependencies", [])}
    assert not [d for d in deps if d.endswith("-scanner")]
    # And the chart renders standalone — the bare render needs no umbrella
    # values beyond the two required joins its guards name (CHT-03's
    # full global.* declaration).
    error = helm_render_fails(CHART)
    assert "schedule is required" in error
    assert "catalogue.serverUrl is required" in error


@pytest.mark.covers(rules=["CHT-115"])
def test__workload_is_one_cronjob_and_nothing_serving(scanner_docs: list[dict[str, Any]]) -> None:
    """CronJob + ServiceAccount only: no Service, Certificate, or policy (CHT-115).

    The job listens on no port and no in-cluster caller dials it, so the
    service charts' leaf-certificate and NetworkPolicy family renders
    nothing here.
    """
    assert names(scanner_docs, "CronJob") == {"atlas-quality-scanner"}
    assert names(scanner_docs, "ServiceAccount") == {"atlas-quality-scanner"}
    for kind in ("Deployment", "Service", "Certificate", "NetworkPolicy", "Ingress", "HorizontalPodAutoscaler"):
        assert kind not in {d["kind"] for d in scanner_docs}, kind
    # The chart never generates a credential (DD-509): no Secret of its own.
    assert "Secret" not in {d["kind"] for d in scanner_docs}


@pytest.mark.covers(rules=["CHT-115"])
def test__cron_posture_is_overlap_and_zombie_safe(scanner_docs: list[dict[str, Any]]) -> None:
    """Forbid, deadline, history limits, and the Never restart policy (DD-510)."""
    cronjob = find(scanner_docs, "CronJob", "atlas-quality-scanner")
    spec = cronjob["spec"]
    assert spec["schedule"] == "0 3 * * *"
    assert spec["concurrencyPolicy"] == "Forbid"
    assert spec["startingDeadlineSeconds"] == 600
    assert spec["successfulJobsHistoryLimit"] == 3
    assert spec["failedJobsHistoryLimit"] == 1
    assert spec["suspend"] is False
    assert "ttlSecondsAfterFinished" not in spec  # renders only when named
    job_spec = spec["jobTemplate"]["spec"]
    assert job_spec["activeDeadlineSeconds"] == 3600
    pod = job_spec["template"]["spec"]
    assert pod["restartPolicy"] == "Never"
    assert pod["automountServiceAccountToken"] is False

    with_ttl = helm_render(CHART, value_files=TEST_VALUES, sets=("ttlSecondsAfterFinished=300",))
    assert find(with_ttl, "CronJob", "atlas-quality-scanner")["spec"]["ttlSecondsAfterFinished"] == 300


@pytest.mark.covers(rules=["CHT-115"])
def test__pod_is_hardened_like_the_service_charts(scanner_docs: list[dict[str, Any]]) -> None:
    """uid/gid 65532, read-only root, drop-all, seccomp RuntimeDefault (DD-257)."""
    pod = _pod(scanner_docs)
    psc = pod["securityContext"]
    assert psc["runAsNonRoot"] is True
    assert psc["runAsUser"] == 65532
    assert psc["runAsGroup"] == 65532
    assert psc["seccompProfile"] == {"type": "RuntimeDefault"}
    sc = _container(scanner_docs)["securityContext"]
    assert sc["readOnlyRootFilesystem"] is True
    assert sc["allowPrivilegeEscalation"] is False
    assert sc["capabilities"] == {"drop": ["ALL"]}
    # A batch pod with automountServiceAccountToken false mounts no API token.
    assert not [v for v in pod.get("volumes", []) if "projected" in v]


@pytest.mark.covers(rules=["CHT-116"])
def test__identity_env_block_is_joins_not_literals(scanner_docs: list[dict[str, Any]]) -> None:
    """SERVER_URL, derived TOKEN_URL, CLIENT_ID, and the secretKeyRef join (CHT-116).

    The CHT-21 rule for a batch job: nothing credential-shaped is a literal,
    and the token URL follows the CHT-74 one-fact realm contract. The
    default Secret name is <release>-scanner-clients under the client-id
    key — a Secret the deployment places itself (CHT-118/119, DD-509): no
    shipped chart generates it.
    """
    envs = env_map(_container(scanner_docs))
    assert env_value(envs, f"{PREFIX}SERVER_URL") == "https://atlas-server.atlas.svc.cluster.local:21000"
    assert (
        env_value(envs, f"{PREFIX}TOKEN_URL")
        == "https://keycloak.atlas.test/realms/aurelius-atlas/protocol/openid-connect/token"
    )
    assert env_value(envs, f"{PREFIX}CLIENT_ID") == CLIENT_ID
    join = envs[f"{PREFIX}CLIENT_SECRET"]["valueFrom"]["secretKeyRef"]
    assert join == {"name": "atlas-scanner-clients", "key": CLIENT_ID}


@pytest.mark.covers(rules=["CHT-116"])
def test__token_url_follows_the_issuer_and_realm_facts() -> None:
    """global.realm retargets TOKEN_URL; the domain fallback derives the issuer.

    The same CHT-74/CHT-03 contract the service charts pin: issuer.url wins,
    https://keycloak.<domain> is its fallback, and the realm segment is the
    one fact — a master-realm deployment mints against master.
    """
    master = helm_render(CHART, value_files=TEST_VALUES, sets=("global.realm=master",))
    envs = env_map(_container(master))
    assert (
        env_value(envs, f"{PREFIX}TOKEN_URL")
        == "https://keycloak.atlas.test/realms/master/protocol/openid-connect/token"
    )

    fallback = helm_render(
        CHART,
        value_files=TEST_VALUES,
        sets=("global.issuer.url=", "global.domain=atlas.example"),
    )
    fenvs = env_map(_container(fallback))
    assert (
        env_value(fenvs, f"{PREFIX}TOKEN_URL")
        == "https://keycloak.atlas.example/realms/aurelius-atlas/protocol/openid-connect/token"
    )


@pytest.mark.covers(rules=["CHT-116"])
def test__secret_join_and_client_id_are_operator_knobs(tmp_path: Path) -> None:
    """auth.secretName/_key and clientId override; the chart still makes no Secret."""
    values = tmp_path / "auth.yaml"
    values.write_text("auth:\n    clientId: my-scanner\n    secretName: byo-clients\n    secretKey: my-key\n")
    docs = helm_render(CHART, value_files=(*TEST_VALUES, values))
    envs = env_map(_container(docs))
    assert env_value(envs, f"{PREFIX}CLIENT_ID") == "my-scanner"
    join = envs[f"{PREFIX}CLIENT_SECRET"]["valueFrom"]["secretKeyRef"]
    assert join == {"name": "byo-clients", "key": "my-key"}
    assert "Secret" not in {d["kind"] for d in docs}


@pytest.mark.covers(rules=["CHT-117"])
def test__trust_ca_mounts_only_when_named(scanner_docs: list[dict[str, Any]]) -> None:
    """A named CA Secret mounts read-only and joins CA_FILE; none keeps system trust.

    The bootstrap path for a bring-your-own issuer: with no name the render
    carries no CA volume, no mount, and no CA_FILE, so the image resolves
    the public chain from its own trust store.
    """
    docs = helm_render(CHART, value_files=TEST_VALUES, sets=("trust.caSecretName=my-ca",))
    envs = env_map(_container(docs))
    assert env_value(envs, f"{PREFIX}CA_FILE") == "/etc/aurelius-atlas/ca/ca.crt"
    pod = _pod(docs)
    volumes = {v["name"]: v for v in pod["volumes"]}
    assert volumes["ca"]["secret"]["secretName"] == "my-ca"
    mounts = {m["name"]: m for m in _container(docs)["volumeMounts"]}
    assert mounts["ca"]["mountPath"] == "/etc/aurelius-atlas/ca"
    assert mounts["ca"]["readOnly"] is True

    # global.trust.caSecretName is the umbrella-shaped spelling; the chart-level
    # name wins when both are set (the chart-over-global precedence, CHT-03).
    docs = helm_render(CHART, value_files=TEST_VALUES, sets=("global.trust.caSecretName=global-ca",))
    volumes = {v["name"]: v for v in _pod(docs)["volumes"]}
    assert volumes["ca"]["secret"]["secretName"] == "global-ca"
    docs = helm_render(
        CHART,
        value_files=TEST_VALUES,
        sets=("global.trust.caSecretName=global-ca", "trust.caSecretName=chart-ca"),
    )
    volumes = {v["name"]: v for v in _pod(docs)["volumes"]}
    assert volumes["ca"]["secret"]["secretName"] == "chart-ca"

    envs = env_map(_container(scanner_docs))
    assert f"{PREFIX}CA_FILE" not in envs
    assert not _pod(scanner_docs).get("volumes")


@pytest.mark.covers(rules=["CHT-117"])
def test__passthrough_blocks_render_verbatim(tmp_path: Path) -> None:
    """config, secretRefs, and extraEnv reach the container unchanged (CHT-117).

    Telemetry (DD-511) and any setting the chart does not model travel these
    blocks; the file-source SOURCES map rides the config block's twin, the
    typed scan block below.
    """
    values = tmp_path / "pass.yaml"
    values.write_text(
        "config:\n"
        "    AURELIUS_ATLAS_QUALITY_SCANNER_LOG_LEVEL: DEBUG\n"
        "secretRefs:\n"
        "    -   name: AURELIUS_ATLAS_QUALITY_SCANNER_SASL_PASSWORD\n"
        "        secret: byo-sasl\n"
        "        key: password\n"
        "extraEnv:\n"
        "    -   name: OTEL_SERVICE_NAME\n"
        "        value: quality-scanner\n"
    )
    envs = env_map(_container(helm_render(CHART, value_files=(*TEST_VALUES, values))))
    assert env_value(envs, "AURELIUS_ATLAS_QUALITY_SCANNER_LOG_LEVEL") == "DEBUG"
    assert envs["AURELIUS_ATLAS_QUALITY_SCANNER_SASL_PASSWORD"]["valueFrom"]["secretKeyRef"] == {
        "name": "byo-sasl",
        "key": "password",
    }
    assert env_value(envs, "OTEL_SERVICE_NAME") == "quality-scanner"


@pytest.mark.covers(rules=["CHT-117"])
def test__scan_knobs_render_only_when_set(scanner_docs: list[dict[str, Any]]) -> None:
    """The sources envelope, max rows, and search limit join as the app parses them.

    DQS-17's envelope: SOURCES is the JSON list, rendered by toJson so the
    app's pydantic parse gets valid JSON; the bounds are ints. Unset, no env
    renders and the app's defaults stay the app's (CHT-117's shape rule).
    """
    docs = helm_render(
        CHART,
        value_files=TEST_VALUES,
        sets=(
            "scan.sources[0].kind=file",
            "scan.sources[0].dataset.qualifiedName=/d3",
            "scan.sources[0].config.path=/data/d3.parquet",
            "scan.maxRows=500000",
            "scan.searchLimit=20000",
        ),
    )
    envs = env_map(_container(docs))
    assert json.loads(env_value(envs, f"{PREFIX}SOURCES")) == [
        {"kind": "file", "dataset": {"qualifiedName": "/d3"}, "config": {"path": "/data/d3.parquet"}}
    ]
    assert env_value(envs, f"{PREFIX}MAX_ROWS") == "500000"
    assert env_value(envs, f"{PREFIX}SEARCH_LIMIT") == "20000"

    envs = env_map(_container(scanner_docs))
    for name in (f"{PREFIX}SOURCES", f"{PREFIX}MAX_ROWS", f"{PREFIX}SEARCH_LIMIT"):
        assert name not in envs


@pytest.mark.covers(rules=["CHT-116"])
def test__bare_render_fails_naming_both_required_joins() -> None:
    """The two guards fire together on the bare render (CHT-115/116, CHT-02)."""
    error = helm_render_fails(CHART)
    assert "schedule is required" in error
    assert "catalogue.serverUrl is required" in error
    # The registration name the deployment issues this client under
    # (CHT-118): the test values never override auth.clientId.
    assert CLIENT_ID == "aurelius-atlas-quality-scanner"


@pytest.mark.covers(rules=["CHT-125"])
def test__telemetry_off_by_default_and_endpoint_guarded(scanner_docs: list[dict[str, Any]]) -> None:
    """Off renders no OTEL env at all; on without an endpoint fails the render.

    A batch job exports a handful of spans per run, so the block is opt-in
    (CHT-125): the silent default is the plain SDK setup. And there is no
    co-deployed collector to derive an endpoint from (DD-508), so enabling
    the block names the collector or the chart refuses to render.
    """
    envs = env_map(_container(scanner_docs))
    assert not [name for name in envs if "OTEL" in name]
    error = helm_render_fails(CHART, value_files=TEST_VALUES, sets=("telemetry.enabled=true",))
    assert "telemetry.endpoint is required" in error


@pytest.mark.covers(rules=["CHT-125"])
def test__telemetry_auth_on_joins_the_app_leg_and_reuses_identity() -> None:
    """Auth on: the prefixed trio, minting with the job's own client by default.

    The reuse defaults are the whole point (DD-514's rule): the ingest client
    and its Secret default to the identity join the job already reads, so a
    deployment that registered one scanner client turns telemetry on with two
    values. Overriding the client or Secret splits it (a dedicated ingest
    client, CHT-125). The chart still generates no Secret (DD-509).
    """
    docs = helm_render(
        CHART,
        value_files=TEST_VALUES,
        sets=("telemetry.enabled=true", "telemetry.endpoint=https://otel.example:4319"),
    )
    envs = env_map(_container(docs))
    assert env_value(envs, f"{PREFIX}OTEL_ENDPOINT") == "https://otel.example:4319"
    assert (
        env_value(envs, f"{PREFIX}OTEL_TOKEN_URL")
        == "https://keycloak.atlas.test/realms/aurelius-atlas/protocol/openid-connect/token"
    )
    assert env_value(envs, f"{PREFIX}OTEL_CLIENT_ID") == CLIENT_ID
    assert envs[f"{PREFIX}OTEL_CLIENT_SECRET"]["valueFrom"]["secretKeyRef"] == {
        "name": "atlas-scanner-clients",
        "key": CLIENT_ID,
    }
    assert "Secret" not in {d["kind"] for d in docs}

    split = helm_render(
        CHART,
        value_files=TEST_VALUES,
        sets=(
            "telemetry.enabled=true",
            "telemetry.endpoint=https://otel.example:4319",
            "telemetry.auth.clientId=ingest-bot",
            "telemetry.auth.secretName=otel-creds",
        ),
    )
    envs = env_map(_container(split))
    assert env_value(envs, f"{PREFIX}OTEL_CLIENT_ID") == "ingest-bot"
    assert envs[f"{PREFIX}OTEL_CLIENT_SECRET"]["valueFrom"]["secretKeyRef"] == {
        "name": "otel-creds",
        "key": "ingest-bot",
    }


@pytest.mark.covers(rules=["CHT-125"])
def test__telemetry_auth_off_rides_the_env_leg_unauthenticated() -> None:
    """Auth off: the bare SDK env var, plus the cert var only when a CA mounts.

    A customer collector that asks for no credential still gets the export:
    the chart joins OTEL_EXPORTER_OTLP_ENDPOINT, which the SDK's env leg
    reads on its own (DD-210). TLS to the collector stays optional the same
    way every other leg has it — the trust CA mount (CHT-117) doubles as the
    collector's pin via the SDK's standard certificate var.
    """
    docs = helm_render(
        CHART,
        value_files=TEST_VALUES,
        sets=(
            "telemetry.enabled=true",
            "telemetry.endpoint=https://otel.example:4319",
            "telemetry.auth.enabled=false",
        ),
    )
    envs = env_map(_container(docs))
    assert env_value(envs, "OTEL_EXPORTER_OTLP_ENDPOINT") == "https://otel.example:4319"
    assert "OTEL_EXPORTER_OTLP_CERTIFICATE" not in envs
    assert f"{PREFIX}OTEL_ENDPOINT" not in envs
    assert f"{PREFIX}OTEL_CLIENT_SECRET" not in envs

    docs = helm_render(
        CHART,
        value_files=TEST_VALUES,
        sets=(
            "telemetry.enabled=true",
            "telemetry.endpoint=https://otel.example:4319",
            "telemetry.auth.enabled=false",
            "trust.caSecretName=my-ca",
        ),
    )
    envs = env_map(_container(docs))
    assert env_value(envs, "OTEL_EXPORTER_OTLP_CERTIFICATE") == "/etc/aurelius-atlas/ca/ca.crt"


def _pod(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """The CronJob's pod template spec."""
    return find(docs, "CronJob", "atlas-quality-scanner")["spec"]["jobTemplate"]["spec"]["template"]["spec"]


def _container(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """The scanner container (the chart names it after the short component)."""
    (app,) = _pod(docs)["containers"]
    return app

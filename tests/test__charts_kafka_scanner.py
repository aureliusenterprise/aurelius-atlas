"""Chart-contract suite for the kafka-scanner CronJob chart (CHT-114..117, 121/122, 13.2).

The shared batch contract re-proven for this chart (the CHT-115..117 rules
apply verbatim, 13.2's spec) plus the broker half: BOOTSTRAP_SERVERS is a
required first-class join (CHT-121) and the OAUTHBEARER leg reuses the
catalogue client (CHT-122, DD-514). The audience default and the registration
absence (CHT-118..120) ride the server, keycloak, and umbrella suites.
"""

from pathlib import Path
from typing import Any

import pytest
from conftest import (
    SCANNER_CHARTS,
    env_map,
    env_value,
    find,
    helm_render,
    helm_render_fails,
    names,
)

CHART = SCANNER_CHARTS["kafka-scanner"]
TEST_VALUES = (CHART / "tests/values.test.yaml",)
CLIENT_ID = "aurelius-atlas-kafka-scanner"
PREFIX = "AURELIUS_ATLAS_KAFKA_SCANNER_"


@pytest.fixture(scope="session")
def scanner_docs() -> list[dict[str, Any]]:
    """The chart under its CI test values (the three required guards answered)."""
    return helm_render(CHART, value_files=TEST_VALUES)


@pytest.mark.covers(rules=["CHT-115"])
def test__cronjob_workload_and_cron_posture(scanner_docs: list[dict[str, Any]]) -> None:
    """One CronJob, no serving kinds, Forbid + deadline + Never (CHT-115, DD-510)."""
    assert names(scanner_docs, "CronJob") == {"atlas-kafka-scanner"}
    assert names(scanner_docs, "ServiceAccount") == {"atlas-kafka-scanner"}
    for kind in ("Deployment", "Service", "Certificate", "NetworkPolicy", "Secret"):
        assert kind not in {d["kind"] for d in scanner_docs}, kind

    spec = find(scanner_docs, "CronJob", "atlas-kafka-scanner")["spec"]
    assert spec["schedule"] == "30 4 * * *"
    assert spec["concurrencyPolicy"] == "Forbid"
    job_spec = spec["jobTemplate"]["spec"]
    assert job_spec["activeDeadlineSeconds"] == 3600
    pod = job_spec["template"]["spec"]
    assert pod["restartPolicy"] == "Never"
    assert pod["automountServiceAccountToken"] is False
    psc = pod["securityContext"]
    assert (psc["runAsUser"], psc["runAsGroup"], psc["runAsNonRoot"]) == (65532, 65532, True)
    sc = _container(scanner_docs)["securityContext"]
    assert sc["readOnlyRootFilesystem"] is True
    assert sc["capabilities"] == {"drop": ["ALL"]}


@pytest.mark.covers(rules=["CHT-116"])
def test__identity_env_block_is_joins_not_literals(scanner_docs: list[dict[str, Any]]) -> None:
    """SERVER_URL, derived TOKEN_URL, CLIENT_ID, secretKeyRef join (CHT-116)."""
    envs = env_map(_container(scanner_docs))
    assert env_value(envs, f"{PREFIX}SERVER_URL") == "https://atlas-server.atlas.svc.cluster.local:21000"
    assert (
        env_value(envs, f"{PREFIX}TOKEN_URL")
        == "https://keycloak.atlas.test/realms/aurelius-atlas/protocol/openid-connect/token"
    )
    assert env_value(envs, f"{PREFIX}CLIENT_ID") == CLIENT_ID
    join = envs[f"{PREFIX}CLIENT_SECRET"]["valueFrom"]["secretKeyRef"]
    assert join == {"name": "atlas-scanner-clients", "key": CLIENT_ID}

    master = helm_render(CHART, value_files=TEST_VALUES, sets=("global.realm=master",))
    menvs = env_map(_container(master))
    assert (
        env_value(menvs, f"{PREFIX}TOKEN_URL")
        == "https://keycloak.atlas.test/realms/master/protocol/openid-connect/token"
    )


@pytest.mark.covers(rules=["CHT-117"])
def test__trust_ca_and_passthroughs(scanner_docs: list[dict[str, Any]]) -> None:
    """CA_FILE only with a named Secret; config/secretRefs/extraEnv verbatim (CHT-117)."""
    assert f"{PREFIX}CA_FILE" not in env_map(_container(scanner_docs))
    assert not _pod(scanner_docs).get("volumes")

    docs = helm_render(CHART, value_files=TEST_VALUES, sets=("trust.caSecretName=my-ca",))
    envs = env_map(_container(docs))
    assert env_value(envs, f"{PREFIX}CA_FILE") == "/etc/aurelius-atlas/ca/ca.crt"
    volumes = {v["name"]: v for v in _pod(docs)["volumes"]}
    assert volumes["ca"]["secret"]["secretName"] == "my-ca"


@pytest.mark.covers(rules=["CHT-121"])
def test__broker_address_is_a_required_join(scanner_docs: list[dict[str, Any]]) -> None:
    """BOOTSTRAP_SERVERS is the required value; the bare render fails naming it.

    The app's default is the dev loopback — pointing a cluster job at
    localhost:29092 is a silent no-scan (KSC-01), so the guard fails the
    install, not the 04:30 run (DD-515).
    """
    envs = env_map(_container(scanner_docs))
    assert env_value(envs, f"{PREFIX}BOOTSTRAP_SERVERS") == "kafka.dev.svc.cluster.local:29092"

    error = helm_render_fails(CHART)
    assert "broker.bootstrapServers is required" in error
    assert "schedule is required" in error
    assert "catalogue.serverUrl is required" in error


@pytest.mark.covers(rules=["CHT-121"])
def test__scan_knobs_render_only_when_set(scanner_docs: list[dict[str, Any]], tmp_path: Path) -> None:
    """Unset knobs render nothing (the app's defaults stay the app's, KSC-02/03/05)."""
    envs = env_map(_container(scanner_docs))
    for name in (
        "SECURITY_PROTOCOL",
        "SYSTEM_NAME",
        "TOPICS",
        "SNIFF_MESSAGES",
        "POLL_TIMEOUT_SECONDS",
        "ADMIN_REQUEST_TIMEOUT_MS",
        "REGISTRY_TIMEOUT_SECONDS",
        "SCHEMA_REGISTRY_URL",
    ):
        assert f"{PREFIX}{name}" not in envs, name

    values = tmp_path / "knobs.yaml"
    values.write_text(
        "broker:\n"
        "    securityProtocol: SASL_SSL\n"
        "    systemName: Prod Cluster\n"
        "    topicPattern: 'events\\..*'\n"
        "    sniffMessages: 50\n"
        "    pollTimeoutSeconds: 2.5\n"
        "    adminRequestTimeoutMs: 4000\n"
        "    registryTimeoutSeconds: 8\n"
        "schemaRegistry:\n"
        "    url: http://registry:8081\n"
    )
    docs = helm_render(CHART, value_files=(*TEST_VALUES, values))
    envs = env_map(_container(docs))
    assert env_value(envs, f"{PREFIX}SECURITY_PROTOCOL") == "SASL_SSL"
    assert env_value(envs, f"{PREFIX}SYSTEM_NAME") == "Prod Cluster"
    assert env_value(envs, f"{PREFIX}TOPICS") == "events\\..*"
    assert env_value(envs, f"{PREFIX}SNIFF_MESSAGES") == "50"
    assert env_value(envs, f"{PREFIX}POLL_TIMEOUT_SECONDS") == "2.5"
    assert env_value(envs, f"{PREFIX}ADMIN_REQUEST_TIMEOUT_MS") == "4000"
    assert env_value(envs, f"{PREFIX}REGISTRY_TIMEOUT_SECONDS") == "8"
    assert env_value(envs, f"{PREFIX}SCHEMA_REGISTRY_URL") == "http://registry:8081"


@pytest.mark.covers(rules=["CHT-122"])
def test__broker_oauth_leg_reuses_the_catalogue_client(scanner_docs: list[dict[str, Any]]) -> None:
    """brokerOauth.enabled renders the OAUTHBEARER pair off the same identity.

    DD-514: the broker accepts the same Keycloak the catalogue trusts, so
    the chart joins SASL_OAUTH_TOKEN_URL/CLIENT_ID from the CHT-116 fact
    pair and the same Secret — one credential serves both doors. Off, none
    of the SASL_* env renders; securityProtocol is never inferred (an
    explicit value only).
    """
    envs = env_map(_container(scanner_docs))
    for name in ("SASL_MECHANISM", "SASL_OAUTH_TOKEN_URL", "SASL_OAUTH_CLIENT_ID", "SASL_OAUTH_CLIENT_SECRET"):
        assert f"{PREFIX}{name}" not in envs, name

    docs = helm_render(CHART, value_files=TEST_VALUES, sets=("brokerOauth.enabled=true",))
    envs = env_map(_container(docs))
    assert env_value(envs, f"{PREFIX}SASL_MECHANISM") == "OAUTHBEARER"
    assert (
        env_value(envs, f"{PREFIX}SASL_OAUTH_TOKEN_URL")
        == "https://keycloak.atlas.test/realms/aurelius-atlas/protocol/openid-connect/token"
    )
    assert env_value(envs, f"{PREFIX}SASL_OAUTH_CLIENT_ID") == CLIENT_ID
    join = envs[f"{PREFIX}SASL_OAUTH_CLIENT_SECRET"]["valueFrom"]["secretKeyRef"]
    assert join == {"name": "atlas-scanner-clients", "key": CLIENT_ID}

    # The realm fact retargets the broker token URL with the catalogue one.
    master = helm_render(CHART, value_files=TEST_VALUES, sets=("brokerOauth.enabled=true", "global.realm=master"))
    menvs = env_map(_container(master))
    assert (
        env_value(menvs, f"{PREFIX}SASL_OAUTH_TOKEN_URL")
        == "https://keycloak.atlas.test/realms/master/protocol/openid-connect/token"
    )


@pytest.mark.covers(rules=["CHT-121"])
def test__sasl_credentials_travel_secret_refs_never_values(scanner_docs: list[dict[str, Any]]) -> None:
    """PLAIN/SCRAM secrets arrive through the CHT-117 passthrough (DD-514).

    The chart models no SASL credential value: an operator names an
    existing Secret and maps its keys to the app's SASL_* env names, so no
    broker password ever enters a values file or a rendered manifest.
    """
    envs = env_map(_container(scanner_docs))
    assert f"{PREFIX}SASL_PASSWORD" not in envs
    assert f"{PREFIX}SASL_USERNAME" not in envs

    docs = helm_render(
        CHART,
        value_files=TEST_VALUES,
        sets=(
            f"secretRefs[0].name={PREFIX}SASL_PASSWORD",
            "secretRefs[0].secret=byo",
            "secretRefs[0].key=pw",
        ),
    )
    envs = env_map(_container(docs))
    assert envs[f"{PREFIX}SASL_PASSWORD"]["valueFrom"]["secretKeyRef"] == {"name": "byo", "key": "pw"}


@pytest.mark.covers(rules=["CHT-125"])
def test__telemetry_off_by_default_and_endpoint_guarded(scanner_docs: list[dict[str, Any]]) -> None:
    """Off renders no OTEL env at all; on without an endpoint fails the render (CHT-125)."""
    envs = env_map(_container(scanner_docs))
    assert not [name for name in envs if "OTEL" in name]
    error = helm_render_fails(CHART, value_files=TEST_VALUES, sets=("telemetry.enabled=true",))
    assert "telemetry.endpoint is required" in error


@pytest.mark.covers(rules=["CHT-125"])
def test__telemetry_auth_on_joins_the_app_leg_and_reuses_identity() -> None:
    """The trio with the job's own client/Secret by default; overrides split it (DD-514)."""
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
    """Bare SDK env var; the cert var joins only when the trust CA mounts (DD-210)."""
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
    return find(docs, "CronJob", "atlas-kafka-scanner")["spec"]["jobTemplate"]["spec"]["template"]["spec"]


def _container(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """The scanner container."""
    (app,) = _pod(docs)["containers"]
    return app

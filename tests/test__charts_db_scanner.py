"""Chart-contract suite for the db-scanner CronJob chart (CHT-114..117, 123/124, 13.4).

The shared batch contract re-proven for this chart (the CHT-115..117 rules
apply verbatim, 13.4's spec) plus the database half: the DSN is a Secret
reference and never a value, the System name is required (CHT-123, DD-516),
and one release scans one database under release-derived names (CHT-124,
DD-517). The audience default and the registration absence (CHT-118..120)
ride the server, keycloak, and umbrella suites.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import (
    SCANNER_CHARTS,
    env_map,
    env_value,
    find,
    helm_render,
    helm_render_fails,
    names,
)

CHART = SCANNER_CHARTS["db-scanner"]
TEST_VALUES = (CHART / "tests/values.test.yaml",)
CLIENT_ID = "aurelius-atlas-db-scanner"
PREFIX = "AURELIUS_ATLAS_DB_SCANNER_"


@pytest.fixture(scope="session")
def scanner_docs() -> list[dict[str, Any]]:
    """The chart under its CI test values (the four required guards answered)."""
    return helm_render(CHART, value_files=TEST_VALUES)


@pytest.mark.covers(rules=["CHT-115"])
def test__cronjob_workload_and_cron_posture(scanner_docs: list[dict[str, Any]]) -> None:
    """One CronJob, no serving kinds, Forbid + deadline + Never (CHT-115, DD-510)."""
    assert names(scanner_docs, "CronJob") == {"atlas-db-scanner"}
    assert names(scanner_docs, "ServiceAccount") == {"atlas-db-scanner"}
    for kind in ("Deployment", "Service", "Certificate", "NetworkPolicy", "Secret"):
        assert kind not in {d["kind"] for d in scanner_docs}, kind

    spec = find(scanner_docs, "CronJob", "atlas-db-scanner")["spec"]
    assert spec["schedule"] == "0 5 * * 1"
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


@pytest.mark.covers(rules=["CHT-123"])
def test__dsn_is_a_secret_reference_never_a_value(scanner_docs: list[dict[str, Any]]) -> None:
    """DSN renders as a secretKeyRef into the named Secret (DD-516).

    The DSN carries the database's credentials, so the chart takes only the
    Secret's name (required) and key (default "dsn"): no value path exists,
    and the credential never enters a values file, ConfigMap, or render —
    13.3's rule (DD-506) extended to the chart.
    """
    envs = env_map(_container(scanner_docs))
    join = envs[f"{PREFIX}DSN"]["valueFrom"]["secretKeyRef"]
    assert join == {"name": "crm-db-dsn", "key": "dsn"}
    assert "value" not in envs[f"{PREFIX}DSN"]

    keyed = helm_render(CHART, value_files=TEST_VALUES, sets=("database.dsnSecret.key=uri",))
    kenvs = env_map(_container(keyed))
    assert kenvs[f"{PREFIX}DSN"]["valueFrom"]["secretKeyRef"] == {"name": "crm-db-dsn", "key": "uri"}


@pytest.mark.covers(rules=["CHT-123"])
def test__system_name_is_required_and_joins() -> None:
    """SYSTEM_NAME comes from the required value; the bare render names it (DBS-03)."""
    envs = env_map(_container(helm_render(CHART, value_files=TEST_VALUES)))
    assert env_value(envs, f"{PREFIX}SYSTEM_NAME") == "CRM Postgres"

    error = helm_render_fails(CHART)
    assert "database.dsnSecret.name is required" in error
    assert "database.systemName is required" in error
    assert "schedule is required" in error
    assert "catalogue.serverUrl is required" in error


@pytest.mark.covers(rules=["CHT-123"])
def test__scan_knobs_render_only_when_set(scanner_docs: list[dict[str, Any]], tmp_path: Path) -> None:
    """Schema/table patterns and the connect timeout render only when named.

    Unset keeps the app's defaults (DBS-04's "default" Collection, the "*"
    patterns, the 10-second door timeout) — the CHT-117 shape rule again.
    """
    envs = env_map(_container(scanner_docs))
    for name in ("SCHEMA_NAME", "SCHEMAS", "TABLES", "CONNECT_TIMEOUT_SECONDS"):
        assert f"{PREFIX}{name}" not in envs, name

    values = tmp_path / "knobs.yaml"
    values.write_text(
        "database:\n"
        "    dsnSecret:\n"
        "        name: crm-db-dsn\n"
        "    systemName: CRM Postgres\n"
        "    schemaName: core\n"
        "    schemaPatterns: 'public|core'\n"
        "    tablePatterns: 'fact_.*'\n"
        "    connectTimeoutSeconds: 30\n"
    )
    docs = helm_render(CHART, value_files=(*TEST_VALUES, values))
    envs = env_map(_container(docs))
    assert env_value(envs, f"{PREFIX}SCHEMA_NAME") == "core"
    assert env_value(envs, f"{PREFIX}SCHEMAS") == "public|core"
    assert env_value(envs, f"{PREFIX}TABLES") == "fact_.*"
    assert env_value(envs, f"{PREFIX}CONNECT_TIMEOUT_SECONDS") == "30"


@pytest.mark.covers(rules=["CHT-124"])
def test__one_release_one_database_under_release_names() -> None:
    """Two releases, two independent scanners — names follow the release (DD-517).

    The fullname convention gives each release its own CronJob,
    ServiceAccount, and identity-Secret join (<release>-scanner-clients,
    CHT-116), which is what lets one chart scan two customer databases in
    one namespace. No driver-volume value exists: shipping a wheel beside
    the signed image stays an image concern (DBS-01).
    """
    docs = helm_render(CHART, release="crm", value_files=TEST_VALUES)
    assert names(docs, "CronJob") == {"crm-atlas-db-scanner"}
    assert names(docs, "ServiceAccount") == {"crm-atlas-db-scanner"}
    join = env_map(_container(docs))[f"{PREFIX}CLIENT_SECRET"]["valueFrom"]["secretKeyRef"]
    assert join == {"name": "crm-scanner-clients", "key": CLIENT_ID}

    # The fullname dedupe: a release already named like the chart does not
    # double it (the service charts' convention).
    dupe = helm_render(CHART, release="atlas-db-scanner", value_files=TEST_VALUES)
    assert names(dupe, "CronJob") == {"atlas-db-scanner"}

    # No driver layer in the chart: no init container, sidecar, or driver
    # volume in the template, and no driver-shaped value key (the word may
    # appear in the comments citing DBS-01). 13.4's deliberate boundary.
    template_text = (CHART / "templates/cronjob.yaml").read_text()
    assert "initContainers" not in template_text
    assert "sidecar" not in template_text.lower()
    values = yaml.safe_load((CHART / "values.yaml").read_text())
    assert not [k for k in _walk_keys(values) if "driver" in k.lower()]


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
    """Bare SDK env var; the cert var joins only when the trust CA mounts (DD-210).

    The database's own TLS stays inside the DSN (CHT-123) — this leg's pin is
    the collector's, riding the same optional CA mount every other leg has.
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


def _walk_keys(node: object) -> Iterator[str]:
    """Every mapping key in a parsed values tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key)
            yield from _walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item)


def _pod(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """The CronJob's pod template spec (one CronJob per release, CHT-124)."""
    (cronjob,) = [d for d in docs if d["kind"] == "CronJob"]
    return cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]


def _container(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """The scanner container."""
    (app,) = _pod(docs)["containers"]
    return app

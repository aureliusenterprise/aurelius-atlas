"""Chart-contract suite for ``atlas-keycloak`` (CHT-16..18, 10.2).

Keycloak's cluster shape asserted at the render: prod-mode boot, the issuer
hostname chain, the RSS companion, the realm asset and its placeholder
resolution, the management-port probes, and the bundled Postgres — the cert-
copy boot, the pg_hba, the verify-full JDBC pin (the dev compose sibling is
the reference, ``dev/keycloak/docker-compose.yaml``).
"""

from typing import Any

import pytest
import yaml
from conftest import (
    KC_CHART,
    WORKSPACE,
    container,
    env_map,
    env_value,
    find,
    helm_render,
    helm_render_fails,
    names,
    pod_spec,
)


@pytest.mark.covers(rules=["CHT-16"])
def test__prod_mode_boot_and_workload_shapes(kc_docs: list[dict[str, Any]]) -> None:
    """``kc.sh start --import-realm``, never start-dev (CHT-16).

    StatefulSet + ClusterIP + the RSS headless Service for JGroups discovery.
    """
    ss = find(kc_docs, "StatefulSet", "atlas-keycloak")
    command = container(ss, "keycloak")["command"]
    assert "start" in command
    assert "--import-realm" in command
    assert not any("start-dev" in part for part in command)
    assert ss["spec"]["serviceName"] == "atlas-keycloak-rss"
    assert find(kc_docs, "Service", "atlas-keycloak")["spec"]["type"] == "ClusterIP"
    rss = find(kc_docs, "Service", "atlas-keycloak-rss")
    assert rss["spec"]["clusterIP"] == "None"
    assert rss["spec"]["publishNotReadyAddresses"] is True
    assert any("-Djgroups.dns.query=atlas-keycloak-rss" in part for part in command)


@pytest.mark.covers(rules=["CHT-16"])
def test__runs_as_image_uid_with_fs_group(kc_docs: list[dict[str, Any]]) -> None:
    """The pod runs the image's uid (65532), which owns the Quarkus build dir.

    DD-257: the hardened image does no privilege drop; `kc.sh start` re-augments
    in place, so a foreign uid cannot write it. fsGroup matches for the data.
    """
    ss = find(kc_docs, "StatefulSet", "atlas-keycloak")
    psc = pod_spec(ss)["securityContext"]
    assert psc["runAsNonRoot"] is True
    assert psc["runAsUser"] == 65532
    assert psc["fsGroup"] == 65532
    assert psc["seccompProfile"] == {"type": "RuntimeDefault"}


@pytest.mark.covers(rules=["CHT-16"])
def test__replicas_above_one_fails_render() -> None:
    """Multi-node Keycloak is a later increment, so replicas 2 fails the render."""
    error = helm_render_fails(KC_CHART, sets=("replicas=2",))
    assert "replicas > 1" in error


@pytest.mark.covers(rules=["CHT-16"])
def test__hostname_chain() -> None:
    """KC_HOSTNAME: explicit hostname, then issuer.url's host, then the domain."""

    def hostname(sets: tuple[str, ...]) -> str:
        ss = find(helm_render(KC_CHART, sets=sets), "StatefulSet", "atlas-keycloak")
        return env_value(env_map(container(ss, "keycloak")), "KC_HOSTNAME")

    assert hostname(("hostname=kc.example.com",)) == "kc.example.com"
    assert hostname(("global.issuer.url=https://auth.example.com/", "hostname=")) == "auth.example.com"
    assert hostname(("global.domain=atlas.example", "hostname=", "global.issuer.url=")) == "keycloak.atlas.example"


@pytest.mark.covers(rules=["CHT-16"])
def test__credentials_from_generated_secrets(kc_docs: list[dict[str, Any]]) -> None:
    """Every credential arrives via secretKeyRef, none inline (CHT-16/19).

    Admin, database, demo-user, and otel-client credentials point at the
    <release>-<purpose> Secret names the umbrella generates.
    """
    ss = find(kc_docs, "StatefulSet", "atlas-keycloak")
    envs = env_map(container(ss, "keycloak"))
    refs = {
        "KC_BOOTSTRAP_ADMIN_USERNAME": ("atlas-keycloak-admin", "user"),
        "KC_BOOTSTRAP_ADMIN_PASSWORD": ("atlas-keycloak-admin", "password"),
        "KC_DB_USERNAME": ("atlas-keycloak-database", "user"),
        "KC_DB_PASSWORD": ("atlas-keycloak-database", "password"),
        "DEV_USER_WRITER_PASSWORD": ("atlas-keycloak-users", "writer-password"),
        "DEV_USER_READER_PASSWORD": ("atlas-keycloak-users", "reader-password"),
        "OTEL_INGEST_CLIENT_SECRET": ("atlas-otel-clients", "OTEL_INGEST_CLIENT_SECRET"),
    }
    for name, (secret, key) in refs.items():
        ref = envs[name]["valueFrom"]["secretKeyRef"]
        assert ref == {"name": secret, "key": key}, name
        assert "value" not in envs[name], name


@pytest.mark.covers(rules=["CHT-16"])
def test__realm_configmap_byte_copies_the_dev_import(kc_docs: list[dict[str, Any]]) -> None:
    """The realm asset is byte-identical to the dev import (the drift guard).

    DD-256: one authored realm file; editing the dev import means re-running
    the copy, and this test is what enforces it.
    """
    cm = find(kc_docs, "ConfigMap", "atlas-keycloak-realm")
    asset = (KC_CHART / "files/master.json").read_bytes()
    assert cm["data"]["master.json"].encode() == asset
    dev_import = (WORKSPACE / "dev/keycloak/import/master.json").read_bytes()
    assert asset == dev_import


@pytest.mark.covers(rules=["CHT-16"])
def test__realm_mounts_at_import_dir_with_placeholder_flag(kc_docs: list[dict[str, Any]]) -> None:
    """The realm mounts at the import dir and Keycloak resolves the placeholders.

    The ``${...}`` secrets resolve via the JVM's own
    replace-placeholders flag (DD-256), never by Helm substitution.
    """
    ss = find(kc_docs, "StatefulSet", "atlas-keycloak")
    mount = next(vm for vm in container(ss, "keycloak")["volumeMounts"] if vm["name"] == "realm")
    assert mount["mountPath"] == "/opt/keycloak/data/import"
    volumes = {v["name"]: v for v in pod_spec(ss)["volumes"]}
    assert volumes["realm"]["configMap"]["name"] == "atlas-keycloak-realm"
    envs = env_map(container(ss, "keycloak"))
    assert "-Dkeycloak.migration.replace-placeholders=true" in env_value(envs, "JAVA_OPTS")


@pytest.mark.covers(rules=["CHT-16"])
def test__telemetry_renders_only_when_pointed_at_a_collector() -> None:
    """No endpoint means no telemetry env (CHT-16)."""
    bare = find(helm_render(KC_CHART), "StatefulSet", "atlas-keycloak")
    bare_envs = env_map(container(bare, "keycloak"))
    assert not [n for n in bare_envs if n.startswith("OTEL_EXPORTER") or n == "OTEL_SERVICE_NAME"]

    docs = helm_render(KC_CHART, sets=("telemetry.endpoint=https://collector:4320",))
    ss = find(docs, "StatefulSet", "atlas-keycloak")
    envs = env_map(container(ss, "keycloak"))
    assert env_value(envs, "OTEL_SERVICE_NAME") == "keycloak"
    assert env_value(envs, "OTEL_EXPORTER_OTLP_ENDPOINT") == "https://collector:4320"
    assert env_value(envs, "OTEL_EXPORTER_OTLP_CERTIFICATE") == "/etc/aurelius-atlas/tls/ca.crt"
    header = envs["OTEL_EXPORTER_OTLP_HEADERS"]["valueFrom"]["secretKeyRef"]
    assert header == {"name": "atlas-collector-legacy", "key": "otel-header"}


@pytest.mark.covers(rules=["CHT-16"])
def test__management_port_probes_and_tls_listener(kc_docs: list[dict[str, Any]]) -> None:
    """HTTPS management probes, TLS browser listener, no dev truststore (CHT-16).

    Prod mode puts TLS on the management interface too (DD-260), so the
    probes' scheme is HTTPS — the plaintext probe the dev healthcheck uses
    only worked on the compose's named relaxation (ADR 039).
    """
    ss = find(kc_docs, "StatefulSet", "atlas-keycloak")
    c = container(ss, "keycloak")
    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
        assert c[probe]["httpGet"]["port"] == "management"
        assert c[probe]["httpGet"]["path"] == "/health/ready"
        assert c[probe]["httpGet"]["scheme"] == "HTTPS"
    assert c["startupProbe"]["failureThreshold"] * c["startupProbe"]["periodSeconds"] >= 300
    ports = {p["name"]: p["containerPort"] for p in c["ports"]}
    assert ports == {"https": 8443, "management": 9000, "jgroups": 7800}
    envs = env_map(c)
    assert env_value(envs, "KC_HTTPS_CERTIFICATE_FILE") == "/etc/aurelius-atlas/tls/tls.crt"
    assert env_value(envs, "KC_HTTP_ENABLED") == "false"
    assert "trustStore" not in yaml.dump(ss)


@pytest.mark.covers(rules=["CHT-16"])
def test__certificate_covers_issuer_and_cluster_names() -> None:
    """The Certificate SANs are the issuer host plus the in-cluster names."""
    docs = helm_render(KC_CHART, sets=("global.domain=atlas.example",))
    cert = find(docs, "Certificate", "atlas-keycloak")
    sans = set(cert["spec"]["dnsNames"])
    assert "keycloak.atlas.example" in sans
    assert {"atlas-keycloak", "atlas-keycloak.atlas.svc.cluster.local", "atlas-keycloak-rss"} <= sans
    assert cert["spec"]["secretName"] == "atlas-keycloak-tls"


@pytest.mark.covers(rules=["CHT-17"])
def test__postgres_certificate_covers_probe_and_jdbc_names(kc_docs: list[dict[str, Any]]) -> None:
    """The database Certificate SANs are the JDBC names plus the probe's dial.

    The pg_isready probes dial 127.0.0.1 under verify-full, so the loopback
    address must be a SAN (DD-258 — the dev tls.json lists it for this).
    """
    cert = find(kc_docs, "Certificate", "atlas-keycloak-postgres")
    sans = set(cert["spec"]["dnsNames"])
    assert {"atlas-keycloak-postgres", "atlas-keycloak-postgres.atlas.svc.cluster.local"} <= sans
    assert cert["spec"]["ipAddresses"] == ["127.0.0.1"]


@pytest.mark.covers(rules=["CHT-16"])
def test__bundled_flavor_waits_for_the_database(kc_docs: list[dict[str, Any]]) -> None:
    """A wait-for-postgres init container ports the compose depends_on (DD-258)."""
    ss = find(kc_docs, "StatefulSet", "atlas-keycloak")
    inits = pod_spec(ss)["initContainers"]
    assert [c["name"] for c in inits] == ["wait-for-postgres"]
    script = " ".join(inits[0]["command"])
    assert "/dev/tcp/atlas-keycloak-postgres/5432" in script


@pytest.mark.covers(rules=["CHT-17"])
def test__bundled_postgres_boot(kc_docs: list[dict[str, Any]]) -> None:
    """The cert-copy boot, tmpfs /tmp, scram, and the shared Secret (CHT-17)."""
    ss = find(kc_docs, "StatefulSet", "atlas-keycloak-postgres")
    spec = pod_spec(ss)
    c = container(ss, "postgres")
    boot = c["command"][2]
    assert "mktemp -d" in boot
    assert "install -m 600 /certs/tls.crt" in boot
    assert "-c ssl=on" in boot
    assert "-c hba_file=/conf/pg_hba.conf" in boot
    volumes = {v["name"]: v for v in spec["volumes"]}
    assert volumes["tmp"]["emptyDir"].get("medium") == "Memory"
    assert volumes["certs"]["secret"]["secretName"] == "atlas-keycloak-postgres-tls"
    assert volumes["conf"]["configMap"]["name"] == "atlas-keycloak-postgres"
    envs = env_map(c)
    assert env_value(envs, "POSTGRES_HOST_AUTH_METHOD") == "scram-sha-256"
    assert envs["POSTGRES_USER"]["valueFrom"]["secretKeyRef"] == {"name": "atlas-keycloak-database", "key": "user"}
    assert env_value(envs, "POSTGRES_DB") == "keycloak"
    # The probes pin verify-full against the issuer CA.
    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
        script = " ".join(c[probe]["exec"]["command"])
        assert "PGSSLMODE=verify-full" in script, probe
        assert "pg_isready" in script, probe


@pytest.mark.covers(rules=["CHT-17"])
def test__pg_hba_and_jdbc_verify_full(kc_docs: list[dict[str, Any]]) -> None:
    """The pg_hba is local-trust + hostssl-scram; the JDBC URL pins verify-full."""
    cm = find(kc_docs, "ConfigMap", "atlas-keycloak-postgres")
    hba = cm["data"]["pg_hba.conf"]
    assert "local all all trust" in hba
    assert "hostssl all all all scram-sha-256" in hba
    ss = find(kc_docs, "StatefulSet", "atlas-keycloak")
    jdbc = env_value(env_map(container(ss, "keycloak")), "KC_DB_URL")
    assert jdbc.startswith("jdbc:postgresql://atlas-keycloak-postgres:5432/keycloak?")
    assert "sslmode=verify-full" in jdbc
    assert "sslrootcert=/etc/aurelius-atlas/tls/ca.crt" in jdbc


@pytest.mark.covers(rules=["CHT-17"])
def test__external_flavor_renders_no_postgres() -> None:
    """flavor=external drops every Postgres resource and takes the URL (CHT-17).

    The wait-for-postgres init is bundled-only too — an external database is
    somebody else's availability contract.
    """
    docs = helm_render(
        KC_CHART,
        sets=(
            "database.flavor=external",
            "database.url=jdbc:postgresql://db.example:5432/keycloak?sslmode=verify-full&sslrootcert=/etc/aurelius-atlas/tls/ca.crt",
        ),
    )
    ss = find(docs, "StatefulSet", "atlas-keycloak")
    assert "initContainers" not in pod_spec(ss)
    pg_names = {"atlas-keycloak-postgres", "atlas-keycloak-postgres-tls"}
    assert not pg_names & names(docs, "StatefulSet")
    assert not pg_names & names(docs, "Service")
    assert not pg_names & names(docs, "Certificate")
    ss = find(docs, "StatefulSet", "atlas-keycloak")
    jdbc = env_value(env_map(container(ss, "keycloak")), "KC_DB_URL")
    assert jdbc.startswith("jdbc:postgresql://db.example:5432/")

    error = helm_render_fails(KC_CHART, sets=("database.flavor=external",))
    assert "database.url" in error


@pytest.mark.covers(rules=["CHT-18"])
def test__pdbs_for_stateful_pair(kc_docs: list[dict[str, Any]]) -> None:
    """Keycloak and its database each get a minAvailable-1 PDB (CHT-18)."""
    for name in ("atlas-keycloak", "atlas-keycloak-postgres"):
        pdb = find(kc_docs, "PodDisruptionBudget", name)
        assert pdb["spec"]["minAvailable"] == 1


@pytest.mark.covers(rules=["CHT-18"])
def test__postgres_volume_claim_storage_class() -> None:
    """The PG claim omits storageClassName at "" and carries it when set."""
    bare = find(helm_render(KC_CHART), "StatefulSet", "atlas-keycloak-postgres")
    assert "storageClassName" not in bare["spec"]["volumeClaimTemplates"][0]["spec"]
    docs = helm_render(KC_CHART, sets=("global.storageClass=fast-ssd",))
    ss = find(docs, "StatefulSet", "atlas-keycloak-postgres")
    assert ss["spec"]["volumeClaimTemplates"][0]["spec"]["storageClassName"] == "fast-ssd"

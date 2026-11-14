"""Tenancy in the server chart and the standalone stack (WPT-08 to WPT-11, DD-579; 15.4, ADR 063).

The chart sets the server's tenancy settings and provisions the listed tenants with a hook Job whose pod never
receives the server's traffic; the standalone stack offers the setting, off by default.
"""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from conftest import SERVER_CHART, WORKSPACE, container, env_map, env_value, find, helm_render, helm_render_fails

SERVER_TEST_VALUES = (SERVER_CHART / "tests/values.test.yaml",)
JOB = "atlas-server-provision-tenants"
TENANTS = (
    "tenancy.enabled=true",
    "tenancy.tenants[0].alias=acme",
    "tenancy.tenants[1].alias=globex",
    "tenancy.tenants[1].trustsOperators=false",
)
TENANCY_ENV = (
    "AURELIUS_ATLAS_SERVER_TENANCY_ENABLED",
    "AURELIUS_ATLAS_SERVER_TENANCY_OPERATOR_ORGANIZATION",
    "AURELIUS_ATLAS_SERVER_TENANCY_REFRESH_SECONDS",
)


def render(*sets: str) -> list[dict[str, Any]]:
    """The server chart under its test values and the settings given."""
    return helm_render(SERVER_CHART, value_files=SERVER_TEST_VALUES, sets=sets)


@pytest.mark.covers(rules=["WPT-08"])
def test__tenancy_on_sets_the_servers_settings() -> None:
    """The Deployment's server is told tenancy is on, its operator organization and its refresh."""
    docs = render("tenancy.enabled=true", "tenancy.operatorOrganization=ops", "tenancy.refreshSeconds=10")
    envs = env_map(container(find(docs, "Deployment", "atlas-server"), "server"))
    assert [env_value(envs, name) for name in TENANCY_ENV] == ["true", "ops", "10"]


@pytest.mark.covers(rules=["WPT-08"])
def test__each_listed_tenant_is_provisioned_in_order_by_a_hook_job() -> None:
    """One init container per tenant, ``--existing-ok`` always, ``--no-operator-trust`` where trust is off; the
    main container lists the tenants; the Job runs after each install and upgrade with the server's settings.
    """  # noqa: D205 - one sentence
    job = find(render(*TENANTS), "Job", JOB)
    assert job["metadata"]["annotations"]["helm.sh/hook"] == "post-install,post-upgrade"
    spec = job["spec"]["template"]["spec"]
    commands = [init["command"][3:] for init in spec["initContainers"]]
    assert commands == [
        ["provision", "acme", "--existing-ok"],
        ["provision", "globex", "--existing-ok", "--no-operator-trust"],
    ]
    main = container(job, "list")
    assert main["command"] == ["python", "-m", "aurelius_atlas_server.provisioning", "list"]
    envs = env_map(spec["initContainers"][0])
    assert env_value(envs, "AURELIUS_ATLAS_SERVER_TENANCY_ENABLED") == "true"
    assert env_value(envs, "AURELIUS_ATLAS_SERVER_M4I_MODELS_ENABLED") == "true"
    assert envs["AURELIUS_ATLAS_SERVER_ELASTICSEARCH_PASSWORD"]["valueFrom"]["secretKeyRef"]["key"] == (
        "elastic-password"
    )


@pytest.mark.covers(rules=["WPT-08"])
@pytest.mark.parametrize(
    ("sets", "reason"),
    [
        (("tenancy.tenants[0].alias=acme",), "tenancy.tenants needs tenancy.enabled"),
        (("tenancy.enabled=true", "tenancy.tenants[0].alias=Acme"), "is no tenant alias"),
        (("tenancy.enabled=true", "tenancy.tenants[0].alias=operators"), "is the operator organization"),
    ],
)
def test__a_tenant_list_that_cannot_be_provisioned_fails_the_render(sets: tuple[str, ...], reason: str) -> None:
    """Tenants without tenancy, an alias that isn't index-safe, and the operator organization are refused."""
    assert reason in helm_render_fails(SERVER_CHART, value_files=SERVER_TEST_VALUES, sets=sets)


@pytest.mark.covers(rules=["WPT-09"])
def test__the_jobs_pod_reaches_the_store_but_the_service_never_selects_it() -> None:
    """The pod carries the server's name and instance, which the store admits, and its own component, which the
    Service's selector excludes while the server's pods match it.
    """  # noqa: D205 - one sentence
    docs = render(*TENANTS)
    pod = find(docs, "Job", JOB)["spec"]["template"]["metadata"]["labels"]
    server = find(docs, "Deployment", "atlas-server")["spec"]["template"]["metadata"]["labels"]
    selector = find(docs, "Service", "atlas-server")["spec"]["selector"]
    assert {"app.kubernetes.io/name": "atlas-server", "app.kubernetes.io/instance": "atlas"}.items() <= pod.items()
    assert selector.items() <= server.items()
    assert not selector.items() <= pod.items()


@pytest.mark.covers(rules=["WPT-11"])
def test__without_tenancy_the_chart_renders_no_job_and_no_setting() -> None:
    """The default values: no provisioning Job, no tenancy setting."""
    docs = render()
    assert not [doc for doc in docs if doc["kind"] == "Job"]
    envs = env_map(container(find(docs, "Deployment", "atlas-server"), "server"))
    assert not set(TENANCY_ENV) & set(envs)


@pytest.mark.covers(rules=["WPT-10"])
def test__the_standalone_stack_offers_tenancy_off_by_default() -> None:
    """``ATLAS_TENANCY_ENABLED`` sets the server's setting, false unless given."""
    compose = yaml.safe_load((WORKSPACE / "apps/aurelius-atlas-server/standalone/docker-compose.yaml").read_text())
    environment = compose["services"]["aurelius-atlas-server"]["environment"]
    assert environment["AURELIUS_ATLAS_SERVER_TENANCY_ENABLED"] == "${ATLAS_TENANCY_ENABLED:-false}"

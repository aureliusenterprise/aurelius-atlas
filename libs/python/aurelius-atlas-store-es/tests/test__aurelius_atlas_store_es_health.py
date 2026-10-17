from typing import cast

import pytest
from aurelius_atlas_store_es import HealthReport, HealthStatus, check_health
from aurelius_atlas_store_es.testing.fake import FakeClient, response_meta
from elasticsearch import AsyncElasticsearch, AuthenticationException, ConnectionTimeout
from elasticsearch import ConnectionError as TransportConnectionError


def as_client(fake: FakeClient) -> AsyncElasticsearch:
    """Type the fake as the client ``check_health`` expects."""
    return cast("AsyncElasticsearch", fake)


@pytest.mark.parametrize(("cluster_status", "expected"), [("green", HealthStatus.UP), ("yellow", HealthStatus.UP)])
async def test__check_health_is_up_for_green_and_yellow(cluster_status: str, expected: HealthStatus) -> None:
    """STO-05, STO-07: green and yellow are up, and the report names the cluster and version."""
    fake = FakeClient()
    fake.cluster_status = cluster_status

    report = await check_health(as_client(fake))

    assert report == HealthReport(
        status=expected, cluster_name="aurelius-atlas", version="9.5.5", cluster_status=cluster_status
    )


async def test__check_health_is_down_for_red() -> None:
    """STO-05, STO-07: red is down, and the server details are still reported."""
    fake = FakeClient()
    fake.cluster_status = "red"

    report = await check_health(as_client(fake))

    assert report == HealthReport(
        status=HealthStatus.DOWN,
        cluster_name="aurelius-atlas",
        version="9.5.5",
        cluster_status="red",
        reason="cluster status is red",
    )


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (TransportConnectionError("connection refused"), "server unreachable (ConnectionError)"),
        (ConnectionTimeout("timed out"), "server unreachable (ConnectionTimeout)"),
        (AuthenticationException("unauthorized", response_meta(401), {}), "request rejected with status 401"),
        (ValueError("unexpected"), "unexpected error (ValueError)"),
    ],
)
@pytest.mark.parametrize("failing_call", ["info", "health"])
async def test__check_health_never_raises(error: Exception, reason: str, failing_call: str) -> None:
    """STO-06: any failure to ask the server is reported as down with the reason."""
    fake = FakeClient()
    if failing_call == "info":
        fake.info_error = error
    else:
        fake.health_error = error

    report = await check_health(as_client(fake))

    assert report == HealthReport(status=HealthStatus.DOWN, reason=reason)


async def test__check_health_report_contains_no_password(password: str) -> None:
    """STO-08: a failure message from the transport does not leak into the report as the password."""
    fake = FakeClient()
    fake.info_error = TransportConnectionError(f"https://elastic:{password}@localhost:9200 refused")

    report = await check_health(as_client(fake))

    assert password not in report.model_dump_json()

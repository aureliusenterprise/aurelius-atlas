import logging
from enum import StrEnum

from elasticsearch import ApiError, AsyncElasticsearch, TransportError
from pydantic import BaseModel, ConfigDict

LOGGER = logging.getLogger(__name__)

HEALTHY_CLUSTER_STATUSES = frozenset({"green", "yellow"})
"""Cluster statuses that count as up; yellow is healthy on a single node (DD-008)."""


class HealthStatus(StrEnum):
    """Whether the store can serve requests."""

    UP = "up"
    DOWN = "down"


class HealthReport(BaseModel):
    """The outcome of one health check.

    The server fields are filled whenever the server answered (STO-07); ``reason`` explains a
    ``DOWN`` status. The report never contains credentials (STO-08).
    """

    model_config = ConfigDict(frozen=True)

    status: HealthStatus
    cluster_name: str | None = None
    version: str | None = None
    cluster_status: str | None = None
    reason: str | None = None


async def check_health(client: AsyncElasticsearch) -> HealthReport:
    """Ask the cluster for its health, without ever raising (STO-06).

    Args:
        client: An open Elasticsearch client.

    Returns:
        ``UP`` when the cluster status is green or yellow, ``DOWN`` when it is red or the server
        could not be asked (STO-05, STO-06).
    """
    try:
        info = await client.info()
        health = await client.cluster.health()
    except ApiError as error:
        LOGGER.warning("Elasticsearch health check was rejected with status %s", error.meta.status)
        return HealthReport(status=HealthStatus.DOWN, reason=f"request rejected with status {error.meta.status}")
    except TransportError as error:
        LOGGER.warning("Elasticsearch health check could not reach the server: %s", type(error).__name__)
        return HealthReport(status=HealthStatus.DOWN, reason=f"server unreachable ({type(error).__name__})")
    except Exception as error:
        LOGGER.exception("Elasticsearch health check failed unexpectedly")
        return HealthReport(status=HealthStatus.DOWN, reason=f"unexpected error ({type(error).__name__})")

    cluster_status = str(health["status"])
    healthy = cluster_status in HEALTHY_CLUSTER_STATUSES

    return HealthReport(
        status=HealthStatus.UP if healthy else HealthStatus.DOWN,
        cluster_name=str(info["cluster_name"]),
        version=str(info["version"]["number"]),
        cluster_status=cluster_status,
        reason=None if healthy else f"cluster status is {cluster_status}",
    )

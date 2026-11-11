"""The Schema Registry door: a subject's latest schema, and a schema by its id (13.1, KSC-04, KSC-05, DD-465).

The Registry speaks a plain JSON REST API (Confluent's wire REST, at ``/subjects`` and
``/schemas/ids/{id}``). The door speaks it over ``httpx2`` with the job's CA file (KSC-10) —
no client library, because one JSON document per subject is the whole contract (DD-465).

The door answers ``None`` for "the Registry holds no answer here" — an absent subject, an absent
id, a Registry the settings do not name. That is not a failure: KSC-04 moves such a topic to the
sniff, and KSC-05 lets it land field-less. A Registry that is there and refuses (a 5xx, an
unreachable host) is the job's own failure to reach a configured door, and raises.
"""

import ssl
from dataclasses import dataclass
from typing import Protocol

import httpx2 as httpx


@dataclass(frozen=True)
class SubjectSchema:
    """The latest version of a subject (KSC-04): its type text and the schema's own type name."""

    schema_type: str
    """The schema type as the Registry spells it: ``AVRO`` or ``JSON`` reach the parsers (KSC-04)."""

    schema_str: str
    """The schema text: the Avro definition or the JSON schema document."""


class RegistryDoor(Protocol):
    """What the scan asks the Registry (KSC-04, KSC-05)."""

    async def latest(self, subject: str) -> SubjectSchema | None:
        """The subject's latest schema, or ``None`` when the Registry holds no such subject."""
        ...

    async def by_id(self, schema_id: int) -> SubjectSchema | None:
        """The schema registered under ``schema_id``, or ``None`` when the Registry holds no such id."""
        ...


class SchemaRegistry:
    """The Registry door over its REST API (DD-465).

    Args:
        base_url: The Registry's URL; ``None`` builds a door that answers ``None`` everywhere
            (KSC-04: no Registry, every topic is sniffed).
        ca_file: The PEM CA the Registry's TLS certificate is verified against (KSC-10).
        timeout_seconds: How long one request waits (KSC-04).
    """

    def __init__(
        self,
        base_url: str | None,
        *,
        ca_file: str | None = None,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client: httpx.AsyncClient | None = None
        if base_url is not None:
            verify: ssl.SSLContext | bool = ssl.create_default_context(cafile=ca_file) if ca_file else True
            self._client = httpx.AsyncClient(
                base_url=base_url, verify=verify, timeout=timeout_seconds, transport=transport
            )

    async def latest(self, subject: str) -> SubjectSchema | None:
        """The subject's latest schema (KSC-04): ``GET /subjects/{subject}/versions/latest``.

        A 404 is "no such subject" and answers ``None``; any other refusal raises — a Registry
        that is configured and angry is not "absent".
        """
        if self._client is None:
            return None
        response = await self._client.get(f"/subjects/{subject}/versions/latest")
        if response.status_code == httpx.codes.NOT_FOUND:
            return None
        response.raise_for_status()
        return _to_schema(response.json())

    async def by_id(self, schema_id: int) -> SubjectSchema | None:
        """The schema with ``schema_id`` (KSC-05): ``GET /schemas/ids/{id}``.

        The reply carries only ``schema`` (and its type on a recent Registry); an absent id is a
        404 and answers ``None``.
        """
        if self._client is None:
            return None
        response = await self._client.get(f"/schemas/ids/{schema_id}")
        if response.status_code == httpx.codes.NOT_FOUND:
            return None
        response.raise_for_status()
        return _to_schema(response.json())

    async def close(self) -> None:
        """Close the connection pool."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def _to_schema(payload: object) -> SubjectSchema:
    """The Registry's JSON answer to the door's record; a type it does not name reads as ``AVRO``.

    The by-id reply of an older Registry carries no ``schemaType``; the subject replies always do.
    A text with no type name is read as the type the Registry stores by default.
    """
    body = payload if isinstance(payload, dict) else {}
    schema_str = str(body.get("schema", ""))
    schema_type = str(body.get("schemaType") or "AVRO")
    return SubjectSchema(schema_type=schema_type, schema_str=schema_str)

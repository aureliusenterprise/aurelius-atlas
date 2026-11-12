"""The stored type definitions: one Elasticsearch document, written with optimistic concurrency (DD-028, DD-029)."""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from aurelius_atlas_model.patches import AtlasPatch
from aurelius_atlas_model.typedef import AtlasTypesDef
from elasticsearch import ApiError, AsyncElasticsearch, ConflictError, NotFoundError

TYPEDEF_INDEX = "aurelius-atlas-typedefs"
"""The alias of the index that holds the type definitions."""

TYPEDEF_DOCUMENT_ID = "typedefs"
"""The id of the one document that holds every type definition."""

INDEX_SETTINGS: dict[str, Any] = {"index.auto_expand_replicas": "0-1"}
"""The settings of every index the server keeps (IDX-02, DD-323): a replica when the cluster has a node to hold
it, none on a single node, whose indices are then green, not yellow."""

ALREADY_EXISTS = "resource_already_exists_exception"
"""What Elasticsearch calls a create of an index that exists, the answer two servers booting on one store trade
when both make the same index (DD-508)."""


async def ensure_index(
    client: AsyncElasticsearch,
    *,
    index: str,
    aliases: dict[str, Any] | None = None,
    mappings: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
) -> bool:
    """Create ``index`` unless it exists; whether this call made it (DD-508).

    Two servers that share a store make the same indices as they start, from the same definitions. A create that
    loses to the other server's identical one answers ``resource_already_exists_exception``, which is success for
    both: the index stands, made whole by whoever got there first. Any other answer raises.
    """
    try:
        await client.indices.create(index=index, aliases=aliases, mappings=mappings, settings=settings)
    except ApiError as error:
        if ALREADY_EXISTS not in repr(error.body):
            raise
        return False
    return True


@dataclass(frozen=True)
class DocumentVersion:
    """Which write of the document a reader saw: Elasticsearch's ``_seq_no`` and ``_primary_term`` (TDS-11)."""

    seq_no: int
    primary_term: int


@dataclass
class StoredTypedefs:
    """What the document holds: the definitions, and the record of each typedef patch (DD-028, DD-031)."""

    types_def: AtlasTypesDef
    patches: list[AtlasPatch] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        """The document's source: ``typesDef`` and ``patches``."""
        return {"typesDef": self.types_def.to_json(), "patches": [patch.to_json() for patch in self.patches]}

    @classmethod
    def from_json(cls, source: dict[str, Any]) -> StoredTypedefs:
        """Read a document's source; one written before 1.5 has no ``patches``."""
        return cls(
            AtlasTypesDef.model_validate(source["typesDef"]),
            [AtlasPatch.model_validate(patch) for patch in source.get("patches", [])],
        )


class VersionConflictError(Exception):
    """Another process wrote the document since this one read it (TDS-11)."""


@runtime_checkable
class TypedefDocument(Protocol):
    """Where the type definitions are kept."""

    async def prepare(self) -> None:
        """Make sure the definitions can be read and written, such as by creating an index."""
        ...

    async def read(self) -> tuple[StoredTypedefs | None, DocumentVersion | None]:
        """The stored definitions and their version; ``(None, None)`` when nothing is stored."""
        ...

    async def version(self) -> DocumentVersion | None:
        """The version of the stored definitions, without reading them."""
        ...

    async def write(self, stored: StoredTypedefs, expected: DocumentVersion | None) -> DocumentVersion:
        """Replace the stored definitions, if they are still at ``expected``.

        Raises:
            VersionConflictError: The stored definitions changed since ``expected`` was read.
        """
        ...


class ElasticsearchTypedefDocument:
    """The type definitions as one document of the ``aurelius-atlas-typedefs`` index (DD-028)."""

    def __init__(self, client: AsyncElasticsearch, index: str = TYPEDEF_INDEX) -> None:
        self._client = client
        self._index = index

    async def prepare(self) -> None:
        """Create the index behind the alias unless it exists; the document itself is not searched.

        An existing index gets the settings of a new one, as its replicas (IDX-02). A create lost to a server
        booting on the same store takes that path too (DD-508).
        """
        if not await self._client.indices.exists_alias(name=self._index):
            made = await ensure_index(
                self._client,
                index=f"{self._index}-000001",
                aliases={self._index: {"is_write_index": True}},
                mappings={"dynamic": False, "properties": {}},
                settings={"number_of_shards": 1} | INDEX_SETTINGS,
            )
            if made:
                return
        await self._client.indices.put_settings(index=self._index, settings=INDEX_SETTINGS)

    async def read(self) -> tuple[StoredTypedefs | None, DocumentVersion | None]:
        """The stored definitions and their version; ``(None, None)`` when nothing is stored (TDS-12)."""
        try:
            response = await self._client.get(index=self._index, id=TYPEDEF_DOCUMENT_ID)
        except NotFoundError:
            return None, None
        source: dict[str, Any] = response["_source"]
        return StoredTypedefs.from_json(source), _version_of(response)

    async def version(self) -> DocumentVersion | None:
        """The version of the stored definitions, or None when nothing is stored (TDS-13)."""
        try:
            response = await self._client.get(index=self._index, id=TYPEDEF_DOCUMENT_ID, source=False)
        except NotFoundError:
            return None
        return _version_of(response)

    async def write(self, stored: StoredTypedefs, expected: DocumentVersion | None) -> DocumentVersion:
        """Replace the stored definitions if they are still at ``expected``; create them when it is None (TDS-11).

        Raises:
            VersionConflictError: Another process wrote the document first.
        """
        document = stored.to_json()
        try:
            if expected is None:
                response = await self._client.index(
                    index=self._index, id=TYPEDEF_DOCUMENT_ID, document=document, op_type="create", refresh=True
                )
            else:
                response = await self._client.index(
                    index=self._index,
                    id=TYPEDEF_DOCUMENT_ID,
                    document=document,
                    if_seq_no=expected.seq_no,
                    if_primary_term=expected.primary_term,
                    refresh=True,
                )
        except ConflictError as error:
            raise VersionConflictError from error
        return _version_of(response)


def _version_of(response: Any) -> DocumentVersion:  # noqa: ANN401 - an Elasticsearch response
    return DocumentVersion(seq_no=int(response["_seq_no"]), primary_term=int(response["_primary_term"]))

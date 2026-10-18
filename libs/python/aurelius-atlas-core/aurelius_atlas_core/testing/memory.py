"""A ``TypedefDocument`` in memory, for unit tests that need no Elasticsearch."""

from aurelius_atlas_model.typedef import AtlasTypesDef

from aurelius_atlas_core.typedef_document import DocumentVersion, VersionConflictError


class MemoryTypedefDocument:
    """Keeps the definitions as JSON, as Elasticsearch would, with a version per write.

    Set ``fail_next_write`` to make the next write raise, or ``conflicts`` to make that many writes conflict.
    """

    def __init__(self) -> None:
        self.json: dict[str, object] | None = None
        self.seq_no = -1
        self.prepared = False
        self.writes = 0
        self.conflicts = 0
        self.fail_next_write: BaseException | None = None

    async def prepare(self) -> None:
        """Record the call."""
        self.prepared = True

    async def read(self) -> tuple[AtlasTypesDef | None, DocumentVersion | None]:
        """The stored definitions and their version."""
        if self.json is None:
            return None, None
        return AtlasTypesDef.model_validate(self.json), DocumentVersion(self.seq_no, 1)

    async def version(self) -> DocumentVersion | None:
        """The version of the stored definitions."""
        return None if self.json is None else DocumentVersion(self.seq_no, 1)

    async def write(self, types_def: AtlasTypesDef, expected: DocumentVersion | None) -> DocumentVersion:
        """Store the definitions if they are at ``expected``."""
        if self.fail_next_write is not None:
            error, self.fail_next_write = self.fail_next_write, None
            raise error
        if self.conflicts:
            self.conflicts -= 1
            raise VersionConflictError
        if expected != await self.version():
            raise VersionConflictError
        self.writes += 1
        self.seq_no += 1
        self.json = types_def.to_json()
        return DocumentVersion(self.seq_no, 1)

    def store(self, types_def: AtlasTypesDef) -> None:
        """Put definitions in place, as another process would."""
        self.seq_no += 1
        self.json = types_def.to_json()

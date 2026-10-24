"""``HardDeleteHandler``: entities are removed, and references to them with them (EDL-06, EDL-07)."""

from aurelius_atlas_core.delete_handler import DeleteHandler
from aurelius_atlas_core.stored_entity import StoredEntity


class HardDeleteHandler(DeleteHandler):
    """``HardDeleteHandlerV1``: what a hard delete and a purge do."""

    soft = False

    def _delete_vertex(self, stored: StoredEntity) -> StoredEntity | None:  # noqa: ARG002 - a removed entity has no state
        """``_deleteVertex``: removed."""
        return None

"""``SoftDeleteHandler``: entities are marked ``DELETED`` and kept (EDL-06)."""

from aurelius_atlas_model.instance import EntityStatus

from aurelius_atlas_core.delete_handler import DeleteHandler
from aurelius_atlas_core.stored_entity import StoredEntity


class SoftDeleteHandler(DeleteHandler):
    """``SoftDeleteHandlerV1``: references to deleted entities stay, as soft-deleted edges do."""

    soft = True

    def _delete_vertex(self, stored: StoredEntity) -> StoredEntity:
        """``_deleteVertex``: ``DELETED``, changed now; an entity already ``DELETED`` stays as it is."""
        if stored.state is EntityStatus.DELETED:
            return stored
        return stored.model_copy(update={"state": EntityStatus.DELETED}).touched(now=self.now, user=self.user)

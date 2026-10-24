"""``AtlasEntityHeaders``: entity headers by GUID, the body of ``/v2/entity/bulk/headers`` (ENT-16)."""

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.instance.entity_header import AtlasEntityHeader


class AtlasEntityHeaders(AtlasModel):
    """``guidHeaderMap``: the header of each entity, by GUID."""

    guid_header_map: dict[str, AtlasEntityHeader] | None = None

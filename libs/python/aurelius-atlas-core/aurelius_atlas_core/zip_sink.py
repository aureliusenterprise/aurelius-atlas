"""``ZipSink``: an export's ZIP: each entity as ``<guid>.json``, then its order, types and result (EXP-06)."""

import io
import zipfile
from collections.abc import Sequence

from aurelius_atlas_model import codec
from aurelius_atlas_model.impexp import AtlasExportResult
from aurelius_atlas_model.instance import AtlasEntityWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef

ATLAS_EXPORT_INFO_NAME = "atlas-export-info"
ATLAS_EXPORT_ORDER_NAME = "atlas-export-order"
ATLAS_TYPESDEF_NAME = "atlas-typesdef"
"""``ZipExportFileNames``."""
FILE_EXTENSION_JSON = ".json"


class ZipSink:
    """``ZipSink``: the entries written, deflated, as ``ZipOutputStream`` writes them."""

    def __init__(self) -> None:
        self._buffer = io.BytesIO()
        self._zip = zipfile.ZipFile(self._buffer, "w", compression=zipfile.ZIP_DEFLATED)
        self.guids: set[str] = set()

    def add(self, found: AtlasEntityWithExtInfo) -> None:
        """``add``: the entity with what it owns, under its GUID; their GUIDs recorded."""
        guid = "" if found.entity is None else str(found.entity.guid)
        self._save(guid, found.to_json())
        self.guids.add(guid)
        self.guids.update(found.referred_entities or {})

    def set_result(self, result: AtlasExportResult) -> None:
        """``setResult``: ``atlas-export-info.json``."""
        self._save(ATLAS_EXPORT_INFO_NAME, result.to_json())

    def set_types_def(self, types_def: AtlasTypesDef | None) -> None:
        """``setTypesDef``: ``atlas-typesdef.json``."""
        self._save(ATLAS_TYPESDEF_NAME, None if types_def is None else types_def.to_json())

    def set_export_order(self, order: Sequence[str]) -> None:
        """``setExportOrder``: ``atlas-export-order.json``."""
        self._save(ATLAS_EXPORT_ORDER_NAME, list(order))

    def has_entity(self, guid: str) -> bool:
        """``hasEntity``: whether an entity of the GUID, or one an added entity owns, was added."""
        return guid in self.guids

    def close(self) -> bytes:
        """``close``: the finished ZIP's bytes."""
        self._zip.close()
        return self._buffer.getvalue()

    def _save(self, name: str, value: object) -> None:
        self._zip.writestr(name + FILE_EXTENSION_JSON, codec.dumps(value))

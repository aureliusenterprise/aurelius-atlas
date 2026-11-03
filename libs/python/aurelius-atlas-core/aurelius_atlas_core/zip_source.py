"""``ZipSource``: the entries of an export's ZIP, read for an import (IMS-02).

The export's result, its types and the order of its entities, then each entity as ``<guid>.json``, read in that
order from a starting position.
"""

import io
import json
import zipfile
from typing import Any

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.impexp import AtlasExportResult
from aurelius_atlas_model.instance import AtlasEntityWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef

from aurelius_atlas_core.import_transforms import ImportTransforms
from aurelius_atlas_core.zip_sink import ATLAS_EXPORT_INFO_NAME, ATLAS_EXPORT_ORDER_NAME, ATLAS_TYPESDEF_NAME

EMPTY_ZIP = "Attempting to import empty ZIP."


class ZipSource:
    """``ZipSource`` of the ZIP's bytes.

    Raises:
        AtlasError: ``IMPORT_ATTEMPTING_EMPTY_ZIP`` for a ZIP of no entries, or of an empty export order; a file
            that is no ZIP counts as one of no entries.
    """

    def __init__(self, content: bytes) -> None:
        self._entries: dict[str, str] = {}
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                for name in archive.namelist():
                    key = name.replace(".json", "")
                    self._entries.setdefault(key, archive.read(name).decode("utf-8", errors="replace"))
        except zipfile.BadZipFile:
            self._entries = {}
        if not self._entries or self._entries.get(ATLAS_EXPORT_ORDER_NAME) == "[]":
            raise AtlasError(AtlasErrorCode.IMPORT_ATTEMPTING_EMPTY_ZIP, EMPTY_ZIP)
        order = self._json(ATLAS_EXPORT_ORDER_NAME)
        self.creation_order: list[str] = [str(guid) for guid in order] if isinstance(order, list) else []
        self._position = 0
        self.position = 0
        """``getPosition``: how many entities were read."""
        self.import_transform: ImportTransforms | None = None
        """``setImportTransform``: the transforms each entity read goes through (ITR-01)."""

    def types_def(self) -> AtlasTypesDef:
        """``getTypesDef``: the export's types, none when the ZIP holds none."""
        found = self._json(ATLAS_TYPESDEF_NAME)
        return AtlasTypesDef.model_validate(found) if isinstance(found, dict) else AtlasTypesDef()

    def export_result(self) -> AtlasExportResult | None:
        """``getExportResult``: the export's result, or None."""
        found = self._json(ATLAS_EXPORT_INFO_NAME)
        return AtlasExportResult.model_validate(found) if isinstance(found, dict) else None

    def has_next(self) -> bool:
        """``hasNext``: whether an entity is left in the export order."""
        return self._position < len(self.creation_order)

    def next_entity_with_ext_info(self) -> AtlasEntityWithExtInfo | None:
        """``getNextEntityWithExtInfo``: the next entity of the order, or None for one the ZIP does not hold."""
        guid = self.creation_order[self._position]
        self._position += 1
        self.position += 1
        found = self._json(guid)
        entity = AtlasEntityWithExtInfo.model_validate(found) if isinstance(found, dict) else None
        return entity if self.import_transform is None else self.import_transform.apply(entity)

    def set_position(self, index: int) -> None:
        """``setPosition``: the entities up to and with ``index`` skipped."""
        self.position = index
        self._position = 0
        for guid in self.creation_order[: index + 1]:
            self._position += 1
            self.on_import_complete(guid)

    def set_position_using_entity_guid(self, guid: str | None) -> None:
        """``setPositionUsingEntityGuid``: from the entity after the one of ``guid``, when the order holds it."""
        if guid and guid.strip() and guid in self.creation_order:
            self.set_position(self.creation_order.index(guid))

    def on_import_complete(self, guid: str) -> None:
        """``onImportComplete``: the entity's entry let go."""
        self._entries.pop(guid, None)

    def size(self) -> int:
        """``size``: how many entities the export order names."""
        return len(self.creation_order)

    def _json(self, name: str) -> Any:  # noqa: ANN401 - a JSON value
        text = self._entries.get(name)
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError as error:
            raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, "Error converting file to JSON.") from error

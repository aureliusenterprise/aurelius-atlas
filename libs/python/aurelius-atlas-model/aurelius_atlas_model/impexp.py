"""``AtlasExportRequest`` and ``AtlasExportResult``: what an export is asked for and what it answers (EXP-01, EXP-02).

Atlas writes both with ``NON_NULL``: an absent field is left out, an empty list or map kept.
"""

from enum import StrEnum
from typing import Any

from pydantic import Field

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.instance import AtlasObjectId
from aurelius_atlas_model.typedef import AtlasTypesDef

OPTION_FETCH_TYPE = "fetchType"
OPTION_ATTR_MATCH_TYPE = "matchType"
OPTION_SKIP_LINEAGE = "skipLineage"
OPTION_KEY_REPLICATED_TO = "replicatedTo"
FETCH_TYPE_FULL = "full"
FETCH_TYPE_CONNECTED = "connected"
FETCH_TYPE_INCREMENTAL = "incremental"
FETCH_TYPE_INCREMENTAL_CHANGE_MARKER = "changeMarker"
MATCH_TYPE_STARTS_WITH = "startsWith"
MATCH_TYPE_ENDS_WITH = "endsWith"
MATCH_TYPE_CONTAINS = "contains"
MATCH_TYPE_MATCHES = "matches"
MATCH_TYPE_FOR_TYPE = "forType"
OMIT_ZIP_RESPONSE_FOR_EMPTY_EXPORT = "omitZipResponseForEmptyExport"


class AtlasExportRequest(AtlasModel):
    """``AtlasExportRequest``: the entities to start from and the options of the export."""

    items_to_export: list[AtlasObjectId] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)

    def fetch_type(self) -> str:
        """``getFetchTypeOptionValue``: the ``fetchType`` option when it is text, else ``full``."""
        value = self.options.get(OPTION_FETCH_TYPE)
        return value if isinstance(value, str) else FETCH_TYPE_FULL

    def skip_lineage(self) -> bool:
        """``getSkipLineageOptionValue``: the ``skipLineage`` option, a boolean or ``true`` in any case."""
        value = self.options.get(OPTION_SKIP_LINEAGE)
        if isinstance(value, str):
            return value.lower() == "true"
        return value is True

    def match_type(self) -> str | None:
        """``getMatchTypeOptionValue``: the ``matchType`` option's text, or None."""
        value = self.options.get(OPTION_ATTR_MATCH_TYPE)
        return None if value is None else _java_text(value)

    def change_marker(self) -> int:
        """``getChangeTokenFromOptions``: the ``changeMarker`` of an incremental export, else 0.

        Raises:
            ValueError: for a marker that is not a whole number (Java's ``NumberFormatException``).
        """
        if (
            self.fetch_type().lower() != FETCH_TYPE_INCREMENTAL
            or FETCH_TYPE_INCREMENTAL_CHANGE_MARKER not in self.options
        ):
            return 0
        return int(_java_text(self.options[FETCH_TYPE_INCREMENTAL_CHANGE_MARKER]))

    def omit_zip_response_for_empty_export(self) -> bool:
        """``getOmitZipResponseForEmptyExport``: the option, a boolean or ``true`` in any case."""
        value = self.options.get(OMIT_ZIP_RESPONSE_FOR_EMPTY_EXPORT)
        if isinstance(value, str):
            return value.lower() == "true"
        return value is True


class OperationStatus(StrEnum):
    """``AtlasExportResult.OperationStatus``."""

    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAIL = "FAIL"


class AtlasExportData(AtlasModel):
    """``AtlasExportData``: the type definitions an export collected, and the order it added entities in."""

    types_def: AtlasTypesDef = Field(default_factory=AtlasTypesDef)
    entity_creation_order: list[str] | None = None


class AtlasExportResult(AtlasModel):
    """``AtlasExportResult``: who exported what, when, from where, its counts and status (EXP-06)."""

    request: AtlasExportRequest | None = None
    user_name: str | None = None
    client_ip_address: str | None = None
    host_name: str | None = None
    time_stamp: int = 0
    metrics: dict[str, int] = Field(default_factory=dict)
    data: AtlasExportData | None = Field(default_factory=AtlasExportData)
    operation_status: OperationStatus = OperationStatus.FAIL
    source_cluster_name: str | None = None
    change_marker: int = 0

    def increment_metrics_counter(self, key: str, increment_by: int = 1) -> None:
        """``incrementMeticsCounter``: add to the count of ``key``."""
        self.metrics[key] = self.metrics.get(key, 0) + increment_by


def _java_text(value: object) -> str:
    """``Object.toString`` of an option's JSON value."""
    return java_string(value)


TRANSFORMS_KEY = "transforms"
TRANSFORMERS_KEY = "transformers"
OPTION_KEY_REPLICATED_FROM = "replicatedFrom"
OPTION_KEY_MIGRATION = "migration"
START_GUID_KEY = "startGuid"
FILE_NAME_KEY = "fileName"
START_POSITION_KEY = "startPosition"
UPDATE_TYPE_DEFINITION_KEY = "updateTypeDefinition"


class AtlasImportRequest(AtlasModel):
    """``AtlasImportRequest``: an import's options, each a text (IMS-01)."""

    options: dict[str, Any] = Field(default_factory=dict)

    def option(self, key: str) -> str | None:
        """``getOptionForKey``: the option's text, or None when it is not given."""
        value = self.options.get(key)
        return None if key not in self.options else (None if value is None else _java_text(value))

    def is_replication_option_set(self) -> bool:
        """``isReplicationOptionSet``: whether ``replicatedFrom`` is given."""
        return OPTION_KEY_REPLICATED_FROM in self.options


class AtlasImportResult(AtlasModel):
    """``AtlasImportResult``: who imported, when, from where, its counts, the entities it wrote and its status."""

    request: AtlasImportRequest | None = None
    user_name: str | None = None
    client_ip_address: str | None = None
    host_name: str | None = None
    time_stamp: int = 0
    metrics: dict[str, int] = Field(default_factory=dict)
    processed_entities: list[str] = Field(default_factory=list)
    operation_status: OperationStatus = OperationStatus.FAIL
    export_result: AtlasExportResult | None = None

    def increment_metrics_counter(self, key: str, increment_by: int = 1) -> None:
        """``incrementMeticsCounter``: add to the count of ``key``."""
        self.metrics[key] = self.metrics.get(key, 0) + increment_by

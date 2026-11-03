"""The export request's options, the result's counters and the replication models (EXP-02, EXP-06, REP-01 to REP-04).

Read from ``AtlasExportRequest`` (``getFetchTypeOptionValue``, ``getSkipLineageOptionValue``,
``getMatchTypeOptionValue``, ``getChangeTokenFromOptions``, ``getOmitZipResponseForEmptyExport``) and
``AtlasExportResult#incrementMeticsCounter`` of Apache Atlas 2.4.0.
"""

import pytest
from aurelius_atlas_model.impexp import (
    AtlasExportRequest,
    AtlasExportResult,
    AtlasImportRequest,
    AtlasImportResult,
    AtlasServer,
    ExportImportAuditEntry,
    replicated,
    skip_update_replication_attr,
)

R = "aurelius_atlas_model.impexp.AtlasExportRequest"


def request(**options: object) -> AtlasExportRequest:
    """A request of these options."""
    return AtlasExportRequest.model_validate({"itemsToExport": [], "options": options})


@pytest.mark.covers(
    f"{R}.fetch_type",
    f"{R}.skip_lineage",
    f"{R}.match_type",
    f"{R}.change_marker",
    f"{R}.omit_zip_response_for_empty_export",
    rules=["EXP-02"],
)
def test__the_options_are_read_as_atlas_reads_them() -> None:
    """Text fetch types, boolean or text flags, a marker only of an incremental export."""
    assert request().fetch_type() == "full"
    assert request(fetchType=1).fetch_type() == "full"
    assert request(fetchType="CONNECTED").fetch_type() == "CONNECTED"
    assert (request(skipLineage="TRUE").skip_lineage(), request(skipLineage=True).skip_lineage()) == (True, True)
    assert (request(skipLineage="yes").skip_lineage(), request(skipLineage=1).skip_lineage()) == (False, False)
    assert (request().match_type(), request(matchType="forType").match_type()) == (None, "forType")
    assert request(fetchType="incremental", changeMarker="15").change_marker() == 15
    assert request(fetchType="full", changeMarker=15).change_marker() == 0
    assert request(omitZipResponseForEmptyExport="true").omit_zip_response_for_empty_export() is True
    assert request().omit_zip_response_for_empty_export() is False
    with pytest.raises(ValueError, match="invalid literal"):
        request(fetchType="incremental", changeMarker="x").change_marker()


@pytest.mark.covers("aurelius_atlas_model.impexp.AtlasExportResult.increment_metrics_counter", rules=["EXP-06"])
def test__the_result_counts_by_key_and_leaves_out_what_it_lacks() -> None:
    """Counters add up; an absent field is left out, as ``NON_NULL`` writes it."""
    result = AtlasExportResult()
    result.increment_metrics_counter("entity:t")
    result.increment_metrics_counter("entity:t", 2)
    result.data = None

    assert result.to_json() == {
        "timeStamp": 0,
        "metrics": {"entity:t": 3},
        "operationStatus": "FAIL",
        "changeMarker": 0,
    }


@pytest.mark.covers(
    "aurelius_atlas_model.impexp.AtlasImportRequest.option",
    "aurelius_atlas_model.impexp.AtlasImportRequest.is_replication_option_set",
    "aurelius_atlas_model.impexp.AtlasImportResult.increment_metrics_counter",
    rules=["IMS-01"],
)
def test__the_import_request_reads_its_options_as_text() -> None:
    """``getOptionForKey``: the option's text, None when absent; the result counts by key."""
    request = AtlasImportRequest.model_validate({"options": {"startPosition": 2, "updateTypeDefinition": True}})
    result = AtlasImportResult()
    result.increment_metrics_counter("entity:t:created")

    assert (request.option("startPosition"), request.option("updateTypeDefinition")) == ("2", "true")
    assert request.option("startGuid") is None
    assert not request.is_replication_option_set()
    assert AtlasImportRequest.model_validate({"options": {"replicatedFrom": "x"}}).is_replication_option_set()
    assert result.metrics == {"entity:t:created": 1}


@pytest.mark.covers(
    "aurelius_atlas_model.impexp.skip_update_replication_attr",
    "aurelius_atlas_model.impexp.replicated",
    rules=["REP-03", "REP-04"],
)
def test__the_replication_options_are_read_as_atlas_reads_them() -> None:
    """``skipUpdateReplicationAttr`` as a boolean or text; a replication option's text, empty when absent."""
    assert skip_update_replication_attr({"skipUpdateReplicationAttr": True})
    assert skip_update_replication_attr({"skipUpdateReplicationAttr": "True"})
    assert not skip_update_replication_attr({"skipUpdateReplicationAttr": "yes"})
    assert not skip_update_replication_attr({"skipUpdateReplicationAttr": 1})
    assert not skip_update_replication_attr({})
    assert replicated({"replicatedTo": "dc$cl2"}, "replicatedTo") == "dc$cl2"
    assert replicated({"replicatedTo": True}, "replicatedTo") == "true"
    assert replicated({}, "replicatedFrom") == ""


@pytest.mark.covers("aurelius_atlas_model.impexp.AtlasServer.set_additional_info_repl", rules=["REP-01", "REP-04"])
def test__a_server_keeps_each_replicated_entity_time_in_its_details() -> None:
    """``REPL_DETAILS`` is a JSON map of GUID to time; a time of 0 takes the GUID out; other info is kept."""
    server = AtlasServer.model_validate({"name": "cl2", "fullName": "dc$cl2", "additionalInfo": {"k": "v"}})

    server.set_additional_info_repl("g1", 10)
    server.set_additional_info_repl("g2", 20)
    server.set_additional_info_repl("g1", 0)

    assert server.additional_info == {"k": "v", "REPL_DETAILS": '{"g2":20}'}
    assert server.to_json() == {
        "guid": "-1",
        "name": "cl2",
        "fullName": "dc$cl2",
        "additionalInfo": {"k": "v", "REPL_DETAILS": '{"g2":20}'},
    }
    entry = ExportImportAuditEntry.model_validate(
        {"userName": "u", "operation": "EXPORT", "startTime": 1, "endTime": 2}
    )
    assert entry.to_json() == {"guid": "-1", "userName": "u", "operation": "EXPORT", "startTime": 1, "endTime": 2}

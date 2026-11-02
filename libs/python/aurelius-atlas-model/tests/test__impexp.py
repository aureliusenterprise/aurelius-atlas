"""The export request's options and the result's counters (EXP-02, EXP-06).

Read from ``AtlasExportRequest`` (``getFetchTypeOptionValue``, ``getSkipLineageOptionValue``,
``getMatchTypeOptionValue``, ``getChangeTokenFromOptions``, ``getOmitZipResponseForEmptyExport``) and
``AtlasExportResult#incrementMeticsCounter`` of Apache Atlas 2.4.0.
"""

import pytest
from aurelius_atlas_model.impexp import AtlasExportRequest, AtlasExportResult

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

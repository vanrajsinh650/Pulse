from datetime import datetime, timezone
from pulse.contracts.models import (
    IncidentReport,
    InvariantResult,
    InvariantType,
    InvestigationResult,
    PropertyRecord,
    RequestTrace,
    RunTrace,
)


def test_property_record_creation():
    record = PropertyRecord(
        property_entity_id="nextimmo:12345",
        source="nextimmo",
        source_listing_id=12345,  # test coercion
        source_url="https://nextimmo.lu/listing/12345",
        deal_type="sale",
        property_type="apartment",
        price=550000.0,
        currency="EUR",
        area=85.0,
        rooms=2,
        location="Luxembourg-City",
    )
    assert record.source_listing_id == "12345"
    assert record.price == 550000.0
    assert record.currency == "EUR"
    assert record.observed_at is not None


def test_run_trace_properties():
    req1 = RequestTrace(
        page=1,
        url="https://nextimmo.lu/search/page/1",
        status_code=200,
        response_size=1024,
    )
    rec1 = PropertyRecord(
        property_entity_id="p1",
        source="nextimmo",
        source_listing_id="101",
        source_url="https://nextimmo.lu/101",
    )
    rec2 = PropertyRecord(
        property_entity_id="p2",
        source="nextimmo",
        source_listing_id="102",
        source_url="https://nextimmo.lu/102",
    )
    trace = RunTrace(
        run_id="run-001",
        source="nextimmo",
        requested_limit=20,
        requests=[req1],
        records=[rec1, rec2],
    )
    assert trace.total_records == 2
    assert trace.total_requests == 1
    assert trace.unique_record_ids == ["101", "102"]


def test_investigation_result_validation():
    res = InvestigationResult(
        failure_type="pagination_stalled",
        summary="Page 2 repeated page 1 records",
        evidence=["page_1_ids == page_2_ids"],
        likely_cause="State did not increment",
        confidence=0.95,
        recommended_action="Advance page index",
        suggested_regression_test="test_pagination_must_progress",
    )
    assert res.confidence == 0.95
    assert res.failure_type == "pagination_stalled"

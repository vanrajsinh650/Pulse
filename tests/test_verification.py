import json
from pulse.contracts.models import InvariantType, PropertyRecord, RequestTrace, RunTrace
from pulse.verification.engine import VerificationEngine


def make_record(rec_id: str, price: float = 400000.0) -> PropertyRecord:
    return PropertyRecord(
        property_entity_id=f"nextimmo:{rec_id}",
        source="nextimmo",
        source_listing_id=rec_id,
        source_url=f"https://nextimmo.lu/listing/{rec_id}",
        deal_type="sale",
        property_type="apartment",
        price=price,
        currency="EUR",
        area=75.0,
        rooms=2,
        location="Luxembourg",
    )


def test_verification_healthy_run():
    req1 = RequestTrace(page=1, url="https://nextimmo.lu/search/page/1", status_code=200)
    req2 = RequestTrace(page=2, url="https://nextimmo.lu/search/page/2", status_code=200)
    recs = [make_record(str(i)) for i in range(1, 21)]

    trace = RunTrace(
        run_id="run-healthy",
        source="nextimmo",
        requested_limit=20,
        requests=[req1, req2],
        records=recs,
    )

    engine = VerificationEngine()
    report = engine.verify(trace)

    assert report.status == "PASSED"
    assert len(report.failed_invariants) == 0


def test_verification_limit_overrun():
    req = RequestTrace(page=1, url="https://nextimmo.lu/search/page/1", status_code=200)
    recs = [make_record(str(i)) for i in range(1, 25)]

    trace = RunTrace(
        run_id="run-overrun",
        source="nextimmo",
        requested_limit=20,  # 24 records collected for limit 20
        requests=[req],
        records=recs,
    )

    engine = VerificationEngine()
    report = engine.verify(trace)

    assert report.status == "FAILED"
    assert InvariantType.LIMIT_BOUND in report.failed_invariants


def test_verification_duplicate_pagination():
    req1 = RequestTrace(page=1, url="https://nextimmo.lu/search/page/1", raw_payload="p1")
    req2 = RequestTrace(page=2, url="https://nextimmo.lu/search/page/2", raw_payload="p1")
    recs = [make_record("101"), make_record("102"), make_record("101")]

    trace = RunTrace(
        run_id="run-dupe",
        source="nextimmo",
        requested_limit=10,
        requests=[req1, req2],
        records=recs,
    )

    engine = VerificationEngine()
    report = engine.verify(trace)

    assert report.status == "FAILED"
    assert InvariantType.PAGINATION_CONTINUITY in report.failed_invariants


def test_verification_silent_zero_yield():
    substantial_html = "<html><body>" + "listing property detail " * 50 + "</body></html>"
    req = RequestTrace(
        page=1,
        url="https://nextimmo.lu/search/page/1",
        status_code=200,
        raw_payload=substantial_html,
    )
    trace = RunTrace(
        run_id="run-zero",
        source="nextimmo",
        requested_limit=10,
        requests=[req],
        records=[],
    )

    engine = VerificationEngine()
    report = engine.verify(trace)

    assert report.status == "FAILED"
    assert InvariantType.ZERO_YIELD in report.failed_invariants


def test_verification_legitimate_empty_source():
    empty_payload = json.dumps({"totalItems": 0, "data": []})
    req = RequestTrace(
        page=1,
        url="https://nextimmo.lu/search/page/1",
        status_code=200,
        raw_payload=empty_payload,
    )
    trace = RunTrace(
        run_id="run-legit-empty",
        source="nextimmo",
        requested_limit=10,
        requests=[req],
        records=[],
    )

    engine = VerificationEngine()
    report = engine.verify(trace)

    assert InvariantType.ZERO_YIELD not in report.failed_invariants


def test_verification_provenance_failure():
    bad_rec = PropertyRecord(
        property_entity_id="1",
        source="nextimmo",
        source_listing_id="1",
        source_url="not-a-valid-url",
    )
    req = RequestTrace(page=1, url="https://nextimmo.lu/search/page/1", status_code=200)
    trace = RunTrace(
        run_id="run-provenance",
        source="nextimmo",
        requests=[req],
        records=[bad_rec],
    )

    engine = VerificationEngine()
    report = engine.verify(trace)

    assert report.status == "FAILED"
    assert InvariantType.PROVENANCE in report.failed_invariants


def test_verification_request_consistency_failure():
    req1 = RequestTrace(
        page=1,
        url="https://nextimmo.lu/search/page/1",
        params={"category": "residential", "country": "LU"},
    )
    req2 = RequestTrace(
        page=2,
        url="https://nextimmo.lu/search/page/2",
        params={"category": "commercial", "country": "LU"},  # diverged!
    )
    recs = [make_record("1"), make_record("2")]
    trace = RunTrace(
        run_id="run-inconsistent",
        source="nextimmo",
        requests=[req1, req2],
        records=recs,
    )

    engine = VerificationEngine()
    report = engine.verify(trace)

    assert report.status == "FAILED"
    assert InvariantType.REQUEST_CONSISTENCY in report.failed_invariants


def test_verification_schema_integrity_failure():
    rec = make_record("1", price=-50.0)
    req = RequestTrace(page=1, url="https://nextimmo.lu/search/page/1")
    trace = RunTrace(
        run_id="run-schema",
        source="nextimmo",
        requests=[req],
        records=[rec],
    )

    engine = VerificationEngine()
    report = engine.verify(trace)

    assert report.status == "FAILED"
    assert InvariantType.SCHEMA_INTEGRITY in report.failed_invariants

from pulse.contracts.models import IncidentReport, InvariantResult, InvariantType
from pulse.investigator.agent import AIInvestigator


def test_ai_investigator_diagnoses_pagination_stall():
    inv_res = InvariantResult(
        invariant=InvariantType.PAGINATION_CONTINUITY,
        passed=False,
        expected="unique records progressing across pages",
        observed="20 duplicated records detected on page(s) [2]",
        affected_pages=[2],
        details={"duplicate_count": 20},
        evidence=["pagination repeated previous page", "affected page: [2]"],
    )
    report = IncidentReport(
        incident_id="INC-002",
        source="nextimmo",
        status="FAILED",
        results=[inv_res],
        summary="Pagination stalled on page 2",
        recommended_next_step="inspect pagination state advancement",
        total_records=40,
        total_requests=2,
        failed_invariants=[InvariantType.PAGINATION_CONTINUITY],
    )

    investigator = AIInvestigator()
    diagnosis = investigator.investigate(report)

    assert diagnosis.failure_type == "pagination_stalled"
    assert diagnosis.confidence >= 0.90
    assert "page" in diagnosis.likely_cause.lower()
    assert len(diagnosis.evidence) > 0
    assert "pagination" in diagnosis.suggested_regression_test


def test_ai_investigator_diagnoses_limit_overrun():
    inv_res = InvariantResult(
        invariant=InvariantType.LIMIT_BOUND,
        passed=False,
        expected="<= 20 records",
        observed="40 records",
        details={"overrun": 20, "requested_limit": 20},
        evidence=["requested limit = 20", "collected records = 40"],
    )
    report = IncidentReport(
        incident_id="INC-001",
        source="nextimmo",
        status="FAILED",
        results=[inv_res],
        summary="Limit bound violated",
        recommended_next_step="slice accumulated records",
        total_records=40,
        total_requests=2,
        failed_invariants=[InvariantType.LIMIT_BOUND],
    )

    investigator = AIInvestigator()
    diagnosis = investigator.investigate(report)

    assert diagnosis.failure_type == "limit_overrun"
    assert diagnosis.confidence >= 0.90
    assert "limit" in diagnosis.recommended_action.lower()


def test_ai_investigator_diagnoses_silent_zero_yield():
    inv_res = InvariantResult(
        invariant=InvariantType.ZERO_YIELD,
        passed=False,
        expected="records extracted from substantial response",
        observed="0 records extracted from HTTP 200 payload",
        details={"payload_length": 5000},
        evidence=["HTTP 200 received with 5000 bytes payload"],
    )
    report = IncidentReport(
        incident_id="INC-003",
        source="nextimmo",
        status="FAILED",
        results=[inv_res],
        summary="Silent zero yield",
        recommended_next_step="inspect HTML parser selectors",
        total_records=0,
        total_requests=1,
        failed_invariants=[InvariantType.ZERO_YIELD],
    )

    investigator = AIInvestigator()
    diagnosis = investigator.investigate(report)

    assert diagnosis.failure_type == "silent_zero_yield"
    assert "markup" in diagnosis.likely_cause.lower() or "structure" in diagnosis.likely_cause.lower()

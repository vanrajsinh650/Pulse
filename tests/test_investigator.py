from pulse.contracts.models import (
    IncidentReport,
    InvariantResult,
    InvariantType,
    InvestigationResult,
)
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
    assert diagnosis.source == "deterministic fallback"


class FakeModelService:
    def __init__(self, response_or_exc: object) -> None:
        self.response_or_exc = response_or_exc
        self.last_call: dict[str, object] = {}

    def generate_content(self, model: str, contents: str, config: object) -> object:
        self.last_call = {"model": model, "contents": contents, "config": config}
        if isinstance(self.response_or_exc, Exception):
            raise self.response_or_exc
        return self.response_or_exc


class FakeGeminiClient:
    def __init__(self, response_or_exc: object) -> None:
        self.models = FakeModelService(response_or_exc)


class FakeResponse:
    def __init__(self, text: str | None = None, parsed: object = None) -> None:
        self.text = text
        self.parsed = parsed


def _sample_failed_report() -> IncidentReport:
    inv_res = InvariantResult(
        invariant=InvariantType.PAGINATION_CONTINUITY,
        passed=False,
        expected="unique records per page",
        observed="20 duplicated records detected on page(s) [2]",
        affected_pages=[2],
        details={"duplicate_count": 20},
        evidence=["pagination repeated previous page", "affected page: [2]"],
    )
    return IncidentReport(
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


def test_gemini_investigator_valid_response():
    fake_parsed = InvestigationResult(
        failure_type="pagination_stalled",
        summary="Page 2 repeated page 1 records due to cursor stall.",
        evidence=["Page 1 and Page 2 contain duplicate listing IDs."],
        likely_cause="The adapter pagination state did not advance in request loop.",
        confidence=0.94,
        recommended_action="Inspect pagination query parameters.",
        suggested_regression_test="test_pagination_must_progress",
    )
    fake_client = FakeGeminiClient(FakeResponse(parsed=fake_parsed))

    investigator = AIInvestigator(client=fake_client)
    report = _sample_failed_report()
    diagnosis = investigator.investigate(report)

    assert diagnosis.source == "Gemini 3.1 Flash-Lite"
    assert diagnosis.failure_type == "pagination_stalled"
    assert diagnosis.confidence == 0.94
    # Ensure verified invariant evidence is preserved
    assert any("pagination repeated previous page" in ev for ev in diagnosis.evidence)


def test_gemini_investigator_invalid_json_fallback():
    # Model returns non-JSON or malformed string
    fake_client = FakeGeminiClient(FakeResponse(text="NOT_VALID_JSON"))

    investigator = AIInvestigator(client=fake_client)
    report = _sample_failed_report()
    diagnosis = investigator.investigate(report)

    # Must fall back gracefully to deterministic diagnosis
    assert diagnosis.source == "deterministic fallback"
    assert diagnosis.failure_type == "pagination_stalled"


def test_gemini_investigator_api_exception_fallback():
    # API raises network error or rate-limit error
    fake_client = FakeGeminiClient(RuntimeError("API quota exceeded or network disconnect"))

    investigator = AIInvestigator(client=fake_client)
    report = _sample_failed_report()
    diagnosis = investigator.investigate(report)

    # Must fall back gracefully
    assert diagnosis.source == "deterministic fallback"
    assert diagnosis.failure_type == "pagination_stalled"


def test_gemini_investigator_insufficient_evidence_allowed():
    fake_parsed = InvestigationResult(
        failure_type="insufficient_evidence",
        summary="Supplied evidence is insufficient to identify the exact parser change.",
        evidence=["Single HTTP 200 with 0 records"],
        likely_cause="Indeterminate source drift without full markup inspection.",
        confidence=0.45,
        recommended_action="Inspect full raw payload manually.",
        suggested_regression_test="test_record_extraction_with_raw_fixture",
    )
    fake_client = FakeGeminiClient(FakeResponse(parsed=fake_parsed))

    investigator = AIInvestigator(client=fake_client)
    report = _sample_failed_report()
    diagnosis = investigator.investigate(report)

    assert diagnosis.source == "Gemini 3.1 Flash-Lite"
    assert diagnosis.failure_type == "insufficient_evidence"
    assert diagnosis.confidence == 0.45


def test_gemini_investigator_confidence_clamping():
    # When output confidence is out of bounds, it is safely clamped to [0.0, 1.0]
    fake_parsed = InvestigationResult(
        failure_type="limit_overrun",
        summary="Overrun occurred.",
        evidence=["collected 40 > 20"],
        likely_cause="Loop failed to exit.",
        confidence=1.0,
        recommended_action="Slice records.",
        suggested_regression_test="test_limit",
    )
    # Force out of bounds for testing clamping
    fake_parsed.__dict__["confidence"] = 1.8
    fake_client = FakeGeminiClient(FakeResponse(parsed=fake_parsed))

    investigator = AIInvestigator(client=fake_client)
    report = _sample_failed_report()
    diagnosis = investigator.investigate(report)

    assert diagnosis.confidence == 1.0


def test_gemini_investigator_healthy_run_never_calls_ai():
    fake_client = FakeGeminiClient(RuntimeError("Should not be called!"))
    investigator = AIInvestigator(client=fake_client)

    healthy_report = IncidentReport(
        incident_id="INC-HEALTHY",
        source="nextimmo",
        status="PASSED",
        results=[],
        summary="All invariants passed",
        recommended_next_step="promote",
        total_records=20,
        total_requests=1,
        failed_invariants=[],
    )

    diagnosis = investigator.investigate(healthy_report)
    assert diagnosis.failure_type == "no_failure"
    assert diagnosis.source == "deterministic fallback"

from pathlib import Path

from pulse.contracts.models import InvariantType
from pulse.diff.comparator import StructuralComparator
from pulse.replay.recorder import load_run_trace
from pulse.verification.engine import VerificationEngine

INCIDENTS_DIR = Path(__file__).parent.parent / "incidents"


def test_incident_001_limit_overrun():
    trace_path = INCIDENTS_DIR / "INC-001" / "trace.json"
    baseline_path = INCIDENTS_DIR / "INC-001" / "baseline_trace.json"

    trace = load_run_trace(trace_path)
    baseline = load_run_trace(baseline_path)

    verifier = VerificationEngine()
    b_report = verifier.verify(baseline)
    i_report = verifier.verify(trace, incident_id="INC-001")

    assert b_report.status == "PASSED"
    assert i_report.status == "FAILED"
    assert InvariantType.LIMIT_BOUND in i_report.failed_invariants

    comparator = StructuralComparator()
    diff = comparator.compare(baseline, trace)
    assert diff.records_baseline == 20
    assert diff.records_incident == 40
    assert diff.records_delta == 20
    assert "LIMIT_BOUND" in diff.failed_invariants_incident


def test_incident_002_duplicate_pagination():
    trace_path = INCIDENTS_DIR / "INC-002" / "trace.json"
    baseline_path = INCIDENTS_DIR / "INC-002" / "baseline_trace.json"

    trace = load_run_trace(trace_path)
    baseline = load_run_trace(baseline_path)

    verifier = VerificationEngine()
    b_report = verifier.verify(baseline)
    i_report = verifier.verify(trace, incident_id="INC-002")

    assert b_report.status == "PASSED"
    assert i_report.status == "FAILED"
    assert InvariantType.PAGINATION_CONTINUITY in i_report.failed_invariants

    comparator = StructuralComparator()
    diff = comparator.compare(baseline, trace)
    assert len(diff.duplicate_ids_in_incident) == 20
    assert "PAGINATION_CONTINUITY" in diff.failed_invariants_incident


def test_incident_003_silent_zero_yield():
    trace_path = INCIDENTS_DIR / "INC-003" / "trace.json"
    baseline_path = INCIDENTS_DIR / "INC-003" / "baseline_trace.json"

    trace = load_run_trace(trace_path)
    baseline = load_run_trace(baseline_path)

    verifier = VerificationEngine()
    b_report = verifier.verify(baseline)
    i_report = verifier.verify(trace, incident_id="INC-003")

    assert b_report.status == "PASSED"
    assert i_report.status == "FAILED"
    assert InvariantType.ZERO_YIELD in i_report.failed_invariants

    comparator = StructuralComparator()
    diff = comparator.compare(baseline, trace)
    assert diff.records_baseline == 20
    assert diff.records_incident == 0
    assert "ZERO_YIELD" in diff.failed_invariants_incident

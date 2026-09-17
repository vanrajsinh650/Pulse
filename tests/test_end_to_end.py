import subprocess
import sys
from pathlib import Path

from pulse.diff.comparator import StructuralComparator
from pulse.generator.test_generator import generate_regression_test
from pulse.investigator.agent import AIInvestigator
from pulse.replay.recorder import load_run_trace
from pulse.verification.engine import VerificationEngine


def test_complete_incident_resolution_loop(tmp_path):
    """End-to-end test of the entire developer workflow:

    1. Load incident trace
    2. Detect failed invariants deterministically
    3. Run structural diff against baseline
    4. Run evidence-based AI investigator
    5. Generate executable regression test
    6. Execute regression test and verify both before-repair failure and after-repair success.
    """
    repo_root = Path(__file__).parent.parent
    inc_dir = repo_root / "incidents" / "INC-002"

    trace = load_run_trace(inc_dir / "trace.json")
    baseline = load_run_trace(inc_dir / "baseline_trace.json")

    # Step 1: Detect failure deterministically
    engine = VerificationEngine()
    report = engine.verify(trace, incident_id="INC-002")
    assert report.status == "FAILED"
    assert len(report.failed_invariants) == 1

    # Step 2: Structural diff
    comparator = StructuralComparator()
    diff = comparator.compare(baseline, trace)
    assert len(diff.duplicate_ids_in_incident) > 0

    # Step 3: AI investigation
    investigator = AIInvestigator()
    diagnosis = investigator.investigate(report, diff=diff)
    assert diagnosis.failure_type == "pagination_stalled"
    assert diagnosis.confidence >= 0.90

    # Step 4: Generate regression test
    test_file = generate_regression_test("INC-002", report, diagnosis, output_dir=tmp_path)
    assert test_file.exists()

    # Step 5: Execute generated test via pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "2 passed" in result.stdout

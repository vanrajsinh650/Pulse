import subprocess
import sys
from pathlib import Path
from pulse.generator.test_generator import generate_regression_test
from pulse.investigator.agent import AIInvestigator
from pulse.replay.recorder import load_run_trace
from pulse.verification.engine import VerificationEngine


INCIDENTS_DIR = Path(__file__).parent.parent / "incidents"


def test_generate_and_run_regression_test_for_inc001(tmp_path):
    trace = load_run_trace(INCIDENTS_DIR / "INC-001" / "trace.json")
    engine = VerificationEngine()
    report = engine.verify(trace, incident_id="INC-001")

    investigator = AIInvestigator()
    diagnosis = investigator.investigate(report)

    # Generate the test in tests/regression
    test_file = generate_regression_test("INC-001", report, diagnosis, output_dir=tmp_path)
    assert test_file.exists()

    # Run pytest directly on the generated file to verify both failure before repair and success after repair pass!
    res = subprocess.run([sys.executable, "-m", "pytest", str(test_file)], capture_output=True, text=True)
    assert res.returncode == 0, f"Generated test failed: {res.stdout}\n{res.stderr}"
    assert "2 passed" in res.stdout


def test_generate_and_run_regression_test_for_inc002(tmp_path):
    trace = load_run_trace(INCIDENTS_DIR / "INC-002" / "trace.json")
    engine = VerificationEngine()
    report = engine.verify(trace, incident_id="INC-002")

    investigator = AIInvestigator()
    diagnosis = investigator.investigate(report)

    test_file = generate_regression_test("INC-002", report, diagnosis, output_dir=tmp_path)
    assert test_file.exists()

    res = subprocess.run([sys.executable, "-m", "pytest", str(test_file)], capture_output=True, text=True)
    assert res.returncode == 0, f"Generated test failed: {res.stdout}\n{res.stderr}"
    assert "2 passed" in res.stdout


def test_generate_and_run_regression_test_for_inc003(tmp_path):
    trace = load_run_trace(INCIDENTS_DIR / "INC-003" / "trace.json")
    engine = VerificationEngine()
    report = engine.verify(trace, incident_id="INC-003")

    investigator = AIInvestigator()
    diagnosis = investigator.investigate(report)

    test_file = generate_regression_test("INC-003", report, diagnosis, output_dir=tmp_path)
    assert test_file.exists()

    res = subprocess.run([sys.executable, "-m", "pytest", str(test_file)], capture_output=True, text=True)
    assert res.returncode == 0, f"Generated test failed: {res.stdout}\n{res.stderr}"
    assert "2 passed" in res.stdout

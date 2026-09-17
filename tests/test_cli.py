from click.testing import CliRunner

from pulse.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Pulse" in result.output
    assert "replay" in result.output


def test_cli_replay_inc001():
    runner = CliRunner()
    result = runner.invoke(main, ["replay", "incidents/INC-001"])
    assert result.exit_code == 1  # Replay of failed incident exits with code 1
    assert "Incident: INC-001" in result.output
    assert "Status: FAILED" in result.output
    assert "LIMIT_BOUND" in result.output or "requested limit exceeded" in result.output


def test_cli_replay_inc002():
    runner = CliRunner()
    result = runner.invoke(main, ["replay", "incidents/INC-002"])
    assert result.exit_code == 1
    assert "Incident: INC-002" in result.output
    assert "Status: FAILED" in result.output
    assert "pagination repeated previous page" in result.output


def test_cli_investigate():
    runner = CliRunner()
    result = runner.invoke(main, ["investigate", "INC-001"])
    assert result.exit_code == 0
    assert "limit_overrun" in result.output
    assert "confidence" in result.output


def test_cli_generate_test(tmp_path):
    runner = CliRunner()
    result = runner.invoke(main, ["generate-test", "INC-001", "--output-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Generated regression test:" in result.output


def test_cli_diff():
    runner = CliRunner()
    result = runner.invoke(main, ["diff", "incidents/INC-001/baseline_trace.json", "incidents/INC-001/trace.json"])
    assert result.exit_code == 0
    assert "Structural Diff" in result.output
    assert "LIMIT_BOUND" in result.output


def test_cli_benchmark():
    runner = CliRunner()
    result = runner.invoke(main, ["benchmark"])
    assert result.exit_code == 0
    assert "Benchmark Results" in result.output
    assert "100%" in result.output

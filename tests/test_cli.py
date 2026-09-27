import json
import subprocess
import sys


def test_version():
    result = subprocess.run(
        [sys.executable, "-m", "nadi9.cli", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "0.1.0"


def test_cli_run_and_correction(tmp_path):
    initial = tmp_path / "initial"
    corrected = tmp_path / "corrected"
    run = subprocess.run(
        [sys.executable, "-m", "nadi9.cli", "run", "fixtures/demo.json", "--out", str(initial)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(run.stdout)["decisions"]["APPROVED"] == 3
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "nadi9.cli",
            "correct",
            str(initial / "state.json"),
            "fixtures/correction.json",
            "--out",
            str(corrected),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout)["reprocessed"] == ["S002"]
    assert json.loads(result.stdout)["decisions"]["APPROVED"] == 4


def test_cli_rejects_invalid_input_without_traceback(tmp_path):
    pack = tmp_path / "invalid.json"
    pack.write_text("{}")
    result = subprocess.run(
        [sys.executable, "-m", "nadi9.cli", "validate", str(pack)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr

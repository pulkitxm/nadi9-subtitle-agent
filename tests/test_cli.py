import subprocess
import sys


def test_version():
    result = subprocess.run(
        [sys.executable, "-m", "nadi9.cli", "--version"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "0.1.0"

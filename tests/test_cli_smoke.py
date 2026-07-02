import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_prepare_ir_cli_runs_on_fixture():
    # Use the fixtures copy — immune to TC/ filename-convention changes.
    tc = REPO / "tests" / "fixtures" / "pf002-0098-normalized-test-flow.md"
    r = subprocess.run([sys.executable, "generate_pattern.py", "prepare-ir", str(tc)],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "Run dir:" in r.stdout

import json
import subprocess
from pathlib import Path
from shutil import which

import pytest

ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / "tests" / "js"


@pytest.fixture(scope="session")
def node():
    executable = which("node")

    if executable is None:
        pytest.skip("node is not installed")

    def run(script: str, *arguments: str):
        result = subprocess.run(
            [executable, str(JS / script), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
        )

        if result.returncode != 0:
            raise AssertionError(
                f"node {script} failed with {result.returncode}:\n"
                f"{result.stderr}")

        return json.loads(result.stdout)

    return run

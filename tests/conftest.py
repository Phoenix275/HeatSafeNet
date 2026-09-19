import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "model"))

COVERAGE_FILES = sorted((ROOT / "data" / "int").glob("coverage_*.json"))


@pytest.fixture(params=COVERAGE_FILES, ids=lambda p: p.stem)
def coverage(request):
    with open(request.param) as f:
        return json.load(f)

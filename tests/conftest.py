import sys
from pathlib import Path

import pytest

# make project imports (app, scripts) work when pytest runs from the root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)
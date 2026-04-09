"""Top-level conftest — only fixtures shared by ALL test layers."""
from __future__ import annotations

import sys
import os

# Make `app` importable from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


import pytest


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer dev-key-for-testing"}

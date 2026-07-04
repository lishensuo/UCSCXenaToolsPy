"""Shared fixtures for API tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ucscxenatoolspy.api_service.main import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient — runs in-process, no server needed."""
    return TestClient(app)

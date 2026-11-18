"""The SPA shell must not be cached, and file paths must stay inside the build folder."""
import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app, frontend_dist

pytestmark = pytest.mark.skipif(not frontend_dist, reason="frontend not built")
client = TestClient(app)


def test_page_shell_is_not_cached():
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-cache"


def test_path_traversal_returns_shell_not_file():
    r = client.get("/..%2F..%2Fbackend%2Fconfig.py")
    assert "SECRET" not in r.text and "BaseSettings" not in r.text

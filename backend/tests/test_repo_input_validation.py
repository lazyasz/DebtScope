"""Scans must reject non-GitHub input and never invent files for a repo that can't be read."""
from unittest.mock import patch, MagicMock
import pytest
from backend.services.repo_scanner_service import RepoScannerService as R


@pytest.mark.parametrize("ok", ["psf/requests", "https://github.com/pallets/flask.git", "github.com/a-b/c.d", "zookeeper"])
def test_valid_inputs(ok):
    owner, repo, url = R.parse_repository_target(ok)
    assert url == f"https://github.com/{owner}/{repo}"


@pytest.mark.parametrize("bad", ["", "not a repo", "http://169.254.169.254/latest", "gitlab.com/owner/repo", "a/b c"])
def test_invalid_inputs(bad):
    with pytest.raises(ValueError):
        R.parse_repository_target(bad)


def test_missing_repo_is_an_error_not_fake_files():
    with patch("backend.services.repo_scanner_service.requests.get", return_value=MagicMock(status_code=404)):
        with pytest.raises(ValueError):
            R._scan_live_github_api(MagicMock(), "someone", "nope", "https://github.com/someone/nope", "ws_x", None)


def test_unreadable_tree_is_an_error_not_fake_files():
    meta = MagicMock(status_code=200); meta.json.return_value = {"private": False, "default_branch": "main"}
    tree = MagicMock(status_code=403); tree.json.return_value = {}
    db = MagicMock(); db.query.return_value.filter.return_value.first.return_value = MagicMock(id=1)
    with patch("backend.services.repo_scanner_service.requests.get", side_effect=[meta, tree]):
        with pytest.raises(ValueError):
            R._scan_live_github_api(db, "someone", "empty", "https://github.com/someone/empty", "ws_x", None)


def test_delete_repository_only_in_own_workspace():
    from fastapi.testclient import TestClient
    from backend.main import app
    c = TestClient(app)
    r = c.delete("/api/repositories/987654")
    assert r.status_code == 404

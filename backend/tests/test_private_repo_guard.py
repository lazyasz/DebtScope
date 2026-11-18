"""A private repo must not be scanned with the server's token (it would expose it to every user)."""
from unittest.mock import patch, MagicMock
import pytest
from backend.services.repo_scanner_service import RepoScannerService


def _meta(private):
    r = MagicMock(status_code=200)
    r.json.return_value = {"private": private, "default_branch": "main"}
    return r


def test_private_repo_refused_without_user_token():
    with patch("backend.services.repo_scanner_service.requests.get", return_value=_meta(True)):
        with pytest.raises(PermissionError):
            RepoScannerService._scan_live_github_api(MagicMock(), "someone", "secret-repo", "https://github.com/someone/secret-repo", "ws_x", None)

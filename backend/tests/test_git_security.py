"""
Tests for Sandboxed Git Cloner and SSRF Security Protection.
"""

import os
import pytest
from backend.services.git_cloner import (
    validate_repo_url,
    SSRFValidationError,
    SandboxedGitCloner,
)


class TestSSRFProtection:
    @pytest.mark.parametrize("invalid_url", [
        "http://localhost",
        "http://localhost:8000/api",
        "http://127.0.0.1:8080",
        "http://127.0.0.1",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/internal/repo",
        "http://192.168.1.50/repo.git",
        "http://172.16.0.5/repo.git",
        "file:///etc/passwd",
        "ftp://ftp.example.com/repo.git",
        "gopher://example.com",
        "",
        "   ",
    ])
    def test_ssrf_rejects_internal_and_prohibited_targets(self, invalid_url):
        with pytest.raises(SSRFValidationError):
            validate_repo_url(invalid_url)

    @pytest.mark.parametrize("valid_input,expected_output", [
        ("https://github.com/pallets/flask", "https://github.com/pallets/flask"),
        ("https://github.com/pallets/flask.git", "https://github.com/pallets/flask.git"),
        ("https://gitlab.com/gitlab-org/gitlab", "https://gitlab.com/gitlab-org/gitlab"),
        ("pallets/flask", "https://github.com/pallets/flask"),
        ("tiangolo/fastapi", "https://github.com/tiangolo/fastapi"),
    ])
    def test_ssrf_accepts_valid_public_repositories(self, valid_input, expected_output):
        result = validate_repo_url(valid_input)
        assert result == expected_output


class TestSandboxedClonerCleanup:
    def test_cleanup_removes_temp_directory(self):
        """Verify that temporary clone directories are 100% removed after context exit."""
        cloner = SandboxedGitCloner("https://github.com/pallets/flask")
        # Artificially set a temporary directory to test cleanup without network clone
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix="test_cleanup_")
        cloner.temp_dir = temp_dir
        
        # Verify it exists
        assert os.path.exists(temp_dir)
        
        # Trigger cleanup
        cloner.cleanup()
        
        # Verify it has been purged from disk
        assert not os.path.exists(temp_dir)
        assert cloner.temp_dir is None

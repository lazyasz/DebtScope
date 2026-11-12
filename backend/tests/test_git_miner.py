"""
Tests for Git History & Churn Mining.
Creates an ephemeral git repository and verifies churn, author entropy, and bug detection.
"""

import os
import tempfile
import subprocess
import pytest
from backend.services.git_miner import GitMiner


@pytest.fixture
def mock_git_repo():
    """Initializes a local git repository with multiple commits and authors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        def git(*args):
            subprocess.run(["git"] + list(args), cwd=tmpdir, check=True, capture_output=True)

        git("init")
        git("config", "user.email", "alice@example.com")
        git("config", "user.name", "Alice Engineer")

        # Commit 1 by Alice
        file1 = os.path.join(tmpdir, "calculator.py")
        with open(file1, "w") as f:
            f.write("def add(a, b):\n    return a + b\n")
        git("add", "calculator.py")
        git("commit", "-m", "feat: initial calculator implementation")

        # Commit 2 by Bob (bug fix)
        git("config", "user.email", "bob@example.com")
        git("config", "user.name", "Bob Reviewer")
        with open(file1, "a") as f:
            f.write("\ndef subtract(a, b):\n    return a - b\n")
        git("add", "calculator.py")
        git("commit", "-m", "fix: resolve subtraction defect in calculator")

        yield tmpdir


class TestGitMiner:
    def test_mine_file_history_extracts_churn_and_authors(self, mock_git_repo):
        miner = GitMiner(mock_git_repo)
        history = miner.mine_file_history()

        assert "calculator.py" in history
        stats = history["calculator.py"]
        
        # Verify measured churn
        assert stats["lines_added"] >= 4
        assert stats["churn_lines"] >= 4
        assert stats["commit_count"] == 2
        assert stats["churn_provenance"] == "MEASURED"
        
        # Verify author distribution
        assert stats["authors_count"] == 2
        assert stats["author_entropy"] > 0.0
        
        # Verify SZZ bug fix detection
        assert stats["bug_fixes_count"] == 1
        
        # Verify timestamps
        assert stats["first_commit_date"] is not None
        assert stats["last_commit_date"] is not None
        assert stats["age_days"] >= 0

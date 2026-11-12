"""
Git Repository History & Churn Mining Service.

Mines local cloned git repositories for:
1. Per-file commit churn, additions, deletions, and revisions.
2. Author commit entropy (developer concentration / Bus Factor).
3. File age and recency based on actual git commit timestamps.
4. Bug-fixing commit frequency derived from commit message patterns.
"""

import os
import math
import subprocess
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Patterns matching bug-fixing commits (SZZ heuristic foundation)
BUG_FIX_KEYWORDS = ("fix", "bug", "patch", "issue", "resolve", "defect", "error", "crash")


class GitMiner:
    """Extracts verifiable commit history metrics from a local git repository."""

    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir

    def _run_git(self, args: List[str], timeout: int = 60) -> str:
        """Executes a git command inside the target repo directory."""
        cmd = ["git"] + args
        try:
            res = subprocess.run(
                cmd,
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            if res.returncode != 0:
                logger.debug("Git command %s returned code %d: %s", args, res.returncode, res.stderr)
                return ""
            return res.stdout
        except Exception as e:
            logger.warning("Git execution failed for %s: %s", args, e)
            return ""

    def mine_file_history(self) -> Dict[str, Dict[str, Any]]:
        """
        Parses `git log --numstat` to compute per-file additions, deletions,
        commit frequencies, and unique author distributions.
        
        Returns a dictionary mapping relative file path -> telemetry dict:
        {
            "lines_added": int,
            "lines_removed": int,
            "churn_lines": int,
            "commit_count": int,
            "authors": Dict[str, int],
            "author_entropy": float,
            "bus_factor_risk": str, # LOW, MEDIUM, HIGH
            "bug_fixes_count": int,
            "first_commit_date": Optional[datetime],
            "last_commit_date": Optional[datetime],
            "age_days": int,
            "recency_days": int,
            "churn_provenance": "MEASURED"
        }
        """
        # Format: Hash | AuthorName | UnixTimestamp | Subject
        log_raw = self._run_git([
            "log",
            "--numstat",
            "--pretty=format:COMMIT_SEP|%H|%an|%at|%s",
        ])

        if not log_raw.strip():
            logger.info("No git history found or empty log output.")
            return {}

        file_stats: Dict[str, Dict[str, Any]] = {}
        now_ts = int(datetime.now(timezone.utc).timestamp())

        current_author = "Unknown"
        current_ts = now_ts
        current_is_fix = False

        for line in log_raw.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("COMMIT_SEP|"):
                parts = line.split("|")
                if len(parts) >= 5:
                    current_author = parts[2].strip() or "Unknown"
                    try:
                        current_ts = int(parts[3].strip())
                    except ValueError:
                        current_ts = now_ts
                    subject = parts[4].lower()
                    current_is_fix = any(k in subject for k in BUG_FIX_KEYWORDS)
                continue

            # Numstat line: <added> \t <removed> \t <filepath>
            tokens = line.split("\t")
            if len(tokens) == 3:
                added_str, removed_str, path = tokens
                # Skip binary file numstats (marked with -)
                added = int(added_str) if added_str.isdigit() else 0
                removed = int(removed_str) if removed_str.isdigit() else 0
                norm_path = path.replace("\\", "/").strip()

                if norm_path not in file_stats:
                    file_stats[norm_path] = {
                        "lines_added": 0,
                        "lines_removed": 0,
                        "commit_count": 0,
                        "authors": {},
                        "bug_fixes_count": 0,
                        "first_commit_ts": current_ts,
                        "last_commit_ts": current_ts,
                    }

                entry = file_stats[norm_path]
                entry["lines_added"] += added
                entry["lines_removed"] += removed
                entry["commit_count"] += 1
                entry["authors"][current_author] = entry["authors"].get(current_author, 0) + 1
                if current_is_fix:
                    entry["bug_fixes_count"] += 1

                # Track temporal boundaries
                if current_ts < entry["first_commit_ts"]:
                    entry["first_commit_ts"] = current_ts
                if current_ts > entry["last_commit_ts"]:
                    entry["last_commit_ts"] = current_ts

        # Post-process entropy, age, and risk metrics
        final_results = {}
        for path, data in file_stats.items():
            total_commits = max(1, data["commit_count"])
            churn = data["lines_added"] + data["lines_removed"]

            # Shannon entropy over author commit distribution
            # Higher entropy = widely distributed; Lower entropy = single contributor (bus factor risk)
            entropy = 0.0
            for author, count in data["authors"].items():
                p = count / total_commits
                if p > 0:
                    entropy -= p * math.log2(p)

            # Bus factor heuristic
            num_authors = len(data["authors"])
            if num_authors == 1 and total_commits >= 5:
                bus_factor_risk = "HIGH"
            elif num_authors <= 2:
                bus_factor_risk = "MEDIUM"
            else:
                bus_factor_risk = "LOW"

            age_days = max(1, int((now_ts - data["first_commit_ts"]) / 86400))
            recency_days = max(0, int((now_ts - data["last_commit_ts"]) / 86400))

            first_dt = datetime.fromtimestamp(data["first_commit_ts"], timezone.utc)
            last_dt = datetime.fromtimestamp(data["last_commit_ts"], timezone.utc)

            final_results[path] = {
                "lines_added": data["lines_added"],
                "lines_removed": data["lines_removed"],
                "churn_lines": churn,
                "commit_count": data["commit_count"],
                "authors_count": num_authors,
                "author_entropy": round(entropy, 2),
                "bus_factor_risk": bus_factor_risk,
                "bug_fixes_count": data["bug_fixes_count"],
                "first_commit_date": first_dt,
                "last_commit_date": last_dt,
                "age_days": age_days,
                "recency_days": recency_days,
                "churn_provenance": "MEASURED",
            }

        return final_results

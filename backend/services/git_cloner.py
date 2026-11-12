"""
Sandboxed Git Cloner & SSRF Protection Service.

Responsibilities:
1. Validates repository URLs against SSRF attacks (private IPs, loopback, metadata endpoints).
2. Clones repositories into isolated, temporary operating system directories with depth limits.
3. Enforces execution timeouts and repository disk size caps.
4. Strictly cleans up all temporary files on completion or error.
5. Guaranteed zero code execution on analyzed target repositories.
"""

import os
import re
import shutil
import socket
import tempfile
import subprocess
import ipaddress
import logging
from urllib.parse import urlparse
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Security & resource constraints
MAX_REPO_SIZE_MB = 500
CLONE_TIMEOUT_SECONDS = 180

# Disallowed private and special IP ranges (RFC 1918, loopback, link-local, cloud metadata)
DISALLOWED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # Private RFC 1918
    ipaddress.ip_network("172.16.0.0/12"),    # Private RFC 1918
    ipaddress.ip_network("192.168.0.0/16"),   # Private RFC 1918
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local / Cloud metadata (AWS/GCP/Azure)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]


class SSRFValidationError(ValueError):
    """Raised when a repository URL fails SSRF security validation."""
    pass


class CloneTimeoutError(TimeoutError):
    """Raised when repository cloning exceeds allowed duration."""
    pass


class RepoSizeExceededError(ValueError):
    """Raised when repository size exceeds allowed quota."""
    pass


def validate_repo_url(url: str) -> str:
    """
    Validates a repository URL to protect against SSRF and unauthorized local access.
    
    Accepts:
      - https://github.com/org/repo (and .git)
      - https://gitlab.com/org/repo
      - https://bitbucket.org/org/repo
      - shorthand 'org/repo' (normalized to https://github.com/org/repo)
    
    Rejects:
      - localhost, 127.0.0.1, ::1
      - RFC 1918 private IP addresses (10.x, 192.168.x, 172.16-31.x)
      - Cloud instance metadata services (169.254.169.254)
      - Non-HTTP/HTTPS protocols (e.g. file://, gopher://, ftp://)
    """
    cleaned = url.strip()
    if not cleaned:
        raise SSRFValidationError("Repository URL cannot be empty.")

    # Support shorthand GitHub notation: "owner/repo"
    if re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", cleaned):
        cleaned = f"https://github.com/{cleaned}"

    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        raise SSRFValidationError(
            f"Invalid URL scheme '{parsed.scheme}'. Only https:// and http:// are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("Could not determine hostname from URL.")

    # Disallow known local identifiers directly
    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "metadata.google.internal"):
        raise SSRFValidationError(f"Target host '{hostname}' is not allowed (local/internal address).")

    # Resolve hostname to IP and check against disallowed CIDRs
    try:
        resolved_ips = socket.getaddrinfo(hostname, None)
        for entry in resolved_ips:
            ip_str = entry[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            for disallowed in DISALLOWED_NETWORKS:
                if ip_obj in disallowed:
                    raise SSRFValidationError(
                        f"Resolved address '{ip_str}' for host '{hostname}' falls within prohibited range '{disallowed}'."
                    )
    except socket.gaierror as e:
        raise SSRFValidationError(f"Could not resolve hostname '{hostname}': {e}")

    return cleaned


def get_dir_size_mb(path: str) -> float:
    """Calculates total size of a directory in megabytes."""
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total_size += os.path.getsize(fp)
            except (OSError, FileNotFoundError):
                pass
    return total_size / (1024 * 1024)


class SandboxedGitCloner:
    """
    Manages cloning a git repository into a sandboxed temporary directory
    with automatic cleanup, timeout protection, and disk size caps.
    """

    def __init__(self, repo_url: str, auth_token: Optional[str] = None):
        self.raw_url = repo_url
        self.validated_url = validate_repo_url(repo_url)
        self.auth_token = auth_token
        self.temp_dir: Optional[str] = None

    def __enter__(self) -> Tuple[str, str]:
        """
        Clones repository into a temporary directory.
        Returns (temp_dir_path, sanitized_repo_name).
        """
        self.temp_dir = tempfile.mkdtemp(prefix="debtscope_clone_")
        
        # Prepare clone URL (inject auth token safely if present)
        clone_url = self.validated_url
        if self.auth_token and "github.com" in clone_url:
            parsed = urlparse(clone_url)
            clone_url = f"https://x-access-token:{self.auth_token}@{parsed.netloc}{parsed.path}"

        logger.info("Cloning %s into sandboxed tempdir %s", self.validated_url, self.temp_dir)
        
        # Clone with history (depth 100 to allow commit mining without downloading 20-year history)
        cmd = [
            "git", "clone",
            "--depth", "100",
            "--no-single-branch",
            clone_url,
            self.temp_dir,
        ]

        try:
            # Mask token in environment / execution logs
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CLONE_TIMEOUT_SECONDS,
                check=False,
            )
            if result.returncode != 0:
                # Sanitize error to avoid leaking tokens in logs or exceptions
                stderr_clean = result.stderr.replace(self.auth_token or "___", "[REDACTED]") if self.auth_token else result.stderr
                raise RuntimeError(f"Git clone failed: {stderr_clean.strip()}")

        except subprocess.TimeoutExpired:
            self.cleanup()
            raise CloneTimeoutError(
                f"Repository clone exceeded timeout of {CLONE_TIMEOUT_SECONDS}s."
            )
        except Exception:
            self.cleanup()
            raise

        # Check directory size
        size_mb = get_dir_size_mb(self.temp_dir)
        if size_mb > MAX_REPO_SIZE_MB:
            self.cleanup()
            raise RepoSizeExceededError(
                f"Cloned repository size ({size_mb:.1f} MB) exceeds maximum allowed size ({MAX_REPO_SIZE_MB} MB)."
            )

        # Extract clean repository name
        parsed = urlparse(self.validated_url)
        repo_name = os.path.basename(parsed.path.rstrip("/")).replace(".git", "") or "repo"

        return self.temp_dir, repo_name

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Guaranteed cleanup of temporary directory."""
        self.cleanup()

    def cleanup(self) -> None:
        """Removes the temporary directory and all contents."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                # Windows read-only git files handling
                def _handle_remove_readonly(func, path, exc):
                    import stat
                    os.chmod(path, stat.S_IWRITE)
                    func(path)

                shutil.rmtree(self.temp_dir, onerror=_handle_remove_readonly)
                logger.info("Cleaned up temporary clone dir %s", self.temp_dir)
            except Exception as e:
                logger.warning("Failed to clean up temp dir %s: %s", self.temp_dir, e)
            finally:
                self.temp_dir = None

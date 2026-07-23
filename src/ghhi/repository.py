from __future__ import annotations

import re
import subprocess
from pathlib import Path


class RepositoryError(ValueError):
    pass


def normalize_repo(value: str) -> str:
    """Turn owner/repo or a common GitHub remote URL into owner/repo."""
    candidate = value.strip().rstrip("/")
    patterns = (
        r"^git@github\.com:(?P<repo>[^/\s]+/[^/\s]+?)(?:\.git)?$",
        r"^(?:https?|ssh)://(?:git@)?github\.com/(?P<repo>[^/\s]+/[^/\s]+?)(?:\.git)?$",
        r"^(?P<repo>[^/:@\s]+/[^/\s]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.match(pattern, candidate, flags=re.IGNORECASE)
        if match:
            repo = match.group("repo")
            repo = repo.removesuffix(".git")
            owner, name = repo.split("/", 1)
            if owner and name:
                return f"{owner}/{name}"
    raise RepositoryError("Use OWNER/REPO or a github.com repository URL")


def discover_repo(cwd: Path | None = None) -> str | None:
    """Return owner/repo from this checkout's origin, if it is hosted on GitHub."""
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        return None
    try:
        return normalize_repo(result.stdout)
    except RepositoryError:
        return None

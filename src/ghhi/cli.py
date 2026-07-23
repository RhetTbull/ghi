from __future__ import annotations

import argparse
import os
from pathlib import Path

from ghhi import __version__
from ghhi.app import IssueApp
from ghhi.repository import RepositoryError, discover_repo, normalize_repo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ghhi", description="A fast, lightweight GitHub issue TUI"
    )
    parser.add_argument(
        "repo",
        nargs="?",
        help="GitHub repository as OWNER/REPO or URL (defaults to this checkout's origin)",
    )
    parser.add_argument(
        "--token",
        help="GitHub access token (prefer GITHUB_ISSUE_ACCESS_TOKEN to avoid shell history)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raw_repo = args.repo or discover_repo(Path.cwd())
    if not raw_repo:
        parser.error("no GitHub origin found; pass a repository as OWNER/REPO")
    try:
        repo = normalize_repo(raw_repo)
    except RepositoryError as error:
        parser.error(str(error))
    token = args.token if args.token is not None else os.getenv("GITHUB_ISSUE_ACCESS_TOKEN", "")
    IssueApp(repo, token).run()


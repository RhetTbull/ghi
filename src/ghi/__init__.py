"""ghi: a quick GitHub issue TUI."""

from importlib.metadata import PackageNotFoundError, version

# Single source of truth is the version in pyproject.toml; `uv version --bump`
# updates it and the lockfile together.
try:
    __version__ = version("ghi")
except PackageNotFoundError:  # running from a source checkout, not installed
    __version__ = "0.0.0+dev"

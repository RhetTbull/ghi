import pytest

from ghi.repository import RepositoryError, normalize_repo


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("owner/repo", "owner/repo"),
        ("owner/repo.git", "owner/repo"),
        ("git@github.com:owner/repo.git", "owner/repo"),
        ("https://github.com/owner/repo.git", "owner/repo"),
        ("ssh://git@github.com/owner/repo", "owner/repo"),
    ],
)
def test_normalize_repo(value: str, expected: str) -> None:
    assert normalize_repo(value) == expected


@pytest.mark.parametrize("value", ["repo", "", "https://gitlab.com/owner/repo"])
def test_normalize_repo_rejects_invalid_values(value: str) -> None:
    with pytest.raises(RepositoryError):
        normalize_repo(value)

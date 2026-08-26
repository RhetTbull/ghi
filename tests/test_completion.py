from __future__ import annotations

import pytest

from ghi.completion import LabelSuggester, matching_labels, parse_labels

AVAILABLE = ["bug", "Enhancement", "documentation", "todo"]


def test_parse_labels_trims_and_drops_blanks() -> None:
    assert parse_labels(" bug ,, todo,") == ["bug", "todo"]


def test_matching_labels_completes_the_final_segment() -> None:
    assert matching_labels("do", AVAILABLE) == ["documentation"]
    assert matching_labels("bug, e", AVAILABLE) == ["Enhancement"]


def test_matching_labels_ignores_case_and_labels_already_used() -> None:
    assert matching_labels("ENHANCE", AVAILABLE) == ["Enhancement"]
    assert matching_labels("bug, todo, ", AVAILABLE) == ["documentation", "Enhancement"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("enh", "Enhancement"),
        ("ENH", "Enhancement"),
        ("bug, doc", "bug, documentation"),
        ("bug,doc", "bug,documentation"),
        ("bug, ", None),
        ("", None),
        ("nope", None),
        ("bug, bug", None),
    ],
)
async def test_suggester_keeps_the_rest_of_the_field(value: str, expected: str | None) -> None:
    assert await LabelSuggester(AVAILABLE).get_suggestion(value) == expected

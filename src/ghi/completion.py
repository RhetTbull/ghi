from __future__ import annotations

from collections.abc import Iterable, Sequence

from textual import events
from textual.suggester import Suggester
from textual.widgets import Input


def parse_labels(value: str) -> list[str]:
    """Split a comma separated label field into individual names."""
    return [item.strip() for item in value.split(",") if item.strip()]


def matching_labels(value: str, available: Sequence[str]) -> list[str]:
    """Labels that can complete the final segment of a comma separated label field.

    Labels already used earlier in the field are left out, so an empty segment
    lists everything still available.
    """
    head, _, typed = value.rpartition(",")
    used = {name.casefold() for name in parse_labels(head)}
    needle = typed.strip().casefold()
    return sorted(
        (
            name
            for name in available
            if name.casefold() not in used and name.casefold().startswith(needle)
        ),
        key=str.casefold,
    )


class LabelSuggester(Suggester):
    """Suggest a repository label for the name being typed at the end of the field."""

    def __init__(self, available: Iterable[str]) -> None:
        # Case sensitive so values arrive unfolded and the suggestion can be
        # rendered as a continuation of what was typed; matching itself is not.
        super().__init__(case_sensitive=True)
        self.available = list(available)

    async def get_suggestion(self, value: str) -> str | None:
        head, comma, typed = value.rpartition(",")
        if not typed.strip():
            return None
        matches = matching_labels(value, self.available)
        if not matches:
            return None
        spacing = typed[: len(typed) - len(typed.lstrip())]
        return f"{head}{comma}{spacing}{matches[0]}"


class LabelInput(Input):
    """Comma separated label entry that completes repository labels as you type.

    The best match is shown inline after the cursor; `Tab` or `Enter` accepts it.
    """

    def __init__(
        self,
        value: str = "",
        available: Iterable[str] = (),
        *,
        id: str | None = None,
    ) -> None:
        self.available = list(available)
        super().__init__(
            value=value,
            placeholder="Labels (comma separated)",
            suggester=LabelSuggester(self.available),
            # Existing labels are appended to rather than replaced, so keep the
            # cursor at the end instead of selecting the field on focus.
            select_on_focus=False,
            id=id,
        )
        self.cursor_position = len(self.value)

    @property
    def labels(self) -> list[str]:
        """The labels currently typed into the field."""
        return parse_labels(self.value)

    def complete(self) -> bool:
        """Accept the inline suggestion, reporting whether there was one to accept."""
        # `_suggestion` is what the widget is currently showing, so accepting it
        # always matches what the user sees.
        suggestion = self._suggestion
        if not suggestion or suggestion == self.value or not self.cursor_at_end:
            return False
        self.value = suggestion
        self.cursor_position = len(self.value)
        return True

    def on_key(self, event: events.Key) -> None:
        # Only swallow the key when a completion happens; otherwise Tab moves
        # focus and Enter submits, as they do in any other field.
        if event.key in ("tab", "enter") and self.complete():
            event.stop()
            event.prevent_default()

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea

from ghi.models import Issue


class Dialog(ModalScreen[object]):
    BINDINGS: ClassVar[list[Binding]] = [Binding("escape", "cancel", "Cancel")]

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "save":
            self.save()

    def save(self) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class IssueForm:
    title: str
    body: str
    labels: list[str]


class IssueDialog(Dialog):
    BINDINGS: ClassVar[list[Binding]] = Dialog.BINDINGS + [Binding("ctrl+s", "save", "Save")]

    def __init__(self, issue: Issue | None = None) -> None:
        super().__init__()
        self.issue = issue

    def compose(self) -> ComposeResult:
        title = "Edit issue" if self.issue else "New issue"
        labels = ", ".join(item.name for item in self.issue.labels) if self.issue else ""
        with Vertical(classes="dialog issue-dialog"):
            yield Label(title, classes="dialog-title")
            yield Input(
                value=self.issue.title if self.issue else "",
                placeholder="Title",
                id="issue-title",
            )
            yield TextArea(self.issue.body if self.issue else "", id="issue-body")
            yield Input(value=labels, placeholder="Labels (comma separated)", id="issue-labels")
            yield Static("Ctrl+S save  •  Esc cancel", classes="hint")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Save", variant="primary", id="save")

    def on_mount(self) -> None:
        self.query_one("#issue-title", Input).focus()

    def action_save(self) -> None:
        self.save()

    def save(self) -> None:
        title = self.query_one("#issue-title", Input).value.strip()
        if not title:
            self.notify("A title is required", severity="warning")
            return
        body = self.query_one("#issue-body", TextArea).text
        labels = [
            item.strip()
            for item in self.query_one("#issue-labels", Input).value.split(",")
            if item.strip()
        ]
        self.dismiss(IssueForm(title, body, labels))


class CommentDialog(Dialog):
    BINDINGS: ClassVar[list[Binding]] = Dialog.BINDINGS + [
        Binding("ctrl+enter", "save", "Post")
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog comment-dialog"):
            yield Label("Add comment", classes="dialog-title")
            yield TextArea(id="comment-body")
            yield Static("Ctrl+Enter post  •  Esc cancel", classes="hint")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Post", variant="primary", id="save")

    def on_mount(self) -> None:
        self.query_one(TextArea).focus()

    def action_save(self) -> None:
        self.save()

    def save(self) -> None:
        body = self.query_one(TextArea).text.strip()
        if not body:
            self.notify("A comment cannot be empty", severity="warning")
            return
        self.dismiss(body)


class LabelsDialog(Dialog):
    def __init__(self, current: list[str], available: list[str]) -> None:
        super().__init__()
        self.current = current
        self.available = available

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog labels-dialog"):
            yield Label("Set labels", classes="dialog-title")
            yield Input(value=", ".join(self.current), id="labels-input")
            yield Static(
                "Available: " + (", ".join(self.available) or "none"), classes="label-options"
            )
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Apply", variant="primary", id="save")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def save(self) -> None:
        labels = [item.strip() for item in self.query_one(Input).value.split(",") if item.strip()]
        self.dismiss(labels)


@dataclass(frozen=True)
class ConnectionForm:
    repo: str
    token: str


class ConnectionDialog(Dialog):
    def __init__(self, repo: str, *, include_token: bool = False) -> None:
        super().__init__()
        self.repo = repo
        self.include_token = include_token

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog connection-dialog"):
            yield Label("Connection", classes="dialog-title")
            yield Input(value=self.repo, placeholder="owner/repo", id="repo-input")
            if self.include_token:
                yield Input(placeholder="GitHub access token", password=True, id="token-input")
                yield Static("Token is kept in memory only.", classes="hint")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Connect", variant="primary", id="save")

    def on_mount(self) -> None:
        self.query_one("#token-input" if self.include_token else "#repo-input", Input).focus()

    def save(self) -> None:
        repo = self.query_one("#repo-input", Input).value.strip()
        token_widget = self.query("#token-input")
        token = token_widget.first(Input).value.strip() if token_widget else ""
        self.dismiss(ConnectionForm(repo, token))


class HelpDialog(Dialog):
    SHORTCUTS = """\
[b]Navigation[/b]
  j / k, ↓ / ↑   Move through issues
  Tab / Shift+Tab Switch between list and details
  PgUp / PgDn     Scroll issue body and comments
  /               Search title, body, number, or label
                  Enter keeps the filter visible; Esc clears it
  s               Cycle open / closed / all
  r               Refresh

[b]Actions[/b]
  n               New issue
  e               Edit selected issue
  c               Add comment
  l               Set labels
  x               Close or reopen
  o               Open in browser

[b]Connection[/b]
  g               Change repository
  t               Set access token (memory only)
  ?               This help
  q               Quit
"""

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog help-dialog"):
            yield Label("Keyboard shortcuts", classes="dialog-title")
            yield Static(self.SHORTCUTS)
            yield Button("Close", id="cancel", variant="primary")

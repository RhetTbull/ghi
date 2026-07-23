from __future__ import annotations

import webbrowser
from datetime import datetime
from typing import Any, ClassVar

from rich.markup import escape
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    Static,
    TextArea,
)

from ghi.api import GitHubAPI, GitHubError
from ghi.dialogs import (
    CommentDialog,
    ConnectionDialog,
    ConnectionForm,
    HelpDialog,
    IssueDialog,
    IssueForm,
    LabelsDialog,
)
from ghi.models import Comment, Issue
from ghi.repository import RepositoryError, normalize_repo


class IssueItem(ListItem):
    def __init__(self, issue: Issue) -> None:
        super().__init__()
        self.issue = issue

    def compose(self) -> ComposeResult:
        icon = "●" if self.issue.state == "open" else "✓"
        labels = " ".join(f"[{label.name}]" for label in self.issue.labels)
        yield Label(
            f"[b]{icon} #{self.issue.number}[/b] {escape(self.issue.title)}\n"
            f"[dim]{escape(labels)}[/dim]"
        )


class IssueApp(App[None]):
    TITLE = "ghi"
    CSS_PATH = "ghi.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
        Binding("j,down", "next_issue", "Next", show=False),
        Binding("k,up", "previous_issue", "Previous", show=False),
        Binding("slash", "search", "Search"),
        Binding("n", "new_issue", "New"),
        Binding("e", "edit_issue", "Edit"),
        Binding("c", "comment", "Comment"),
        Binding("l", "labels", "Labels"),
        Binding("x", "toggle_state", "Close/reopen"),
        Binding("s", "cycle_state", "State"),
        Binding("r", "refresh", "Refresh"),
        Binding("o", "open_browser", "Browser", show=False),
        Binding("g", "change_repo", "Repo", show=False),
        Binding("t", "change_token", "Token", show=False),
        Binding("question_mark", "help", "Help"),
    ]
    TEXT_INPUT_BLOCKED_ACTIONS: ClassVar[frozenset[str]] = frozenset(
        {
            "quit",
            "next_issue",
            "previous_issue",
            "search",
            "new_issue",
            "edit_issue",
            "comment",
            "labels",
            "toggle_state",
            "cycle_state",
            "refresh",
            "open_browser",
            "change_repo",
            "change_token",
            "help",
        }
    )

    def __init__(
        self,
        repo: str,
        token: str = "",
        *,
        api: GitHubAPI | None = None,
    ) -> None:
        super().__init__()
        self.repo = repo
        self.token = token
        self.api = api or GitHubAPI(repo, token)
        self.state_filter = "open"
        self.issues: list[Issue] = []
        self.filtered_issues: list[Issue] = []
        self.comments: dict[int, list[Comment]] = {}

    def compose(self) -> ComposeResult:
        yield Header(icon="")
        with Vertical(id="main"):
            yield Input(placeholder="Search issues… (Esc to clear)", id="search")
            with Horizontal(id="panes"):
                with Vertical(id="issue-pane"):
                    yield Static(id="list-title")
                    yield ListView(id="issues")
                with Vertical(id="detail-pane"), VerticalScroll(id="detail-scroll"):
                    yield Markdown("Select an issue", id="detail")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#search").display = False
        self.query_one("#issues", ListView).focus()
        self.sub_title = self.repo
        self._update_list_title(loading=True)
        self.load_issues()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Let text fields consume letters that are otherwise global shortcuts."""
        if isinstance(self.focused, (Input, TextArea)):
            return action not in self.TEXT_INPUT_BLOCKED_ACTIONS
        return True

    async def on_unmount(self) -> None:
        await self.api.close()

    def _update_list_title(self, *, loading: bool = False) -> None:
        query = self.query_one("#search", Input).value.strip()
        if loading:
            count = "… issues"
        elif query:
            count = f"{len(self.filtered_issues)} of {len(self.issues)} issues"
        else:
            count = f"{len(self.filtered_issues)} issues"
        filter_status = f'  [yellow]filter: “{escape(query)}”[/yellow]' if query else ""
        self.query_one("#list-title", Static).update(
            f"[b]{escape(self.repo)}[/b]  [cyan]{self.state_filter}[/cyan]  "
            f"[dim]{count}[/dim]{filter_status}"
        )

    @work(exclusive=True, group="issues")
    async def load_issues(self) -> None:
        self._update_list_title(loading=True)
        try:
            self.issues = await self.api.list_issues(self.state_filter)
        except GitHubError as error:
            self.notify(str(error), title="GitHub error", severity="error", timeout=8)
            self._update_list_title()
            return
        self.comments.clear()
        await self._apply_search()

    async def _apply_search(self) -> None:
        query = self.query_one("#search", Input).value.strip().casefold()
        if not query:
            self.filtered_issues = list(self.issues)
        else:
            self.filtered_issues = [
                issue
                for issue in self.issues
                if query
                in " ".join(
                    (
                        str(issue.number),
                        f"#{issue.number}",
                        issue.title,
                        issue.body,
                        *(label.name for label in issue.labels),
                    )
                ).casefold()
            ]
        issue_list = self.query_one("#issues", ListView)
        await issue_list.clear()
        await issue_list.extend(IssueItem(issue) for issue in self.filtered_issues)
        self._update_list_title()
        if self.filtered_issues:
            issue_list.index = 0
            self.show_selected_issue()
        else:
            self.query_one("#detail", Markdown).update("_No matching issues._")

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            await self._apply_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search":
            self.query_one("#issues", ListView).focus()

    def on_key(self, event: Any) -> None:
        if event.key == "escape" and self.query_one("#search", Input).display:
            search = self.query_one("#search", Input)
            search.value = ""
            search.display = False
            self.query_one("#issues", ListView).focus()
            event.stop()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if isinstance(event.item, IssueItem):
            self.show_selected_issue()

    @property
    def selected_issue(self) -> Issue | None:
        item = self.query_one("#issues", ListView).highlighted_child
        return item.issue if isinstance(item, IssueItem) else None

    def show_selected_issue(self) -> None:
        issue = self.selected_issue
        if not issue:
            return
        self._render_detail(issue, self.comments.get(issue.number))
        if issue.comments_count and issue.number not in self.comments:
            self.load_comments(issue)

    @work(exclusive=True, group="comments")
    async def load_comments(self, issue: Issue) -> None:
        try:
            comments = await self.api.list_comments(issue.number)
        except GitHubError as error:
            self.notify(str(error), severity="error")
            return
        self.comments[issue.number] = comments
        if self.selected_issue and self.selected_issue.number == issue.number:
            self._render_detail(issue, comments)

    def _render_detail(self, issue: Issue, comments: list[Comment] | None) -> None:
        labels = " · ".join(f"`{label.name}`" for label in issue.labels) or "no labels"
        state = "🟢 OPEN" if issue.state == "open" else "🟣 CLOSED"
        body = issue.body or "_No description._"
        created = _short_date(issue.created_at)
        chunks = [
            f"# #{issue.number} {issue.title}",
            f"**{state}** · {labels}",
            f"Opened by **@{issue.author}** {created}",
            "---",
            body,
        ]
        if issue.comments_count:
            chunks.extend(["---", f"## Comments ({issue.comments_count})"])
            if comments is None:
                chunks.append("_Loading comments…_")
            elif not comments:
                chunks.append("_No comments returned._")
            else:
                for comment in comments:
                    chunks.extend(
                        [
                            f"### @{comment.author} · {_short_date(comment.created_at)}",
                            comment.body or "_Empty comment._",
                        ]
                    )
        self.query_one("#detail", Markdown).update("\n\n".join(chunks))

    def action_next_issue(self) -> None:
        if self.focused is self.query_one("#detail-scroll", VerticalScroll):
            self.query_one("#detail-scroll", VerticalScroll).scroll_down()
            return
        issue_list = self.query_one("#issues", ListView)
        issue_list.action_cursor_down()

    def action_previous_issue(self) -> None:
        if self.focused is self.query_one("#detail-scroll", VerticalScroll):
            self.query_one("#detail-scroll", VerticalScroll).scroll_up()
            return
        issue_list = self.query_one("#issues", ListView)
        issue_list.action_cursor_up()

    def action_search(self) -> None:
        search = self.query_one("#search", Input)
        search.display = True
        search.focus()

    def action_refresh(self) -> None:
        self.load_issues()

    def action_cycle_state(self) -> None:
        states = ["open", "closed", "all"]
        self.state_filter = states[(states.index(self.state_filter) + 1) % len(states)]
        self.load_issues()

    def action_new_issue(self) -> None:
        self.push_screen(IssueDialog(), self._created_issue)

    def action_edit_issue(self) -> None:
        if issue := self.selected_issue:
            self.push_screen(IssueDialog(issue), lambda form: self._edited_issue(issue, form))

    def action_comment(self) -> None:
        if issue := self.selected_issue:
            self.push_screen(CommentDialog(), lambda body: self._posted_comment(issue, body))

    @work
    async def action_labels(self) -> None:
        issue = self.selected_issue
        if not issue:
            return
        try:
            available = await self.api.list_labels()
        except GitHubError as error:
            self.notify(str(error), severity="error")
            return
        self.push_screen(
            LabelsDialog(
                [label.name for label in issue.labels], [label.name for label in available]
            ),
            lambda labels: self._set_labels(issue, labels),
        )

    @work
    async def _created_issue(self, form: IssueForm | None) -> None:
        if not form:
            return
        try:
            issue = await self.api.create_issue(form.title, form.body, form.labels)
        except GitHubError as error:
            self.notify(str(error), severity="error")
            return
        self.state_filter = "open"
        search = self.query_one("#search", Input)
        search.value = ""
        search.display = False
        self.issues = [issue, *(item for item in self.issues if item.number != issue.number)]
        await self._apply_search()
        self._select_number(issue.number)
        self.query_one("#issues", ListView).focus()
        self.notify(f"Created #{issue.number}", title="Issue created")

    @work
    async def _edited_issue(self, issue: Issue, form: IssueForm | None) -> None:
        if not form:
            return
        try:
            await self.api.update_issue(
                issue.number, title=form.title, body=form.body, labels=form.labels
            )
        except GitHubError as error:
            self.notify(str(error), severity="error")
            return
        self.notify(f"Updated #{issue.number}")
        await self._reload_and_select(issue.number)

    @work
    async def _posted_comment(self, issue: Issue, body: str | None) -> None:
        if not body:
            return
        try:
            await self.api.add_comment(issue.number, body)
            fresh = await self.api.get_issue(issue.number)
            self.comments[fresh.number] = await self.api.list_comments(fresh.number)
        except GitHubError as error:
            self.notify(str(error), severity="error")
            return
        self._replace_issue(fresh)
        self._render_detail(fresh, self.comments[fresh.number])
        self.notify(f"Commented on #{issue.number}")

    @work
    async def _set_labels(self, issue: Issue, labels: list[str] | None) -> None:
        if labels is None:
            return
        try:
            await self.api.set_labels(issue.number, labels)
            fresh = await self.api.get_issue(issue.number)
        except GitHubError as error:
            self.notify(str(error), severity="error")
            return
        self._replace_issue(fresh)
        await self._apply_search()
        self._select_number(issue.number)
        self.notify(f"Updated labels on #{issue.number}")

    @work
    async def action_toggle_state(self) -> None:
        issue = self.selected_issue
        if not issue:
            return
        state = "closed" if issue.state == "open" else "open"
        try:
            await self.api.set_state(issue.number, state)
        except GitHubError as error:
            self.notify(str(error), severity="error")
            return
        self.notify(f"{state.title()} #{issue.number}")
        await self._reload_and_select(issue.number)

    def action_open_browser(self) -> None:
        if issue := self.selected_issue:
            webbrowser.open(issue.html_url)

    def action_change_repo(self) -> None:
        self.push_screen(ConnectionDialog(self.repo), self._changed_connection)

    def action_change_token(self) -> None:
        self.push_screen(
            ConnectionDialog(self.repo, include_token=True), self._changed_connection
        )

    @work
    async def _changed_connection(self, form: ConnectionForm | None) -> None:
        if not form:
            return
        try:
            repo = normalize_repo(form.repo)
        except RepositoryError as error:
            self.notify(str(error), severity="error")
            return
        old_api = self.api
        self.repo = repo
        if form.token:
            self.token = form.token
        self.api = GitHubAPI(self.repo, self.token)
        await old_api.close()
        self.sub_title = self.repo
        self.issues.clear()
        self.filtered_issues.clear()
        self.load_issues()

    def action_help(self) -> None:
        self.push_screen(HelpDialog())

    async def _reload_and_select(self, number: int) -> None:
        try:
            self.issues = await self.api.list_issues(self.state_filter)
        except GitHubError as error:
            self.notify(str(error), severity="error")
            return
        await self._apply_search()
        self._select_number(number)

    def _select_number(self, number: int) -> None:
        for index, issue in enumerate(self.filtered_issues):
            if issue.number == number:
                self.query_one("#issues", ListView).index = index
                return

    def _replace_issue(self, fresh: Issue) -> None:
        self.issues = [fresh if issue.number == fresh.number else issue for issue in self.issues]


def _short_date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("on %Y-%m-%d")

from __future__ import annotations

from textual.color import Color

from ghi.app import IssueApp, IssueItem
from ghi.models import Comment, Issue, Label


class FakeAPI:
    def __init__(self) -> None:
        self.repo = "acme/widget"
        self.issues = [
            Issue(
                1,
                "First task",
                "\n".join(f"Description line {line}" for line in range(30)),
                "open",
                "sam",
                (Label("todo"),),
                comments_count=2,
            ),
            Issue(2, "Second task", "Another thing", "open", "lee"),
        ]

    async def list_issues(self, state: str = "open") -> list[Issue]:
        return list(self.issues)

    async def list_comments(self, number: int) -> list[Comment]:
        return [
            Comment("pat", "\n".join(f"Comment line {line}" for line in range(20)), "2026-01-01"),
            Comment("lee", "One more comment", "2026-01-02"),
        ]

    async def create_issue(self, title: str, body: str, labels: list[str]) -> Issue:
        created = Issue(
            3,
            title,
            body,
            "open",
            "me",
            tuple(Label(name) for name in labels),
        )
        self.issues.insert(0, created)
        return created

    async def close(self) -> None:
        pass


async def test_app_loads_and_searches_issues() -> None:
    app = IssueApp("acme/widget", api=FakeAPI())  # type: ignore[arg-type]
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app.filtered_issues) == 2
        await pilot.press("/")
        await pilot.press(*"second")
        assert [issue.number for issue in app.filtered_issues] == [2]
        only_result = app.query_one(IssueItem)
        assert only_result.has_class("-highlight")
        assert only_result.styles.background == Color.parse("#1f6feb")
        assert app.selected_issue is not None
        assert app.selected_issue.number == 2

        await pilot.press("enter")
        search = app.query_one("#search")
        assert search.display
        assert search.value == "second"
        assert app.focused is app.query_one("#issues")
        assert 'filter: “second”' in app.query_one("#list-title").render().plain


async def test_tab_focuses_scrollable_details() -> None:
    app = IssueApp("acme/widget", api=FakeAPI())  # type: ignore[arg-type]
    async with app.run_test(size=(80, 20)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.focused is app.query_one("#issues")

        await pilot.press("tab")
        assert app.focused is app.query_one("#detail-scroll")

        detail = app.query_one("#detail-scroll")
        assert detail.max_scroll_y > 0
        await pilot.press("pagedown")
        await pilot.pause()
        assert detail.scroll_y > 0


async def test_creating_issue_updates_list_immediately() -> None:
    api = FakeAPI()
    app = IssueApp("acme/widget", api=api)  # type: ignore[arg-type]
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.press("n")
        await pilot.press(*"A new todo")
        await pilot.press("ctrl+s")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert app.filtered_issues[0].title == "A new todo"
        assert app.selected_issue is not None
        assert app.selected_issue.title == "A new todo"


async def test_tab_cycles_through_new_issue_fields_and_buttons() -> None:
    app = IssueApp("acme/widget", api=FakeAPI())  # type: ignore[arg-type]
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.press("n")

        focus_order = [app.focused.id]
        for _ in range(5):
            await pilot.press("tab")
            focus_order.append(app.focused.id)

        assert focus_order == [
            "issue-title",
            "issue-body",
            "issue-labels",
            "cancel",
            "save",
            "issue-title",
        ]


async def test_click_immediately_highlights_issue_under_pointer() -> None:
    app = IssueApp("acme/widget", api=FakeAPI())  # type: ignore[arg-type]
    async with app.run_test(size=(100, 30)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()

        clicked = list(app.query(IssueItem))[1]
        await pilot.click(clicked)
        await pilot.pause()

        assert clicked.has_class("-highlight")
        assert clicked.styles.background == Color.parse("#1f6feb")
        assert app.selected_issue is not None
        assert app.selected_issue.number == 2

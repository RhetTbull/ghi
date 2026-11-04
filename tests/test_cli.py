import pytest

from ghi import cli


def test_open_launches_browser_without_starting_tui(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(cli.webbrowser, "open", lambda url: opened.append(url) or True)
    monkeypatch.setattr(cli, "IssueApp", lambda *_: pytest.fail("TUI should not start"))

    cli.main(["acme/widget", "--open", "#42"])

    assert opened == ["https://github.com/acme/widget/issues/42"]


def test_open_uses_checkout_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(cli.webbrowser, "open", lambda url: opened.append(url) or True)
    monkeypatch.setattr(cli, "discover_repo", lambda _: "git@github.com:acme/widget.git")

    cli.main(["-o", "7"])

    assert opened == ["https://github.com/acme/widget/issues/7"]


def test_open_reports_url_when_no_browser(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli.webbrowser, "open", lambda _: False)

    with pytest.raises(SystemExit) as exit_info:
        cli.main(["acme/widget", "--open", "3"])

    assert exit_info.value.code == 1
    assert "https://github.com/acme/widget/issues/3" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["abc", "0", "-5", "#"])
def test_open_rejects_invalid_issue_numbers(value: str) -> None:
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--open", value])

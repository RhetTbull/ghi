from __future__ import annotations

import json

import httpx
import pytest

from ghhi.api import GitHubAPI, GitHubError


def issue(number: int = 1, **updates: object) -> dict[str, object]:
    data: dict[str, object] = {
        "number": number,
        "title": "Ship it",
        "body": "A small task",
        "state": "open",
        "user": {"login": "octocat"},
        "labels": [{"name": "todo", "color": "00ff00"}],
        "comments": 0,
        "html_url": f"https://github.com/acme/widget/issues/{number}",
    }
    data.update(updates)
    return data


@pytest.mark.asyncio
async def test_list_issues_filters_pull_requests_and_sends_auth() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret"
        assert request.url.params["state"] == "open"
        return httpx.Response(200, json=[issue(), issue(2, pull_request={})])

    api = GitHubAPI(
        "acme/widget", "secret", base_url="https://example.test", transport=httpx.MockTransport(handler)
    )
    try:
        issues = await api.list_issues()
    finally:
        await api.close()
    assert [item.number for item in issues] == [1]
    assert issues[0].labels[0].name == "todo"


@pytest.mark.asyncio
async def test_create_update_comment_and_labels_use_expected_endpoints() -> None:
    seen: list[tuple[str, str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        seen.append((request.method, request.url.path, body))
        if request.url.path.endswith("/comments"):
            return httpx.Response(
                201,
                json={"user": {"login": "me"}, "body": body["body"], "created_at": "now"},
            )
        if request.url.path.endswith("/labels"):
            return httpx.Response(200, json=[{"name": "todo", "color": "00ff00"}])
        return httpx.Response(201, json=issue())

    api = GitHubAPI("acme/widget", base_url="https://example.test", transport=httpx.MockTransport(handler))
    try:
        await api.create_issue("Ship it", "Soon", ["todo"])
        await api.update_issue(1, title="Shipped", body="Done", labels=[])
        await api.add_comment(1, "Nice")
        await api.set_labels(1, ["todo"])
        await api.set_state(1, "closed")
    finally:
        await api.close()

    assert seen == [
        ("POST", "/repos/acme/widget/issues", {"title": "Ship it", "body": "Soon", "labels": ["todo"]}),
        ("PATCH", "/repos/acme/widget/issues/1", {"title": "Shipped", "body": "Done", "labels": []}),
        ("POST", "/repos/acme/widget/issues/1/comments", {"body": "Nice"}),
        ("PUT", "/repos/acme/widget/issues/1/labels", {"labels": ["todo"]}),
        ("PATCH", "/repos/acme/widget/issues/1", {"state": "closed"}),
    ]


@pytest.mark.asyncio
async def test_api_errors_are_user_presentable() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, json={"message": "Bad credentials"})
    )
    api = GitHubAPI("acme/widget", base_url="https://example.test", transport=transport)
    try:
        with pytest.raises(GitHubError, match="Bad or expired"):
            await api.list_issues()
    finally:
        await api.close()


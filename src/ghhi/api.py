from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Self

import httpx

from ghhi.models import Comment, Issue, Label


class GitHubError(RuntimeError):
    """A user-presentable GitHub API error."""


class GitHubAPI:
    API_VERSION = "2022-11-28"

    def __init__(
        self,
        repo: str,
        token: str = "",
        *,
        base_url: str = "https://api.github.com",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.repo = repo
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
            "User-Agent": "ghhi",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=20,
            transport=transport,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as error:
            response = error.response
            try:
                detail = response.json().get("message", response.text)
            except ValueError:
                detail = response.text
            if response.status_code == 401:
                detail = "Bad or expired access token"
            elif response.status_code == 403:
                detail = f"Access denied or rate limited: {detail}"
            elif response.status_code == 404:
                detail = f"Repository or issue not found: {self.repo}"
            raise GitHubError(detail or f"GitHub returned HTTP {response.status_code}") from error
        except httpx.RequestError as error:
            raise GitHubError(f"Could not reach GitHub: {error}") from error

    async def _pages(self, path: str, params: dict[str, Any] | None = None) -> AsyncIterator[Any]:
        url: str | None = path
        query = {"per_page": 100, **(params or {})}
        while url:
            response = await self._request("GET", url, params=query)
            for item in response.json():
                yield item
            url = response.links.get("next", {}).get("url")
            query = {}

    async def list_issues(self, state: str = "open") -> list[Issue]:
        rows = [row async for row in self._pages(f"/repos/{self.repo}/issues", {"state": state})]
        return [Issue.from_json(row) for row in rows if "pull_request" not in row]

    async def get_issue(self, number: int) -> Issue:
        response = await self._request("GET", f"/repos/{self.repo}/issues/{number}")
        return Issue.from_json(response.json())

    async def list_comments(self, number: int) -> list[Comment]:
        rows = [
            row
            async for row in self._pages(f"/repos/{self.repo}/issues/{number}/comments")
        ]
        return [Comment.from_json(row) for row in rows]

    async def list_labels(self) -> list[Label]:
        rows = [row async for row in self._pages(f"/repos/{self.repo}/labels")]
        return [Label.from_json(row) for row in rows]

    async def create_issue(self, title: str, body: str, labels: list[str]) -> Issue:
        response = await self._request(
            "POST",
            f"/repos/{self.repo}/issues",
            json={"title": title, "body": body, "labels": labels},
        )
        return Issue.from_json(response.json())

    async def update_issue(
        self, number: int, *, title: str, body: str, labels: list[str]
    ) -> Issue:
        response = await self._request(
            "PATCH",
            f"/repos/{self.repo}/issues/{number}",
            json={"title": title, "body": body, "labels": labels},
        )
        return Issue.from_json(response.json())

    async def set_state(self, number: int, state: str) -> Issue:
        response = await self._request(
            "PATCH", f"/repos/{self.repo}/issues/{number}", json={"state": state}
        )
        return Issue.from_json(response.json())

    async def set_labels(self, number: int, labels: list[str]) -> list[Label]:
        response = await self._request(
            "PUT",
            f"/repos/{self.repo}/issues/{number}/labels",
            json={"labels": labels},
        )
        return [Label.from_json(row) for row in response.json()]

    async def add_comment(self, number: int, body: str) -> Comment:
        response = await self._request(
            "POST", f"/repos/{self.repo}/issues/{number}/comments", json={"body": body}
        )
        return Comment.from_json(response.json())

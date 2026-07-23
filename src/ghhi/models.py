from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Label:
    name: str
    color: str = "888888"
    description: str = ""

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Label:
        return cls(
            name=data["name"],
            color=data.get("color", "888888"),
            description=data.get("description") or "",
        )


@dataclass(frozen=True, slots=True)
class Comment:
    author: str
    body: str
    created_at: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Comment:
        return cls(
            author=data.get("user", {}).get("login", "ghost"),
            body=data.get("body") or "",
            created_at=data.get("created_at", ""),
        )


@dataclass(frozen=True, slots=True)
class Issue:
    number: int
    title: str
    body: str
    state: str
    author: str
    labels: tuple[Label, ...] = field(default_factory=tuple)
    comments_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    html_url: str = ""

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Issue:
        return cls(
            number=data["number"],
            title=data["title"],
            body=data.get("body") or "",
            state=data.get("state", "open"),
            author=data.get("user", {}).get("login", "ghost"),
            labels=tuple(Label.from_json(item) for item in data.get("labels", [])),
            comments_count=data.get("comments", 0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            html_url=data.get("html_url", ""),
        )


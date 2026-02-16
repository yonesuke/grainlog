"""Data models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Page:
    id: int
    title: str
    is_journal: bool = False
    journal_date: str | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Block:
    id: int
    page_id: int
    content: str
    parent_id: int | None = None
    order: int = 0
    collapsed: bool = False
    created_at: str = ""
    updated_at: str = ""
    children: list[Block] = field(default_factory=list)


@dataclass
class Link:
    id: int
    source_block_id: int
    source_page_id: int
    target_page_id: int
    target_title: str


@dataclass
class SearchResult:
    block_id: int
    page_id: int
    page_title: str
    content: str
    highlighted: str

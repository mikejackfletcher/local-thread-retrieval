from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .schema import ParsedChunk, ParsedLink, ParsedNote


FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
TAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_/-]+)")


def parse_markdown(path: Path, text: str) -> ParsedNote:
    front_matter: dict[str, Any] = {}
    body = text
    parse_status = "ok"

    match = FRONT_MATTER_RE.match(text)
    if match:
        try:
            loaded = yaml.safe_load(match.group(1)) or {}
            if isinstance(loaded, dict):
                front_matter = loaded
            else:
                parse_status = "error"
        except yaml.YAMLError:
            parse_status = "error"
        body = text[match.end() :]

    title = _string_value(front_matter.get("title")) or path.stem
    tags = _tags(front_matter.get("tags"), body)
    wikilinks = sorted(set(WIKILINK_RE.findall(body)))
    markdown_links = sorted(set(MARKDOWN_LINK_RE.findall(body)))
    created_at = _datetime_value(front_matter.get("created"))
    updated_at = _datetime_value(front_matter.get("updated"))
    chunks = _chunk_body(body)
    links = [
        *[ParsedLink(target=target, link_type="wikilink") for target in wikilinks],
        *[
            ParsedLink(target=target, link_type="markdown")
            for target in markdown_links
        ],
    ]

    return ParsedNote(
        title=title,
        front_matter=front_matter,
        tags=tags,
        wikilinks=wikilinks,
        links=links,
        created_at=created_at,
        updated_at=updated_at,
        body=body,
        chunks=chunks,
        parse_status=parse_status,
    )


def _chunk_body(body: str) -> list[ParsedChunk]:
    matches = list(HEADING_RE.finditer(body))
    if not matches:
        stripped = body.strip()
        return [
            ParsedChunk(
                section_path=[],
                heading=None,
                text=stripped,
                char_start=0,
                char_end=len(body),
                chunk_index=0,
                retrieval_text=stripped,
            )
        ]

    chunks: list[ParsedChunk] = []
    heading_stack: list[tuple[int, str]] = []
    chunk_index = 0
    if matches[0].start() > 0:
        preamble = body[: matches[0].start()].strip()
        if preamble:
            chunks.append(
                ParsedChunk(
                    section_path=[],
                    heading=None,
                    text=preamble,
                    char_start=0,
                    char_end=matches[0].start(),
                    chunk_index=chunk_index,
                    retrieval_text=preamble,
                )
            )
            chunk_index += 1

    for heading_index, match in enumerate(matches):
        level = len(match.group(1))
        heading = match.group(2).strip()
        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        heading_stack.append((level, heading))

        start = match.start()
        end = (
            matches[heading_index + 1].start()
            if heading_index + 1 < len(matches)
            else len(body)
        )
        text = body[start:end].strip()
        section_path = [item[1] for item in heading_stack]
        chunks.append(
            ParsedChunk(
                section_path=section_path,
                heading=heading,
                text=text,
                char_start=start,
                char_end=end,
                chunk_index=chunk_index,
                retrieval_text="\n".join([*section_path, text]).strip(),
            )
        )
        chunk_index += 1
    return chunks


def _tags(front_matter_tags: Any, body: str) -> list[str]:
    tags: set[str] = set(TAG_RE.findall(body))
    if isinstance(front_matter_tags, str):
        tags.add(front_matter_tags.removeprefix("#"))
    elif isinstance(front_matter_tags, list):
        for value in front_matter_tags:
            if isinstance(value, str):
                tags.add(value.removeprefix("#"))
    return sorted(tags)


def _string_value(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _datetime_value(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

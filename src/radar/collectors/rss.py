from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Callable

import feedparser

from radar.config import Source
from radar.models import TechItem


def _to_iso_date(published: str | None) -> str | None:
    if not published:
        return None
    try:
        return parsedate_to_datetime(published).date().isoformat()
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(published).date().isoformat()
        except ValueError:
            return None


class RssCollector:
    def __init__(self, parse_fn: Callable[[str], object] | None = None):
        self.parse_fn = parse_fn or feedparser.parse

    def collect(self, source: Source, now: str) -> list[TechItem]:
        feed = self.parse_fn(source.url)
        items: list[TechItem] = []
        for entry in getattr(feed, "entries", []):
            link = getattr(entry, "link", "")
            if not link:
                continue
            items.append(TechItem(
                source="rss",
                source_tier=source.tier,
                source_type=source.type,
                title=getattr(entry, "title", ""),
                url=link,
                description=getattr(entry, "summary", ""),
                published_at=_to_iso_date(getattr(entry, "published", None)),
                metrics={},
                raw_id=f"rss:{link}",
                collected_at=now,
            ))
        return items

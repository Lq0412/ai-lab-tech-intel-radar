from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Callable

import feedparser
import httpx

from radar.config import Source
from radar.models import TechItem

USER_AGENT = "TechIntelRadar/1.0 (+https://github.com/Lq0412/ai-lab-tech-intel-radar)"


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
    def __init__(self, parse_fn: Callable[[str], object] | None = None,
                 client: Any | None = None):
        self.parse_fn = parse_fn or feedparser.parse
        self.client = client or httpx.Client(
            timeout=20,
            headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"},
            follow_redirects=True,
        )

    def collect(self, source: Source, now: str) -> list[TechItem]:
        if source.url.startswith("http"):
            resp = self.client.get(source.url)
            resp.raise_for_status()
            feed = self.parse_fn(resp.text)
        else:
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
                metrics={
                    "quota_group": source.quota_group or "rss",
                    "source_name": source.name,
                },
                raw_id=f"rss:{link}",
                collected_at=now,
            ))
        return items

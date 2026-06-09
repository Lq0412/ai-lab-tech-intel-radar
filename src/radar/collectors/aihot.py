from __future__ import annotations

from typing import Any

import httpx

from radar.config import Source
from radar.models import TechItem

API_DAILY = "https://aihot.virxact.com/api/public/daily"
USER_AGENT = "TechIntelRadar/1.0 (+https://github.com/Lq0412/ai-lab-tech-intel-radar)"


class AihotCollector:
    """Fetch AI HOT daily briefing via public JSON API (RSS /rss/daily often returns HTML)."""

    def __init__(self, client: Any | None = None):
        self.client = client or httpx.Client(
            timeout=20, headers={"User-Agent": USER_AGENT}, follow_redirects=True)

    def collect(self, source: Source, now: str) -> list[TechItem]:
        if source.url != "daily":
            return []
        resp = self.client.get(API_DAILY)
        resp.raise_for_status()
        data = resp.json()
        items: list[TechItem] = []
        pub = data.get("date") or now[:10]
        for section in data.get("sections", []):
            label = section.get("label") or ""
            for entry in section.get("items", []):
                title = entry.get("title") or ""
                url = entry.get("url") or entry.get("sourceUrl") or entry.get("link") or ""
                if not title or not url:
                    continue
                summary = entry.get("summary") or ""
                items.append(TechItem(
                    source="rss",
                    source_tier=source.tier,
                    source_type=source.type,
                    title=title,
                    url=url,
                    description=f"{label}: {summary}".strip(": "),
                    published_at=pub,
                    metrics={
                        "section": label,
                        "quota_group": source.quota_group or "aihot",
                        "source_name": source.name,
                    },
                    raw_id=f"aihot:{url}",
                    collected_at=now,
                ))
        for flash in data.get("flashes", []):
            title = flash.get("title") or ""
            url = flash.get("url") or flash.get("sourceUrl") or ""
            if not title or not url:
                continue
            items.append(TechItem(
                source="rss",
                source_tier=source.tier,
                source_type=source.type,
                title=title,
                url=url,
                description=flash.get("summary") or "快讯",
                published_at=pub,
                metrics={
                    "section": "快讯",
                    "quota_group": source.quota_group or "aihot",
                    "source_name": source.name,
                },
                raw_id=f"aihot:{url}",
                collected_at=now,
            ))
        return items

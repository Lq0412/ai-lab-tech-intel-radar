from __future__ import annotations

from radar.config import Settings
from radar.models import TechItem


def _keeps(item: TechItem, settings: Settings) -> bool:
    if item.source == "github":
        return item.metrics.get("stars", 0) >= settings.github_min_stars
    if item.source == "rss":
        text = f"{item.title} {item.description}".lower()
        return any(kw in text for kw in settings.keywords)
    return True


def apply_filters(items: list[TechItem],
                  settings: Settings) -> tuple[list[TechItem], list[TechItem]]:
    kept, dropped = [], []
    for it in items:
        (kept if _keeps(it, settings) else dropped).append(it)
    return kept, dropped

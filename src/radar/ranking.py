from __future__ import annotations

import math
from collections.abc import Callable
from datetime import date

from radar.config import Settings
from radar.models import Analysis, TechItem


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def freshness_score(published_at: str | None, today: str) -> int:
    d = _parse_date(published_at)
    if d is None:
        return 3
    age = (_parse_date(today) - d).days
    if age <= 1:
        return 5
    if age <= 7:
        return 4
    if age <= 30:
        return 3
    if age <= 90:
        return 2
    return 1


def compute_quality(analysis: Analysis, source_tier: str,
                    published_at: str | None, settings: Settings,
                    today: str, bonus: float = 0.0) -> float:
    w = settings.weights
    tier_w = settings.tier_weight.get(source_tier, 2)
    fresh = freshness_score(published_at, today)
    score = (
        w["practicality"] * analysis.practicality
        + w["influence"] * analysis.influence
        + w.get("novelty", 0) * analysis.novelty
        + w["follow_cost"] * analysis.follow_cost
        + w["source_tier"] * tier_w
        + w["freshness"] * fresh
        + bonus
    )
    return round(score, 2)


def recommend(quality_score: float, category: str, settings: Settings) -> str:
    threshold = settings.threshold_for(category)
    if quality_score >= threshold:
        return "建议跟进"
    if quality_score >= threshold - 1.0:
        return "保持观察"
    return "暂不投入"


def signal_score(item: TechItem, settings: Settings, today: str,
                 growth: int = 0) -> float:
    """Pre-LLM signal strength for candidate prioritization."""
    tier = settings.tier_weight.get(item.source_tier, 2)
    fresh = freshness_score(item.published_at, today)
    growth_signal = math.log10(max(growth, 1)) * 12
    if item.source == "github":
        stars = item.metrics.get("stars", 0)
        return tier * 6 + growth_signal + math.log10(max(stars, 1)) * 2 + fresh * 2
    if item.source == "huggingface":
        downloads = item.metrics.get("downloads", 0)
        return tier * 6 + growth_signal + math.log10(max(downloads, 1)) * 2 + fresh * 2
    return tier * 4 + fresh * 3


def quota_key(item: TechItem) -> str:
    """Map item to analyze quota bucket (supports split RSS groups)."""
    group = item.metrics.get("quota_group")
    if group:
        return str(group)
    if item.raw_id.startswith("aihot:"):
        return "aihot"
    url = item.url.lower()
    if "qbitai.com" in url or "infoq.cn" in url:
        return "rss_chinese"
    if "openai.com" in url or "huggingface.co/blog" in url:
        return "rss_official"
    return item.source


def _rank_key(item: TechItem, settings: Settings, today: str,
              growth_of: Callable[[str], int] | None) -> float:
    growth = growth_of(item.raw_id) if growth_of else 0
    return signal_score(item, settings, today, growth=growth)


def select_candidates(items: list[TechItem], limit: int | None,
                      today: str, settings: Settings,
                      growth_of: Callable[[str], int] | None = None) -> list[TechItem]:
    if limit is None or limit <= 0 or len(items) <= limit:
        return items
    ranked = sorted(
        items,
        key=lambda it: _rank_key(it, settings, today, growth_of),
        reverse=True,
    )
    return ranked[:limit]


def select_by_quota(items: list[TechItem], quota: dict[str, int],
                    today: str, settings: Settings,
                    growth_of: Callable[[str], int] | None = None) -> list[TechItem]:
    """Pick top signal_score items per source according to quota."""
    selected: list[TechItem] = []
    for source, n in quota.items():
        if n <= 0:
            continue
        group = sorted(
            [it for it in items if quota_key(it) == source],
            key=lambda it: _rank_key(it, settings, today, growth_of),
            reverse=True,
        )
        selected.extend(group[:n])
    return selected

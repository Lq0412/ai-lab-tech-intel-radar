from __future__ import annotations

import math
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
                    today: str) -> float:
    w = settings.weights
    tier_w = settings.tier_weight.get(source_tier, 2)
    fresh = freshness_score(published_at, today)
    score = (
        w["practicality"] * analysis.practicality
        + w["influence"] * analysis.influence
        + w["follow_cost"] * analysis.follow_cost
        + w["source_tier"] * tier_w
        + w["freshness"] * fresh
    )
    return round(score, 2)


def recommend(quality_score: float, category: str, settings: Settings) -> str:
    threshold = settings.threshold_for(category)
    if quality_score >= threshold:
        return "建议跟进"
    if quality_score >= threshold - 1.0:
        return "保持观察"
    return "暂不投入"


def signal_score(item: TechItem, settings: Settings, today: str) -> float:
    """Pre-LLM signal strength for candidate prioritization."""
    tier = settings.tier_weight.get(item.source_tier, 2)
    fresh = freshness_score(item.published_at, today)
    if item.source == "github":
        stars = item.metrics.get("stars", 0)
        return tier * 10 + math.log10(max(stars, 1)) * 5 + fresh
    if item.source == "huggingface":
        downloads = item.metrics.get("downloads", 0)
        likes = item.metrics.get("likes", 0)
        return (
            tier * 10
            + math.log10(max(downloads, 1)) * 4
            + math.log10(max(likes, 1)) * 2
            + fresh
        )
    return tier * 10 + fresh * 2


def select_candidates(items: list[TechItem], limit: int | None,
                      today: str, settings: Settings) -> list[TechItem]:
    if limit is None or limit <= 0 or len(items) <= limit:
        return items
    ranked = sorted(
        items,
        key=lambda it: signal_score(it, settings, today),
        reverse=True,
    )
    return ranked[:limit]


def select_by_quota(items: list[TechItem], quota: dict[str, int],
                    today: str, settings: Settings) -> list[TechItem]:
    """Pick top signal_score items per source according to quota."""
    selected: list[TechItem] = []
    for source, n in quota.items():
        if n <= 0:
            continue
        group = sorted(
            [it for it in items if it.source == source],
            key=lambda it: signal_score(it, settings, today),
            reverse=True,
        )
        selected.extend(group[:n])
    return selected

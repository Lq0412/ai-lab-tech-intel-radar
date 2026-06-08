from __future__ import annotations

from datetime import date

from radar.config import Settings
from radar.models import Analysis


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

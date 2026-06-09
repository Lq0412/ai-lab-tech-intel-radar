from __future__ import annotations

from radar.config import Settings
from radar.models import TechItem

# Dedicated AI feeds — skip English keyword gate (titles are often Chinese-only).
_TRUSTED_RSS_DOMAINS = (
    "aihot.virxact.com",
    "qbitai.com",
    "infoq.cn",
)

# HuggingFace model-id markers for throwaway/test/placeholder checkpoints.
_HF_JUNK_MARKERS = (
    "tiny-random",
    "tiny-",
    "-tiny",
    "internal-testing",
    "test-",
    "-test",
    "random-",
    "dummy",
    "debug",
)


def _is_noise(item: TechItem, settings: Settings) -> bool:
    text = f"{item.title} {item.description}".lower()
    return any(kw in text for kw in settings.noise_keywords)


def _is_hf_junk(item: TechItem) -> bool:
    name = (item.title or item.raw_id).lower()
    return any(marker in name for marker in _HF_JUNK_MARKERS)


def _keeps(item: TechItem, settings: Settings) -> bool:
    if item.source == "github":
        if _is_noise(item, settings):
            return False
        return item.metrics.get("stars", 0) >= settings.github_min_stars
    if item.source == "huggingface":
        if _is_noise(item, settings) or _is_hf_junk(item):
            return False
        return item.metrics.get("downloads", 0) >= settings.hf_min_downloads
    if item.source == "rss":
        url_l = item.url.lower()
        if any(d in url_l for d in _TRUSTED_RSS_DOMAINS):
            return True
        text = f"{item.title} {item.description}".lower()
        return any(kw in text for kw in settings.keywords)
    return True


def apply_filters(items: list[TechItem],
                  settings: Settings) -> tuple[list[TechItem], list[TechItem]]:
    kept, dropped = [], []
    for it in items:
        (kept if _keeps(it, settings) else dropped).append(it)
    return kept, dropped

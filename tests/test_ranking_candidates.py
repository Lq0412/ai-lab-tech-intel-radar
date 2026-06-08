from radar.models import TechItem
from radar.config import Settings
from radar.ranking import signal_score, select_candidates


def settings():
    return Settings(
        weights={"practicality": 0.35, "influence": 0.30, "follow_cost": 0.20,
                 "source_tier": 0.10, "freshness": 0.05},
        tier_weight={"T1": 5, "T1.5": 4, "T2": 2},
        thresholds={"default": 4.0},
        github_min_stars=500, github_min_weekly_growth=50,
        keywords=[], title_similarity_threshold=0.6, time_window_days=7)


def item(source, title, stars=0, downloads=0, tier="T1.5"):
    metrics = {}
    if source == "github":
        metrics = {"stars": stars}
    elif source == "huggingface":
        metrics = {"downloads": downloads, "likes": 100}
    return TechItem(
        source=source, source_tier=tier, source_type="repo_index",
        title=title, url="u", description="", published_at="2026-06-08",
        metrics=metrics, raw_id=f"{source}:{title}", collected_at="2026-06-08",
    )


def test_signal_score_prefers_high_star_github():
    s = settings()
    high = signal_score(item("github", "a", stars=50000), s, "2026-06-08")
    low = signal_score(item("github", "b", stars=600), s, "2026-06-08")
    assert high > low


def test_select_candidates_limits_and_prioritizes_github():
    s = settings()
    items = [
        item("rss", "blog", tier="T1"),
        item("github", "big", stars=90000),
        item("github", "small", stars=800),
        item("huggingface", "model", downloads=2_000_000),
    ]
    picked = select_candidates(items, limit=2, today="2026-06-08", settings=s)
    assert len(picked) == 2
    assert picked[0].source in ("github", "huggingface")

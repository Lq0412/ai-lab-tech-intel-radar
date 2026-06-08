from radar.models import TechItem
from radar.config import Settings
from radar.pipeline.filter import apply_filters


def settings():
    return Settings(weights={}, tier_weight={}, thresholds={"default": 4.0},
                    github_min_stars=500, github_min_weekly_growth=50,
                    keywords=["llm", "model"], title_similarity_threshold=0.6,
                    time_window_days=7)


def gh(stars, raw="github:a/b"):
    return TechItem(source="github", source_tier="T1.5", source_type="repo_index",
                    title="repo", url="u", description="", published_at=None,
                    metrics={"stars": stars}, raw_id=raw,
                    collected_at="2026-06-08T00:00:00")


def rss(title, desc, raw="rss:u"):
    return TechItem(source="rss", source_tier="T1", source_type="official_blog",
                    title=title, url="u", description=desc, published_at=None,
                    metrics={}, raw_id=raw, collected_at="2026-06-08T00:00:00")


def test_github_below_star_threshold_is_dropped():
    kept, dropped = apply_filters([gh(100)], settings())
    assert kept == [] and len(dropped) == 1


def test_github_above_threshold_is_kept():
    kept, _ = apply_filters([gh(900)], settings())
    assert len(kept) == 1


def test_rss_without_keyword_is_dropped():
    kept, dropped = apply_filters([rss("Cooking recipe", "no tech here")], settings())
    assert kept == [] and len(dropped) == 1


def test_rss_with_keyword_is_kept():
    kept, _ = apply_filters([rss("New LLM released", "great model")], settings())
    assert len(kept) == 1

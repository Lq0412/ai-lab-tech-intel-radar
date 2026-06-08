from pathlib import Path
from radar.config import load_settings, load_sources, Settings


def test_load_sources_parses_entries():
    sources = load_sources(Path("config/sources.yaml"))
    assert len(sources) >= 4
    gh = [s for s in sources if s.kind == "github"][0]
    assert gh.tier == "T1.5"
    assert gh.name == "GitHub Trending AI"


def test_load_settings_exposes_weights_and_thresholds():
    s: Settings = load_settings(Path("config/settings.yaml"))
    assert abs(sum(s.weights.values()) - 1.0) < 1e-6
    assert s.tier_weight["T1"] == 5
    assert s.threshold_for("model") == 3.5
    assert s.threshold_for("unknown_category") == s.thresholds["default"]


def test_settings_has_tuning_defaults():
    s = Settings(
        weights={}, tier_weight={}, thresholds={"default": 4.0},
        github_min_stars=500, github_min_weekly_growth=50, keywords=[],
        title_similarity_threshold=0.6, time_window_days=7)
    assert s.max_recommendations == 8
    assert s.github_per_page == 50
    assert s.analyze_quota == {"github": 20, "huggingface": 15, "rss": 15}


def test_load_settings_reads_tuning_fields():
    s = load_settings(Path("config/settings.yaml"))
    assert s.max_recommendations == 8
    assert s.github_per_page == 50
    assert s.analyze_quota["github"] >= 1

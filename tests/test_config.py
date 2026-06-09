from pathlib import Path
from radar.config import load_settings, load_sources, Settings


def test_load_sources_parses_entries():
    sources = load_sources(Path("config/sources.yaml"))
    assert len(sources) >= 10
    gh = [s for s in sources if s.kind == "github"][0]
    assert gh.tier == "T1.5"
    assert gh.name == "GitHub Trending AI"
    cn = [s for s in sources if s.name == "AI HOT 精选"][0]
    assert cn.url == "https://aihot.virxact.com/feed"
    assert cn.tier == "T1.5"


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


def test_source_sort_defaults_empty():
    from radar.config import Source
    s = Source(name="gh", url="topic:llm", tier="T1.5",
               type="repo_index", kind="github")
    assert s.sort == ""


def test_source_quota_group_defaults_empty():
    from radar.config import Source
    s = Source(name="InfoQ 中文", url="https://www.infoq.cn/feed", tier="T2",
               type="media", kind="rss")
    assert s.quota_group == ""


def test_load_settings_reads_split_rss_quota():
    s = load_settings(Path("config/settings.yaml"))
    assert s.analyze_quota["rss_chinese"] >= 1
    assert s.analyze_quota["rss_official"] >= 1
    assert "rss" not in s.analyze_quota


def test_load_sources_reads_quota_group():
    cn = [s for s in load_sources(Path("config/sources.yaml"))
          if s.name == "量子位"][0]
    assert cn.quota_group == "rss_chinese"


def test_settings_has_hf_and_bonus_defaults():
    s = Settings(
        weights={}, tier_weight={}, thresholds={"default": 4.0},
        github_min_stars=500, github_min_weekly_growth=50, keywords=[],
        title_similarity_threshold=0.6, time_window_days=7)
    assert s.hf_min_downloads >= 0
    assert isinstance(s.source_bonus, dict)


def test_load_settings_reads_hf_and_bonus():
    s = load_settings(Path("config/settings.yaml"))
    assert s.hf_min_downloads >= 1
    assert s.source_bonus.get("rss_chinese", 0) > 0


def test_settings_has_noise_keywords_default():
    s = Settings(
        weights={}, tier_weight={}, thresholds={"default": 4.0},
        github_min_stars=500, github_min_weekly_growth=50, keywords=[],
        title_similarity_threshold=0.6, time_window_days=7)
    assert "awesome" in s.noise_keywords
    assert "tutorial" in s.noise_keywords

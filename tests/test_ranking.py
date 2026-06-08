from radar.models import Analysis
from radar.config import Settings
from radar.ranking import freshness_score, compute_quality, recommend


def settings():
    return Settings(
        weights={"practicality": 0.35, "influence": 0.30, "follow_cost": 0.20,
                 "source_tier": 0.10, "freshness": 0.05},
        tier_weight={"T1": 5, "T1.5": 4, "T2": 2},
        thresholds={"tool_framework": 3.8, "default": 4.0},
        github_min_stars=500, github_min_weekly_growth=50, keywords=[],
        title_similarity_threshold=0.6, time_window_days=7)


def test_freshness_full_for_today():
    assert freshness_score("2026-06-08", today="2026-06-08") == 5
    assert freshness_score(None, today="2026-06-08") == 3


def test_freshness_decays_with_age():
    assert freshness_score("2026-05-01", today="2026-06-08") < 5


def test_compute_quality_matches_formula():
    a = Analysis(item_id=1, is_relevant=True, practicality=5, influence=5,
                 follow_cost=4)
    score = compute_quality(a, source_tier="T1.5", published_at="2026-06-08",
                            settings=settings(), today="2026-06-08")
    # 0.35*5 + 0.30*5 + 0.20*4 + 0.10*4 + 0.05*5 = 4.7
    assert abs(score - 4.7) < 1e-6


def test_recommend_uses_category_threshold():
    s = settings()
    assert recommend(4.0, "tool_framework", s) == "建议跟进"   # >=3.8
    assert recommend(3.0, "tool_framework", s) == "保持观察"   # >=3.8-1.0
    assert recommend(2.0, "tool_framework", s) == "暂不投入"

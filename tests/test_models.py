from radar.models import TechItem, Analysis, ScoredItem


def test_techitem_roundtrips_through_dict():
    item = TechItem(
        source="github",
        source_tier="T1.5",
        source_type="repo_index",
        title="vLLM",
        url="https://github.com/vllm-project/vllm",
        description="High-throughput LLM inference engine",
        published_at="2026-06-01",
        metrics={"stars": 85000, "weekly_growth": 1200},
        raw_id="github:vllm-project/vllm",
        collected_at="2026-06-08T00:00:00",
    )
    restored = TechItem.from_dict(item.to_dict())
    assert restored == item
    assert restored.metrics["stars"] == 85000


def test_analysis_defaults_to_irrelevant():
    a = Analysis(item_id=1, is_relevant=False)
    assert a.category == ""
    assert a.practicality == 0


def test_scored_item_carries_recommendation():
    s = ScoredItem(item_id=1, quality_score=4.65, recommendation="建议跟进")
    assert s.recommendation == "建议跟进"

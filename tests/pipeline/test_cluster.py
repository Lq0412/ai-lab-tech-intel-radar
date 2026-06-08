from radar.models import TechItem
from radar.pipeline.cluster import cluster_items, primary_priority


def item(raw_id, title, url, tier, stype):
    return TechItem(source="x", source_tier=tier, source_type=stype,
                    title=title, url=url, description="", published_at="2026-06-01",
                    metrics={}, raw_id=raw_id, collected_at="2026-06-08T00:00:00")


def test_primary_priority_prefers_official_blog():
    assert primary_priority("official_blog", "T1") > primary_priority("article", "T2")


def test_cluster_groups_similar_titles_and_picks_official_primary():
    items = [
        item("a", "GPT-5 released today", "https://media.com/x", "T2", "article"),
        item("b", "GPT-5 is released today", "https://openai.com/g5", "T1", "official_blog"),
    ]
    clusters = cluster_items(items, threshold=0.6)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.primary.raw_id == "b"
    assert [m.raw_id for m in cluster.members] == ["a"] or [m.raw_id for m in cluster.members] == ["a", "b"]
    assert cluster.related_urls == ["https://media.com/x"]


def test_cluster_keeps_distinct_events_separate():
    items = [
        item("a", "vLLM new release", "https://github.com/vllm", "T1.5", "repo_index"),
        item("b", "New vision dataset", "https://hf.co/ds", "T1.5", "model_index"),
    ]
    clusters = cluster_items(items, threshold=0.6)
    assert len(clusters) == 2

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


def _gh_hf_items():
    gh = TechItem(
        source="github", source_tier="T1.5", source_type="repo_index",
        title="meta-llama/Llama-3.1-8B-Instruct",
        url="https://github.com/meta-llama/Llama-3.1-8B-Instruct",
        description="Llama 3.1 instruct model", published_at="2026-06-01",
        metrics={"stars": 5000}, raw_id="github:meta-llama/Llama-3.1-8B-Instruct",
        collected_at="2026-06-08T00:00:00",
    )
    hf = TechItem(
        source="huggingface", source_tier="T1.5", source_type="model_index",
        title="meta-llama/Llama-3.1-8B-Instruct",
        url="https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct",
        description="text-generation", published_at="2026-06-01",
        metrics={"downloads": 1_000_000}, raw_id="huggingface:meta-llama/Llama-3.1-8B-Instruct",
        collected_at="2026-06-08T00:00:00",
    )
    return gh, hf


def test_cluster_groups_github_and_huggingface_same_model():
    gh, hf = _gh_hf_items()
    clusters = cluster_items([gh, hf], threshold=0.6)
    assert len(clusters) == 1
    assert len(clusters[0].related_urls) == 1


def test_cluster_groups_rss_blog_with_hf_model():
    _, hf = _gh_hf_items()
    blog = TechItem(
        source="rss", source_tier="T1", source_type="official_blog",
        title="Llama 3.1 8B is now available",
        url="https://huggingface.co/blog/llama-31",
        description="Meta releases Llama-3.1-8B-Instruct on Hugging Face",
        published_at="2026-06-08", metrics={}, raw_id="rss:llama-blog",
        collected_at="2026-06-08T00:00:00",
    )
    clusters = cluster_items([blog, hf], threshold=0.6)
    assert len(clusters) == 1
    assert clusters[0].primary.source_type == "official_blog"
    assert len(clusters[0].related_urls) == 1

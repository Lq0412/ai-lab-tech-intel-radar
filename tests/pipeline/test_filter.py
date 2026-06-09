from radar.models import TechItem
from radar.config import Settings
from radar.pipeline.filter import apply_filters


def settings():
    return Settings(weights={}, tier_weight={}, thresholds={"default": 4.0},
                    github_min_stars=500, github_min_weekly_growth=50,
                    keywords=["llm", "model"], title_similarity_threshold=0.6,
                    time_window_days=7, hf_min_downloads=10000,
                    noise_keywords=["awesome", "tutorial", "deepfake",
                                    "face swap", "faceswap"])


def hf(raw, downloads=100000, title="org/model"):
    return TechItem(source="huggingface", source_tier="T1.5",
                    source_type="model_index", title=title, url="u",
                    description="", published_at=None,
                    metrics={"downloads": downloads, "likes": 10}, raw_id=raw,
                    collected_at="2026-06-08T00:00:00")


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


def test_rss_trusted_chinese_feed_kept_without_english_keyword():
    item = TechItem(
        source="rss", source_tier="T2", source_type="media",
        title="国产大模型发布新版本", url="https://www.qbitai.com/2026/01/01.html",
        description="纯中文报道，无英文关键词", published_at=None,
        metrics={}, raw_id="rss:cn-1", collected_at="2026-06-08T00:00:00",
    )
    kept, dropped = apply_filters([item], settings())
    assert len(kept) == 1
    assert dropped == []


def test_hf_low_downloads_dropped():
    kept, dropped = apply_filters([hf("hf:org/m", downloads=500)], settings())
    assert kept == [] and len(dropped) == 1


def test_hf_enough_downloads_kept():
    kept, _ = apply_filters([hf("hf:org/m", downloads=2_000_000)], settings())
    assert len(kept) == 1


def test_hf_tiny_test_model_dropped_even_with_downloads():
    items = [
        hf("hf:hmellor/tiny-random-LlamaForCausalLM", downloads=5_000_000,
           title="hmellor/tiny-random-LlamaForCausalLM"),
        hf("hf:trl-internal-testing/tiny-Qwen2", downloads=5_000_000,
           title="trl-internal-testing/tiny-Qwen2"),
    ]
    kept, dropped = apply_filters(items, settings())
    assert kept == []
    assert len(dropped) == 2


def test_github_deepfake_dropped():
    item = TechItem(
        source="github", source_tier="T1.5", source_type="repo_index",
        title="hacksider/Deep-Live-Cam", url="u",
        description="real time face swap and one-click video deepfake",
        published_at=None, metrics={"stars": 90000},
        raw_id="github:hacksider/Deep-Live-Cam",
        collected_at="2026-06-08T00:00:00",
    )
    kept, dropped = apply_filters([item], settings())
    assert kept == [] and len(dropped) == 1


def test_filter_drops_noise_repos():
    kept, dropped = apply_filters([
        TechItem(
            source="github", source_tier="T1.5", source_type="repo_index",
            title="foo/awesome-llm-list", url="u",
            description="A curated awesome list of LLM tools",
            published_at=None, metrics={"stars": 50000},
            raw_id="github:foo/awesome-llm-list",
            collected_at="2026-06-08T00:00:00",
        ),
        TechItem(
            source="github", source_tier="T1.5", source_type="repo_index",
            title="acme/inference-server", url="u",
            description="High-throughput LLM inference",
            published_at=None, metrics={"stars": 3000},
            raw_id="github:acme/inference-server",
            collected_at="2026-06-08T00:00:00",
        ),
    ], settings())
    assert len(kept) == 1
    assert kept[0].title == "acme/inference-server"
    assert any("awesome" in d.title.lower() for d in dropped)

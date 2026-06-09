from radar.pipeline.dedup import (canonical_entity, normalize_url,
                                  title_similarity, same_event)


def test_normalize_url_strips_query_and_trailing_slash():
    assert normalize_url("https://X.com/a/?utm=1") == "https://x.com/a"
    assert normalize_url("https://x.com/a") == "https://x.com/a"


def test_title_similarity_high_for_near_duplicates():
    s = title_similarity("vLLM v0.5 released", "vLLM v0.5 is released")
    assert s > 0.6


def test_same_event_true_when_urls_match_after_normalize():
    assert same_event("https://x.com/a?ref=1", "https://x.com/a/", "t1", "t2",
                      threshold=0.6) is True


def test_same_event_true_when_titles_similar():
    assert same_event("https://a.com/x", "https://b.com/y",
                      "GPT-5 released today", "GPT-5 is released today",
                      threshold=0.6) is True


def test_same_event_false_when_unrelated():
    assert same_event("https://a.com/x", "https://b.com/y",
                      "vLLM update", "New dataset for vision",
                      threshold=0.6) is False


def test_canonical_entity_from_repo_slug():
    assert canonical_entity("meta-llama/Llama-3.1-8B-Instruct") == \
        "meta-llama/llama-3.1-8b-instruct"


def test_same_event_true_for_matching_github_and_hf_slug():
    assert same_event(
        "https://github.com/meta-llama/Llama-3.1-8B-Instruct",
        "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
        threshold=0.6,
    ) is True


def test_same_event_true_when_rss_mentions_model_slug():
    assert same_event(
        "https://huggingface.co/deepseek-ai/DeepSeek-R1-0528",
        "https://huggingface.co/blog/deepseek-r1",
        "deepseek-ai/DeepSeek-R1-0528",
        "DeepSeek R1 0528 release notes",
        threshold=0.6,
        desc_b="Announcing DeepSeek-R1-0528 on Hugging Face",
    ) is True

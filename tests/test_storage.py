from radar.models import TechItem, Analysis
from radar.storage import Repository


def make_item(raw_id="github:a/b", url="https://x/1", title="vLLM"):
    return TechItem(
        source="github", source_tier="T1.5", source_type="repo_index",
        title=title, url=url, description="d", published_at="2026-06-01",
        metrics={"stars": 1000}, raw_id=raw_id, collected_at="2026-06-08T00:00:00",
    )


def test_insert_and_fetch_item():
    repo = Repository(":memory:")
    repo.init_schema()
    item_id = repo.upsert_item(make_item())
    rows = repo.list_items()
    assert len(rows) == 1
    assert rows[0].metrics["stars"] == 1000
    assert item_id > 0


def test_upsert_is_idempotent_on_raw_id():
    repo = Repository(":memory:")
    repo.init_schema()
    first = repo.upsert_item(make_item(title="old"))
    second = repo.upsert_item(make_item(title="new"))
    assert first == second
    rows = repo.list_items()
    assert len(rows) == 1
    assert rows[0].title == "new"


def test_save_and_read_analysis():
    repo = Repository(":memory:")
    repo.init_schema()
    item_id = repo.upsert_item(make_item())
    repo.save_analysis(
        Analysis(item_id=item_id, is_relevant=True, category="tool_framework",
                 summary="s", practicality=5, influence=5, follow_cost=4),
        quality_score=4.65, recommendation="建议跟进",
    )
    scored = repo.list_scored()
    assert len(scored) == 1
    assert scored[0].quality_score == 4.65
    assert scored[0].recommendation == "建议跟进"


def test_save_analysis_persists_novelty_and_highlight():
    repo = Repository(":memory:")
    repo.init_schema()
    item_id = repo.upsert_item(make_item())
    repo.save_analysis(
        Analysis(item_id=item_id, is_relevant=True, category="tool_framework",
                 summary="s", practicality=5, influence=5, follow_cost=4,
                 novelty=4, highlight="本周重大更新"),
        quality_score=4.5, recommendation="建议跟进",
    )
    row = repo.get_analysis_row(item_id)
    assert row["novelty"] == 4
    assert row["highlight"] == "本周重大更新"


def test_cluster_member_urls_returns_siblings():
    repo = Repository(":memory:")
    repo.init_schema()
    a = make_item(raw_id="github:a/b", url="https://github.com/a/b")
    b = make_item(raw_id="huggingface:a/b", url="https://huggingface.co/a/b",
                  title="a/b")
    b.source = "huggingface"
    id_a = repo.upsert_item(a)
    id_b = repo.upsert_item(b)
    repo.set_cluster(id_a, cluster_id=0, is_duplicate=False)
    repo.set_cluster(id_b, cluster_id=0, is_duplicate=True)
    assert repo.cluster_member_urls("github:a/b") == ["https://huggingface.co/a/b"]
    assert repo.cluster_member_urls("huggingface:a/b") == ["https://github.com/a/b"]


def test_metric_snapshot_and_weekly_growth(tmp_path):
    repo = Repository(str(tmp_path / "t.db"))
    repo.init_schema()
    repo.record_snapshot("github:a/b", 1000, captured_at="2026-06-01")
    repo.record_snapshot("github:a/b", 1500, captured_at="2026-06-09")
    assert repo.weekly_growth("github:a/b", today="2026-06-09") == 500
    assert repo.weekly_growth("github:x/y", today="2026-06-09") == 0

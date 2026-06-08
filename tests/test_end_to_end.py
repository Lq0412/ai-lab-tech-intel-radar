from radar.models import TechItem
from radar.config import Settings
from radar.storage import Repository
from radar import cli


def settings():
    return Settings(
        weights={"practicality": 0.35, "influence": 0.30, "follow_cost": 0.20,
                 "source_tier": 0.10, "freshness": 0.05},
        tier_weight={"T1": 5, "T1.5": 4, "T2": 2},
        thresholds={"tool_framework": 3.8, "default": 4.0},
        github_min_stars=500, github_min_weekly_growth=50,
        keywords=["llm", "model", "inference"],
        title_similarity_threshold=0.6, time_window_days=7)


class StubClient:
    def complete_json(self, system, user):
        if "is_relevant" in system:
            return {"is_relevant": True}
        return {"category": "tool_framework", "summary": "高吞吐推理框架",
                "scores": {"practicality": 5, "influence": 5, "follow_cost": 4},
                "boundary": {"good_for": "推理", "not_good_for": "训练",
                             "risks": "兼容性"}}


def seed(repo):
    items = [
        TechItem(source="github", source_tier="T1.5", source_type="repo_index",
                 title="vLLM inference", url="https://github.com/vllm-project/vllm",
                 description="High-throughput LLM inference", published_at="2026-06-08",
                 metrics={"stars": 85000}, raw_id="github:vllm-project/vllm",
                 collected_at="2026-06-08T00:00:00"),
        TechItem(source="rss", source_tier="T1", source_type="official_blog",
                 title="vLLM inference released", url="https://media.com/vllm",
                 description="LLM inference news", published_at="2026-06-08",
                 metrics={}, raw_id="rss:https://media.com/vllm",
                 collected_at="2026-06-08T00:00:00"),
        TechItem(source="github", source_tier="T1.5", source_type="repo_index",
                 title="tiny repo", url="https://github.com/x/tiny",
                 description="not relevant", published_at="2026-06-08",
                 metrics={"stars": 10}, raw_id="github:x/tiny",
                 collected_at="2026-06-08T00:00:00"),
    ]
    for it in items:
        repo.upsert_item(it)


def test_full_pipeline_produces_report():
    repo = Repository(":memory:")
    repo.init_schema()
    seed(repo)
    cli.run_process(repo, settings())
    cli.run_analyze(repo, settings(), client=StubClient(), today="2026-06-08")
    md = cli.run_report(repo, week="2026-W23")

    assert "AI 技术情报周报 2026-W23" in md
    assert "vLLM inference" in md
    assert "建议跟进：1 项" in md
    assert "tiny repo" not in md

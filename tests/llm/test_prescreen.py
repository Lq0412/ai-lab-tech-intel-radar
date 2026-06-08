from radar.models import TechItem
from radar.llm.prescreen import prescreen


class StubClient:
    def __init__(self, value):
        self.value = value
        self.last_user = None

    def complete_json(self, system, user):
        self.last_user = user
        return {"is_relevant": self.value}


def item(title="vLLM", desc="LLM inference"):
    return TechItem(source="github", source_tier="T1.5", source_type="repo_index",
                    title=title, url="u", description=desc, published_at=None,
                    metrics={}, raw_id="r", collected_at="2026-06-08T00:00:00")


def test_prescreen_returns_true_for_relevant():
    client = StubClient(True)
    assert prescreen(item(), client) is True
    assert "vLLM" in client.last_user


def test_prescreen_returns_false_for_irrelevant():
    assert prescreen(item("Cooking blog", "recipes"), StubClient(False)) is False

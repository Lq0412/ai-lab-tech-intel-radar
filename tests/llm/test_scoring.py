from radar.models import TechItem
from radar.llm.scoring import score_item


class StubClient:
    def __init__(self, payload):
        self.payload = payload

    def complete_json(self, system, user):
        return self.payload


def item():
    return TechItem(source="github", source_tier="T1.5", source_type="repo_index",
                    title="vLLM", url="u", description="inference engine",
                    published_at=None, metrics={}, raw_id="r",
                    collected_at="2026-06-08T00:00:00")


def test_score_item_builds_analysis():
    payload = {
        "category": "tool_framework",
        "summary": "vLLM 是高吞吐推理框架。",
        "scores": {"practicality": 5, "influence": 5, "follow_cost": 4},
        "boundary": {"good_for": "在线推理", "not_good_for": "训练", "risks": "兼容性"},
    }
    a = score_item(item_id=7, item=item(), client=StubClient(payload))
    assert a.item_id == 7
    assert a.is_relevant is True
    assert a.category == "tool_framework"
    assert a.practicality == 5 and a.follow_cost == 4
    assert a.good_for == "在线推理"


def test_score_item_clamps_out_of_range_scores():
    payload = {"category": "model", "summary": "s",
               "scores": {"practicality": 9, "influence": 0, "follow_cost": 3},
               "boundary": {}}
    a = score_item(item_id=1, item=item(), client=StubClient(payload))
    assert a.practicality == 5
    assert a.influence == 1


def test_score_item_parses_novelty_and_highlight():
    payload = {
        "category": "tool_framework",
        "summary": "新发布的推理框架。",
        "highlight": "本周发布 v0.2，支持多卡并行",
        "scores": {"practicality": 4, "influence": 3, "follow_cost": 4,
                   "novelty": 5},
        "boundary": {"good_for": "推理", "not_good_for": "训练", "risks": "早期"},
    }
    a = score_item(item_id=3, item=item(), client=StubClient(payload))
    assert a.novelty == 5
    assert a.highlight == "本周发布 v0.2，支持多卡并行"

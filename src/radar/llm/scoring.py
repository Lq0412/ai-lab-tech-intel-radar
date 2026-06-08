from __future__ import annotations

from radar.llm.client import LLMClient
from radar.models import Analysis, TechItem

SYSTEM = (
    "你是 AI 技术情报分析助手。对给定条目输出结构化分析，只返回 JSON：\n"
    "{\n"
    '  "category": "model|tool_framework|paper|article|other",\n'
    '  "summary": "一句话中文摘要",\n'
    '  "scores": {"practicality": 1-5, "influence": 1-5, "follow_cost": 1-5},\n'
    '  "boundary": {"good_for": "", "not_good_for": "", "risks": ""}\n'
    "}\n"
    "practicality=能否在真实工程试用；influence=社区/厂商关注度；"
    "follow_cost=跟进成本，分越高表示成本越低。"
)


def _clamp(value: object) -> int:
    try:
        return max(1, min(5, int(value)))
    except (TypeError, ValueError):
        return 1


def score_item(item_id: int, item: TechItem, client: LLMClient) -> Analysis:
    user = (f"标题：{item.title}\n描述：{item.description}\n"
            f"来源：{item.source}（{item.source_tier}）\n指标：{item.metrics}")
    r = client.complete_json(SYSTEM, user)
    scores = r.get("scores", {})
    boundary = r.get("boundary", {})
    return Analysis(
        item_id=item_id,
        is_relevant=True,
        category=r.get("category", "other"),
        summary=r.get("summary", ""),
        practicality=_clamp(scores.get("practicality")),
        influence=_clamp(scores.get("influence")),
        follow_cost=_clamp(scores.get("follow_cost")),
        good_for=boundary.get("good_for", ""),
        not_good_for=boundary.get("not_good_for", ""),
        risks=boundary.get("risks", ""),
    )

from __future__ import annotations

from radar.llm.client import LLMClient
from radar.models import TechItem

SYSTEM = (
    "你是 AI 技术情报筛选助手。判断给定条目是否与 AI / 机器学习技术相关"
    "（模型、论文、开源工具、框架、技术路线等）。"
    "只返回 JSON：{\"is_relevant\": true 或 false}。"
)


def prescreen(item: TechItem, client: LLMClient) -> bool:
    user = f"标题：{item.title}\n描述：{item.description}\n来源：{item.source}"
    result = client.complete_json(SYSTEM, user)
    return bool(result.get("is_relevant", False))

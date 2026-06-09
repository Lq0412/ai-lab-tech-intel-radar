from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class TechItem:
    source: str
    source_tier: str
    source_type: str
    title: str
    url: str
    description: str
    published_at: str | None
    metrics: dict[str, Any]
    raw_id: str
    collected_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TechItem":
        return cls(**data)

    def to_row(self) -> dict[str, Any]:
        row = self.to_dict()
        row["metrics"] = json.dumps(self.metrics, ensure_ascii=False)
        return row


@dataclass
class Analysis:
    item_id: int
    is_relevant: bool
    category: str = ""
    summary: str = ""
    practicality: int = 0
    influence: int = 0
    follow_cost: int = 0
    good_for: str = ""
    not_good_for: str = ""
    risks: str = ""
    novelty: int = 0
    highlight: str = ""


@dataclass
class ScoredItem:
    item_id: int
    quality_score: float
    recommendation: str
    cluster_id: int | None = None
    related_urls: list[str] = field(default_factory=list)

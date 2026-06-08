from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Source:
    name: str
    url: str
    tier: str
    type: str
    kind: str  # "rss" | "github" | "huggingface"


@dataclass
class Settings:
    weights: dict[str, float]
    tier_weight: dict[str, int]
    thresholds: dict[str, float]
    github_min_stars: int
    github_min_weekly_growth: int
    keywords: list[str]
    title_similarity_threshold: float
    time_window_days: int
    max_recommendations: int = 8
    github_per_page: int = 50
    analyze_quota: dict[str, int] = field(
        default_factory=lambda: {"github": 20, "huggingface": 15, "rss": 15})

    def threshold_for(self, category: str) -> float:
        return self.thresholds.get(category, self.thresholds["default"])


@dataclass
class RuntimeConfig:
    openai_api_key: str = ""
    openai_base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-pro"
    github_token: str = ""
    db_path: str = "radar.db"


def load_sources(path: Path) -> list[Source]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [Source(**entry) for entry in data["sources"]]


def load_settings(path: Path) -> Settings:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    ranking = data["ranking"]
    flt = data["filter"]
    cluster = data["cluster"]
    analyze = data.get("analyze", {})
    return Settings(
        weights=ranking["weights"],
        tier_weight=ranking["tier_weight"],
        thresholds=ranking["thresholds"],
        github_min_stars=flt["github_min_stars"],
        github_min_weekly_growth=flt["github_min_weekly_growth"],
        keywords=[k.lower() for k in flt["keywords"]],
        title_similarity_threshold=cluster["title_similarity_threshold"],
        time_window_days=cluster["time_window_days"],
        max_recommendations=ranking.get("max_recommendations", 8),
        github_per_page=flt.get("github_per_page", 50),
        analyze_quota=analyze.get(
            "quota", {"github": 20, "huggingface": 15, "rss": 15}),
    )


def load_runtime() -> RuntimeConfig:
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    return RuntimeConfig(
        openai_api_key=api_key,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("RADAR_MODEL", "deepseek-v4-pro"),
        github_token=os.getenv("GITHUB_TOKEN", ""),
        db_path=os.getenv("RADAR_DB_PATH", "radar.db"),
    )

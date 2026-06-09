from __future__ import annotations

from typing import Any

import httpx

from radar.config import Source
from radar.models import TechItem

API = "https://huggingface.co/api/models"


def _parse_query(raw: str, sort: str = "") -> dict[str, str]:
    params: dict[str, str] = {
        "sort": sort or "trendingScore", "direction": "-1", "limit": "30",
    }
    if ":" in raw:
        key, value = raw.split(":", 1)
        params[key.strip()] = value.strip()
    elif raw.strip():
        params["search"] = raw.strip()
    return params


class HuggingFaceCollector:
    def __init__(self, client: Any | None = None):
        self.client = client or httpx.Client(timeout=20)

    def collect(self, source: Source, now: str) -> list[TechItem]:
        resp = self.client.get(API, params=_parse_query(source.url, source.sort),
                               headers={})
        resp.raise_for_status()
        items: list[TechItem] = []
        for model in resp.json():
            model_id = model["id"]
            items.append(TechItem(
                source="huggingface",
                source_tier=source.tier,
                source_type=source.type,
                title=model_id,
                url=f"https://huggingface.co/{model_id}",
                description=model.get("pipeline_tag") or "",
                published_at=(
                    (model.get("createdAt") or model.get("lastModified") or "")[:10]
                    or None
                ),
                metrics={
                    "downloads": model.get("downloads", 0),
                    "likes": model.get("likes", 0),
                    "trending": model.get("trendingScore", 0),
                },
                raw_id=f"huggingface:{model_id}",
                collected_at=now,
            ))
        return items

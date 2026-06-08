from __future__ import annotations

from typing import Any

import httpx

from radar.config import Source
from radar.models import TechItem

API = "https://api.github.com/search/repositories"


class GithubCollector:
    def __init__(self, client: Any | None = None, token: str = "",
                 per_page: int = 30):
        self.client = client or httpx.Client(timeout=20)
        self.token = token
        self.per_page = per_page

    def collect(self, source: Source, now: str) -> list[TechItem]:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        params = {"q": source.url, "sort": "stars",
                  "order": "desc", "per_page": self.per_page}
        resp = self.client.get(API, params=params, headers=headers)
        resp.raise_for_status()
        items: list[TechItem] = []
        for repo in resp.json().get("items", []):
            full_name = repo["full_name"]
            items.append(TechItem(
                source="github",
                source_tier=source.tier,
                source_type=source.type,
                title=full_name,
                url=repo["html_url"],
                description=repo.get("description") or "",
                published_at=(repo.get("pushed_at") or "")[:10] or None,
                metrics={
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language") or "",
                },
                raw_id=f"github:{full_name}",
                collected_at=now,
            ))
        return items

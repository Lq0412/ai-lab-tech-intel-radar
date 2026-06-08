from __future__ import annotations

from dataclasses import dataclass, field

from radar.models import TechItem
from radar.pipeline.dedup import same_event

TYPE_RANK = {
    "official_blog": 100,
    "official_doc": 95,
    "repo_index": 80,
    "release": 78,
    "official_social": 60,
    "model_index": 55,
    "media": 40,
    "article": 35,
    "kol": 20,
    "community": 10,
}
TIER_RANK = {"T1": 30, "T1.5": 20, "T2": 5}


def primary_priority(source_type: str, source_tier: str) -> int:
    return TYPE_RANK.get(source_type, 30) + TIER_RANK.get(source_tier, 5)


@dataclass
class Cluster:
    primary: TechItem
    members: list[TechItem] = field(default_factory=list)

    @property
    def related_urls(self) -> list[str]:
        return [m.url for m in self.members if m.raw_id != self.primary.raw_id]


def cluster_items(items: list[TechItem], threshold: float) -> list[Cluster]:
    clusters: list[Cluster] = []
    for it in items:
        placed = False
        for cluster in clusters:
            p = cluster.primary
            if same_event(it.url, p.url, it.title, p.title, threshold):
                cluster.members.append(it)
                if primary_priority(it.source_type, it.source_tier) > \
                        primary_priority(p.source_type, p.source_tier):
                    cluster.primary = it
                placed = True
                break
        if not placed:
            clusters.append(Cluster(primary=it, members=[it]))
    return clusters

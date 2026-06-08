from __future__ import annotations

from typing import Protocol

from radar.config import Source
from radar.models import TechItem


class Collector(Protocol):
    def collect(self, source: Source, now: str) -> list[TechItem]:
        ...

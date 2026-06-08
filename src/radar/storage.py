from __future__ import annotations

import json
import sqlite3
from typing import Any

from radar.models import Analysis, ScoredItem, TechItem

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_id TEXT UNIQUE NOT NULL,
    source TEXT, source_tier TEXT, source_type TEXT,
    title TEXT, url TEXT, description TEXT,
    published_at TEXT, metrics TEXT, collected_at TEXT,
    cluster_id INTEGER, is_duplicate INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS analyses (
    item_id INTEGER PRIMARY KEY REFERENCES items(id),
    is_relevant INTEGER, category TEXT, summary TEXT,
    practicality INTEGER, influence INTEGER, follow_cost INTEGER,
    good_for TEXT, not_good_for TEXT, risks TEXT,
    quality_score REAL, recommendation TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS reviews (
    item_id INTEGER PRIMARY KEY REFERENCES items(id),
    verdict TEXT, note TEXT, reviewed_at TEXT
);
"""


def _row_to_item(row: sqlite3.Row) -> TechItem:
    return TechItem(
        source=row["source"], source_tier=row["source_tier"],
        source_type=row["source_type"], title=row["title"], url=row["url"],
        description=row["description"], published_at=row["published_at"],
        metrics=json.loads(row["metrics"] or "{}"),
        raw_id=row["raw_id"], collected_at=row["collected_at"],
    )


class Repository:
    def __init__(self, db_path: str = "radar.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def init_schema(self) -> None:
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def upsert_item(self, item: TechItem) -> int:
        row = item.to_row()
        self.conn.execute(
            """
            INSERT INTO items (raw_id, source, source_tier, source_type, title,
                url, description, published_at, metrics, collected_at)
            VALUES (:raw_id, :source, :source_tier, :source_type, :title,
                :url, :description, :published_at, :metrics, :collected_at)
            ON CONFLICT(raw_id) DO UPDATE SET
                title=excluded.title, description=excluded.description,
                url=excluded.url, metrics=excluded.metrics,
                published_at=excluded.published_at,
                collected_at=excluded.collected_at
            """,
            row,
        )
        self.conn.commit()
        existing = self.conn.execute(
            "SELECT id FROM items WHERE raw_id=?", (item.raw_id,)
        ).fetchone()
        return existing["id"]

    def list_items(self, only_unique: bool = False) -> list[TechItem]:
        sql = "SELECT * FROM items"
        if only_unique:
            sql += " WHERE is_duplicate=0"
        sql += " ORDER BY id"
        return [_row_to_item(r) for r in self.conn.execute(sql)]

    def item_id_by_raw(self, raw_id: str) -> int | None:
        r = self.conn.execute(
            "SELECT id FROM items WHERE raw_id=?", (raw_id,)
        ).fetchone()
        return r["id"] if r else None

    def set_cluster(self, item_id: int, cluster_id: int, is_duplicate: bool) -> None:
        self.conn.execute(
            "UPDATE items SET cluster_id=?, is_duplicate=? WHERE id=?",
            (cluster_id, int(is_duplicate), item_id),
        )
        self.conn.commit()

    def save_analysis(self, a: Analysis, quality_score: float,
                      recommendation: str, created_at: str = "") -> None:
        self.conn.execute(
            """
            INSERT INTO analyses (item_id, is_relevant, category, summary,
                practicality, influence, follow_cost, good_for, not_good_for,
                risks, quality_score, recommendation, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(item_id) DO UPDATE SET
                is_relevant=excluded.is_relevant, category=excluded.category,
                summary=excluded.summary, practicality=excluded.practicality,
                influence=excluded.influence, follow_cost=excluded.follow_cost,
                good_for=excluded.good_for, not_good_for=excluded.not_good_for,
                risks=excluded.risks, quality_score=excluded.quality_score,
                recommendation=excluded.recommendation, created_at=excluded.created_at
            """,
            (a.item_id, int(a.is_relevant), a.category, a.summary,
             a.practicality, a.influence, a.follow_cost, a.good_for,
             a.not_good_for, a.risks, quality_score, recommendation, created_at),
        )
        self.conn.commit()

    def list_scored(self) -> list[ScoredItem]:
        rows = self.conn.execute(
            "SELECT item_id, quality_score, recommendation FROM analyses "
            "ORDER BY quality_score DESC"
        )
        return [
            ScoredItem(item_id=r["item_id"], quality_score=r["quality_score"],
                       recommendation=r["recommendation"])
            for r in rows
        ]

    def get_analysis_row(self, item_id: int) -> dict[str, Any] | None:
        r = self.conn.execute(
            "SELECT * FROM analyses WHERE item_id=?", (item_id,)
        ).fetchone()
        return dict(r) if r else None

    def save_review(self, item_id: int, verdict: str, note: str,
                    reviewed_at: str) -> None:
        self.conn.execute(
            "INSERT INTO reviews (item_id, verdict, note, reviewed_at) "
            "VALUES (?,?,?,?) ON CONFLICT(item_id) DO UPDATE SET "
            "verdict=excluded.verdict, note=excluded.note, "
            "reviewed_at=excluded.reviewed_at",
            (item_id, verdict, note, reviewed_at),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

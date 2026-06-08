# AI 技术情报雷达 MVP 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `docs/AI技术情报雷达-方案设计.md` 的设计落地成一个可运行的 Python CLI：采集 GitHub / Hugging Face / RSS 三类来源，归一化、去重聚类、LLM 两阶段分析、代码化评分，最终输出可人工审核的 Markdown 周报。

**Architecture:** 固定 Pipeline，非 Agent。数据流 `collect -> normalize -> dedup -> cluster -> filter -> llm prescreen -> llm scoring -> code ranking -> human review -> report`。每个阶段读写同一张 SQLite 数据库，CLI 子命令逐阶段可独立运行（便于调试与回测）。"能用代码处理的不交给模型"：去重、聚类、综合评分、阈值精选全部由代码完成，LLM 只负责相关性判断和维度评分。

**Tech Stack:** Python 3.11+、SQLite（标准库 `sqlite3`）、`httpx`（HTTP）、`feedparser`（RSS）、`PyYAML`（配置）、`openai` SDK（OpenAI 兼容，可配置 `base_url`/`model`）、`pytest`（测试）、`python-dotenv`（环境变量）。

**关键假设（实现前确认）：**
- LLM 走 OpenAI 兼容接口，通过环境变量 `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `RADAR_MODEL` 配置，便于切换自建或第三方网关。
- GitHub 走 REST Search API，需要 `GITHUB_TOKEN`（可选，无 token 时降级为低速率）。
- 所有 LLM 调用在测试中通过依赖注入 mock，不发真实请求；网络采集器同样通过注入 HTTP client 做测试。
- "人工审核"在 MVP 用 CLI 命令 + 数据库字段实现，不做 Web 界面。

---

## 文件结构

实现后目标结构（在仓库根目录新增 `src/` `tests/` `config/`，文档保持不变）：

```text
.
├── pyproject.toml                  # 项目元数据、依赖、pytest 配置
├── .env.example                    # 环境变量样例
├── config/
│   ├── sources.yaml                # 信源清单（name/url/tier/type/kind）
│   └── settings.yaml               # 阈值、权重、关键词等可调参数
├── src/radar/
│   ├── __init__.py
│   ├── models.py                   # TechItem / Analysis / ScoredItem 数据类
│   ├── config.py                   # 读取 settings.yaml / sources.yaml / 环境变量
│   ├── storage.py                  # SQLite 建表 + 仓储 (Repository)
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base.py                 # Collector 协议 + 注册
│   │   ├── github.py               # GitHub 采集
│   │   ├── huggingface.py          # Hugging Face 采集
│   │   └── rss.py                  # RSS 采集
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── dedup.py                # URL 去重 + 标题相似度合并
│   │   ├── cluster.py             # 事件聚类 + 主条目选择
│   │   └── filter.py               # 阈值 / 关键词过滤
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py               # LLM 调用封装（可注入）
│   │   ├── prescreen.py            # AI 相关性预筛
│   │   └── scoring.py              # 维度评分
│   ├── ranking.py                  # 代码化综合评分公式 + 精选阈值
│   ├── report.py                   # Markdown 周报生成
│   └── cli.py                      # 命令行入口（collect/analyze/rank/report/review）
└── tests/
    ├── conftest.py
    ├── test_models.py
    ├── test_config.py
    ├── test_storage.py
    ├── collectors/
    │   ├── test_github.py
    │   ├── test_huggingface.py
    │   └── test_rss.py
    ├── pipeline/
    │   ├── test_dedup.py
    │   ├── test_cluster.py
    │   └── test_filter.py
    ├── llm/
    │   ├── test_prescreen.py
    │   └── test_scoring.py
    ├── test_ranking.py
    ├── test_report.py
    └── test_cli.py
```

每个文件单一职责：采集器只负责"拉取并归一化为 `TechItem`"，pipeline 只做无网络的纯函数处理（最易测试），llm 模块隔离所有模型调用，ranking/report 是确定性纯函数。

---

## Task 0: 项目骨架与依赖

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `src/radar/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 创建 `pyproject.toml`**

```toml
[project]
name = "tech-intel-radar"
version = "0.1.0"
description = "AI 技术情报雷达 MVP"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "feedparser>=6.0",
    "PyYAML>=6.0",
    "openai>=1.40",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=5.0"]

[project.scripts]
radar = "radar.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 2: 创建 `.env.example`**

```bash
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
RADAR_MODEL=gpt-4o-mini
GITHUB_TOKEN=
RADAR_DB_PATH=radar.db
```

- [ ] **Step 3: 创建空包文件与测试夹具**

`src/radar/__init__.py`:

```python
__version__ = "0.1.0"
```

`tests/conftest.py`:

```python
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

- [ ] **Step 4: 安装依赖并验证 pytest 可运行**

Run: `pip install -e ".[dev]"`
Then: `pytest`
Expected: PASS（收集到 0 个测试，退出码 5 也可接受；确认 import 路径无误）

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example src/radar/__init__.py tests/conftest.py
git commit -m "chore: scaffold tech-intel-radar python project"
```

---

## Task 1: 数据模型 (`models.py`)

**Files:**
- Create: `src/radar/models.py`
- Test: `tests/test_models.py`

定义贯穿全流程的三个数据类。`TechItem` 是采集归一化后的统一结构；`Analysis` 是 LLM 分析结果；`ScoredItem` 是代码化评分后的结果。

- [ ] **Step 1: 写失败测试**

```python
from radar.models import TechItem, Analysis, ScoredItem


def test_techitem_roundtrips_through_dict():
    item = TechItem(
        source="github",
        source_tier="T1.5",
        source_type="repo_index",
        title="vLLM",
        url="https://github.com/vllm-project/vllm",
        description="High-throughput LLM inference engine",
        published_at="2026-06-01",
        metrics={"stars": 85000, "weekly_growth": 1200},
        raw_id="github:vllm-project/vllm",
        collected_at="2026-06-08T00:00:00",
    )
    restored = TechItem.from_dict(item.to_dict())
    assert restored == item
    assert restored.metrics["stars"] == 85000


def test_analysis_defaults_to_irrelevant():
    a = Analysis(item_id=1, is_relevant=False)
    assert a.category == ""
    assert a.practicality == 0


def test_scored_item_carries_recommendation():
    s = ScoredItem(item_id=1, quality_score=4.65, recommendation="建议跟进")
    assert s.recommendation == "建议跟进"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.models'`

- [ ] **Step 3: 实现 `models.py`**

```python
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


@dataclass
class ScoredItem:
    item_id: int
    quality_score: float
    recommendation: str
    cluster_id: int | None = None
    related_urls: list[str] = field(default_factory=list)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_models.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/models.py tests/test_models.py
git commit -m "feat: add core data models (TechItem/Analysis/ScoredItem)"
```

---

## Task 2: 配置加载 (`config.py`)

**Files:**
- Create: `config/sources.yaml`
- Create: `config/settings.yaml`
- Create: `src/radar/config.py`
- Test: `tests/test_config.py`

配置分两类：信源清单（`sources.yaml`，对应设计文档 Source Tier 模块）与可调参数（`settings.yaml`，对应评分权重/阈值/关键词）。

- [ ] **Step 1: 写 `config/sources.yaml`**

```yaml
sources:
  - name: OpenAI Blog
    url: https://openai.com/news/rss.xml
    tier: T1
    type: official_blog
    kind: rss
  - name: Hugging Face Blog
    url: https://huggingface.co/blog/feed.xml
    tier: T1
    type: official_blog
    kind: rss
  - name: GitHub Trending AI
    url: "topic:artificial-intelligence stars:>500"
    tier: T1.5
    type: repo_index
    kind: github
  - name: Hugging Face Models
    url: "pipeline_tag:text-generation"
    tier: T1.5
    type: model_index
    kind: huggingface
```

- [ ] **Step 2: 写 `config/settings.yaml`**

```yaml
ranking:
  weights:
    practicality: 0.35
    influence: 0.30
    follow_cost: 0.20
    source_tier: 0.10
    freshness: 0.05
  tier_weight:
    T1: 5
    T1.5: 4
    T2: 2
  thresholds:
    model: 3.5
    tool_framework: 3.8
    paper: 4.0
    article: 4.2
    default: 4.0

filter:
  github_min_stars: 500
  github_min_weekly_growth: 50
  keywords:
    - ai
    - llm
    - model
    - inference
    - agent
    - rag
    - transformer

cluster:
  title_similarity_threshold: 0.6
  time_window_days: 7
```

- [ ] **Step 3: 写失败测试**

```python
from pathlib import Path
from radar.config import load_settings, load_sources, Settings


def test_load_sources_parses_entries():
    sources = load_sources(Path("config/sources.yaml"))
    assert len(sources) >= 4
    gh = [s for s in sources if s.kind == "github"][0]
    assert gh.tier == "T1.5"
    assert gh.name == "GitHub Trending AI"


def test_load_settings_exposes_weights_and_thresholds():
    s: Settings = load_settings(Path("config/settings.yaml"))
    assert abs(sum(s.weights.values()) - 1.0) < 1e-6
    assert s.tier_weight["T1"] == 5
    assert s.threshold_for("model") == 3.5
    assert s.threshold_for("unknown_category") == s.thresholds["default"]
```

- [ ] **Step 4: 运行测试确认失败**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.config'`

- [ ] **Step 5: 实现 `config.py`**

```python
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

    def threshold_for(self, category: str) -> float:
        return self.thresholds.get(category, self.thresholds["default"])


@dataclass
class RuntimeConfig:
    openai_api_key: str = ""
    openai_base_url: str = ""
    model: str = "gpt-4o-mini"
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
    return Settings(
        weights=ranking["weights"],
        tier_weight=ranking["tier_weight"],
        thresholds=ranking["thresholds"],
        github_min_stars=flt["github_min_stars"],
        github_min_weekly_growth=flt["github_min_weekly_growth"],
        keywords=[k.lower() for k in flt["keywords"]],
        title_similarity_threshold=cluster["title_similarity_threshold"],
        time_window_days=cluster["time_window_days"],
    )


def load_runtime() -> RuntimeConfig:
    return RuntimeConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
        model=os.getenv("RADAR_MODEL", "gpt-4o-mini"),
        github_token=os.getenv("GITHUB_TOKEN", ""),
        db_path=os.getenv("RADAR_DB_PATH", "radar.db"),
    )
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_config.py -v`
Expected: PASS（2 passed）

- [ ] **Step 7: Commit**

```bash
git add config/sources.yaml config/settings.yaml src/radar/config.py tests/test_config.py
git commit -m "feat: add config loading for sources and tunable settings"
```

---

## Task 3: SQLite 存储 (`storage.py`)

**Files:**
- Create: `src/radar/storage.py`
- Test: `tests/test_storage.py`

仓储层负责建表与读写。三张表：`items`（采集条目 + 聚类/去重标记）、`analyses`（LLM 分析 + 综合分 + 推荐）、`reviews`（人工审核结论）。

- [ ] **Step 1: 写失败测试**

```python
from radar.models import TechItem, Analysis
from radar.storage import Repository


def make_item(raw_id="github:a/b", url="https://x/1", title="vLLM"):
    return TechItem(
        source="github", source_tier="T1.5", source_type="repo_index",
        title=title, url=url, description="d", published_at="2026-06-01",
        metrics={"stars": 1000}, raw_id=raw_id, collected_at="2026-06-08T00:00:00",
    )


def test_insert_and_fetch_item():
    repo = Repository(":memory:")
    repo.init_schema()
    item_id = repo.upsert_item(make_item())
    rows = repo.list_items()
    assert len(rows) == 1
    assert rows[0].metrics["stars"] == 1000
    assert item_id > 0


def test_upsert_is_idempotent_on_raw_id():
    repo = Repository(":memory:")
    repo.init_schema()
    first = repo.upsert_item(make_item(title="old"))
    second = repo.upsert_item(make_item(title="new"))
    assert first == second
    rows = repo.list_items()
    assert len(rows) == 1
    assert rows[0].title == "new"


def test_save_and_read_analysis():
    repo = Repository(":memory:")
    repo.init_schema()
    item_id = repo.upsert_item(make_item())
    repo.save_analysis(
        Analysis(item_id=item_id, is_relevant=True, category="tool_framework",
                 summary="s", practicality=5, influence=5, follow_cost=4),
        quality_score=4.65, recommendation="建议跟进",
    )
    scored = repo.list_scored()
    assert len(scored) == 1
    assert scored[0].quality_score == 4.65
    assert scored[0].recommendation == "建议跟进"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.storage'`

- [ ] **Step 3: 实现 `storage.py`**

```python
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
        cur = self.conn.execute(
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
        if cur.lastrowid:
            existing = self.conn.execute(
                "SELECT id FROM items WHERE raw_id=?", (item.raw_id,)
            ).fetchone()
            return existing["id"]
        return cur.lastrowid

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
```

> 实现说明：SQLite 的 `lastrowid` 在 `ON CONFLICT ... DO UPDATE`（更新已存在行）时不可靠，因此 `upsert_item` 始终通过 `raw_id` 回查真实 id，保证幂等返回稳定主键。

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_storage.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/storage.py tests/test_storage.py
git commit -m "feat: add sqlite repository for items/analyses/reviews"
```

---

## Task 4: 采集器协议与 GitHub 采集 (`collectors/base.py`, `collectors/github.py`)

**Files:**
- Create: `src/radar/collectors/__init__.py`
- Create: `src/radar/collectors/base.py`
- Create: `src/radar/collectors/github.py`
- Test: `tests/collectors/test_github.py`
- Create: `tests/collectors/__init__.py`（空文件）

采集器统一返回 `list[TechItem]`，HTTP client 通过参数注入以便测试。GitHub 用 Search Repositories API。

- [ ] **Step 1: 写失败测试**

```python
from radar.config import Source
from radar.collectors.github import GithubCollector


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.last_params = None

    def get(self, url, params=None, headers=None):
        self.last_params = params
        return FakeResponse(self._payload)


def test_github_collector_maps_to_techitem():
    payload = {"items": [{
        "full_name": "vllm-project/vllm",
        "html_url": "https://github.com/vllm-project/vllm",
        "description": "High-throughput LLM inference engine",
        "stargazers_count": 85000,
        "language": "Python",
        "pushed_at": "2026-06-01T10:00:00Z",
    }]}
    source = Source(name="GitHub Trending AI", url="topic:ai stars:>500",
                    tier="T1.5", type="repo_index", kind="github")
    collector = GithubCollector(client=FakeClient(payload), token="")
    items = collector.collect(source, now="2026-06-08T00:00:00")

    assert len(items) == 1
    it = items[0]
    assert it.source == "github"
    assert it.source_tier == "T1.5"
    assert it.raw_id == "github:vllm-project/vllm"
    assert it.metrics["stars"] == 85000
    assert it.metrics["language"] == "Python"
    assert it.title == "vllm-project/vllm"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/collectors/test_github.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.collectors'`

- [ ] **Step 3: 实现 `collectors/__init__.py` 与 `collectors/base.py`**

`src/radar/collectors/__init__.py`:

```python
```

（保持空文件即可）

`src/radar/collectors/base.py`:

```python
from __future__ import annotations

from typing import Protocol

from radar.config import Source
from radar.models import TechItem


class Collector(Protocol):
    def collect(self, source: Source, now: str) -> list[TechItem]:
        ...
```

- [ ] **Step 4: 实现 `collectors/github.py`**

```python
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
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/collectors/test_github.py -v`
Expected: PASS（1 passed）

- [ ] **Step 6: Commit**

```bash
git add src/radar/collectors/__init__.py src/radar/collectors/base.py src/radar/collectors/github.py tests/collectors/__init__.py tests/collectors/test_github.py
git commit -m "feat: add collector protocol and github collector"
```

---

## Task 5: Hugging Face 采集 (`collectors/huggingface.py`)

**Files:**
- Create: `src/radar/collectors/huggingface.py`
- Test: `tests/collectors/test_huggingface.py`

用 Hugging Face Models 列表 API（`https://huggingface.co/api/models`），按 `source.url` 作为查询参数过滤。

- [ ] **Step 1: 写失败测试**

```python
from radar.config import Source
from radar.collectors.huggingface import HuggingFaceCollector


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, payload):
        self._payload = payload

    def get(self, url, params=None, headers=None):
        return FakeResponse(self._payload)


def test_huggingface_collector_maps_to_techitem():
    payload = [{
        "id": "meta-llama/Llama-3-8B",
        "pipeline_tag": "text-generation",
        "downloads": 1200000,
        "likes": 3400,
        "lastModified": "2026-05-30T00:00:00.000Z",
    }]
    source = Source(name="HF Models", url="pipeline_tag:text-generation",
                    tier="T1.5", type="model_index", kind="huggingface")
    items = HuggingFaceCollector(client=FakeClient(payload)).collect(
        source, now="2026-06-08T00:00:00")

    assert len(items) == 1
    it = items[0]
    assert it.source == "huggingface"
    assert it.raw_id == "huggingface:meta-llama/Llama-3-8B"
    assert it.url == "https://huggingface.co/meta-llama/Llama-3-8B"
    assert it.metrics["downloads"] == 1200000
    assert it.metrics["likes"] == 3400
    assert it.published_at == "2026-05-30"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/collectors/test_huggingface.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.collectors.huggingface'`

- [ ] **Step 3: 实现 `collectors/huggingface.py`**

```python
from __future__ import annotations

from typing import Any

import httpx

from radar.config import Source
from radar.models import TechItem

API = "https://huggingface.co/api/models"


def _parse_query(raw: str) -> dict[str, str]:
    params: dict[str, str] = {"sort": "downloads", "direction": "-1", "limit": "30"}
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
        resp = self.client.get(API, params=_parse_query(source.url), headers={})
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
                published_at=(model.get("lastModified") or "")[:10] or None,
                metrics={
                    "downloads": model.get("downloads", 0),
                    "likes": model.get("likes", 0),
                },
                raw_id=f"huggingface:{model_id}",
                collected_at=now,
            ))
        return items
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/collectors/test_huggingface.py -v`
Expected: PASS（1 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/collectors/huggingface.py tests/collectors/test_huggingface.py
git commit -m "feat: add huggingface models collector"
```

---

## Task 6: RSS 采集 (`collectors/rss.py`)

**Files:**
- Create: `src/radar/collectors/rss.py`
- Test: `tests/collectors/test_rss.py`

用 `feedparser` 解析。为便于测试，构造器接收一个 `parse_fn`（默认 `feedparser.parse`），测试时传入返回固定结构的假函数。

- [ ] **Step 1: 写失败测试**

```python
from types import SimpleNamespace
from radar.config import Source
from radar.collectors.rss import RssCollector


def fake_parse(url):
    entry = SimpleNamespace(
        title="GPT-5 released",
        link="https://openai.com/news/gpt-5",
        summary="A new frontier model.",
        published="Mon, 01 Jun 2026 10:00:00 GMT",
    )
    return SimpleNamespace(entries=[entry])


def test_rss_collector_maps_to_techitem():
    source = Source(name="OpenAI Blog", url="https://openai.com/news/rss.xml",
                    tier="T1", type="official_blog", kind="rss")
    items = RssCollector(parse_fn=fake_parse).collect(source, now="2026-06-08T00:00:00")

    assert len(items) == 1
    it = items[0]
    assert it.source == "rss"
    assert it.source_tier == "T1"
    assert it.title == "GPT-5 released"
    assert it.url == "https://openai.com/news/gpt-5"
    assert it.raw_id == "rss:https://openai.com/news/gpt-5"
    assert it.published_at == "2026-06-01"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/collectors/test_rss.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.collectors.rss'`

- [ ] **Step 3: 实现 `collectors/rss.py`**

```python
from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Callable

import feedparser

from radar.config import Source
from radar.models import TechItem


def _to_iso_date(published: str | None) -> str | None:
    if not published:
        return None
    try:
        return parsedate_to_datetime(published).date().isoformat()
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(published).date().isoformat()
        except ValueError:
            return None


class RssCollector:
    def __init__(self, parse_fn: Callable[[str], object] | None = None):
        self.parse_fn = parse_fn or feedparser.parse

    def collect(self, source: Source, now: str) -> list[TechItem]:
        feed = self.parse_fn(source.url)
        items: list[TechItem] = []
        for entry in getattr(feed, "entries", []):
            link = getattr(entry, "link", "")
            if not link:
                continue
            items.append(TechItem(
                source="rss",
                source_tier=source.tier,
                source_type=source.type,
                title=getattr(entry, "title", ""),
                url=link,
                description=getattr(entry, "summary", ""),
                published_at=_to_iso_date(getattr(entry, "published", None)),
                metrics={},
                raw_id=f"rss:{link}",
                collected_at=now,
            ))
        return items
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/collectors/test_rss.py -v`
Expected: PASS（1 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/collectors/rss.py tests/collectors/test_rss.py
git commit -m "feat: add rss collector"
```

---

## Task 7: 去重 (`pipeline/dedup.py`)

**Files:**
- Create: `src/radar/pipeline/__init__.py`（空文件）
- Create: `src/radar/pipeline/dedup.py`
- Test: `tests/pipeline/__init__.py`（空文件）
- Test: `tests/pipeline/test_dedup.py`

纯函数：输入 `list[TechItem]`，返回标记好重复关系的分组。规则：URL 完全相同视为同一条；标题相似度高（`difflib.SequenceMatcher`）且来源不同则合并。这里只做"两两相似"判定函数，聚类在 Task 8 完成。

- [ ] **Step 1: 写失败测试**

```python
from radar.pipeline.dedup import normalize_url, title_similarity, same_event


def test_normalize_url_strips_query_and_trailing_slash():
    assert normalize_url("https://X.com/a/?utm=1") == "https://x.com/a"
    assert normalize_url("https://x.com/a") == "https://x.com/a"


def test_title_similarity_high_for_near_duplicates():
    s = title_similarity("vLLM v0.5 released", "vLLM v0.5 is released")
    assert s > 0.6


def test_same_event_true_when_urls_match_after_normalize():
    assert same_event("https://x.com/a?ref=1", "https://x.com/a/", "t1", "t2",
                      threshold=0.6) is True


def test_same_event_true_when_titles_similar():
    assert same_event("https://a.com/x", "https://b.com/y",
                      "GPT-5 released today", "GPT-5 is released today",
                      threshold=0.6) is True


def test_same_event_false_when_unrelated():
    assert same_event("https://a.com/x", "https://b.com/y",
                      "vLLM update", "New dataset for vision",
                      threshold=0.6) is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/pipeline/test_dedup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.pipeline'`

- [ ] **Step 3: 实现 `pipeline/__init__.py` 和 `pipeline/dedup.py`**

`src/radar/pipeline/__init__.py`: 空文件。

`src/radar/pipeline/dedup.py`:

```python
from __future__ import annotations

from difflib import SequenceMatcher
from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip().lower())
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def same_event(url_a: str, url_b: str, title_a: str, title_b: str,
               threshold: float) -> bool:
    if normalize_url(url_a) == normalize_url(url_b):
        return True
    return title_similarity(title_a, title_b) >= threshold
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/pipeline/test_dedup.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/pipeline/__init__.py src/radar/pipeline/dedup.py tests/pipeline/__init__.py tests/pipeline/test_dedup.py
git commit -m "feat: add url normalization and event similarity helpers"
```

---

## Task 8: 事件聚类与主条目选择 (`pipeline/cluster.py`)

**Files:**
- Create: `src/radar/pipeline/cluster.py`
- Test: `tests/pipeline/test_cluster.py`

把"同一事件的多源报道"聚成簇，每簇选一个主条目（信源等级优先），其余标记为重复。优先级：`官方博客/文档 > 项目仓库/Release > 官方社媒 > 权威媒体 > KOL/社区`，MVP 用 `source_type` + `source_tier` 映射为优先级分值。

- [ ] **Step 1: 写失败测试**

```python
from radar.models import TechItem
from radar.pipeline.cluster import cluster_items, primary_priority


def item(raw_id, title, url, tier, stype):
    return TechItem(source="x", source_tier=tier, source_type=stype,
                    title=title, url=url, description="", published_at="2026-06-01",
                    metrics={}, raw_id=raw_id, collected_at="2026-06-08T00:00:00")


def test_primary_priority_prefers_official_blog():
    assert primary_priority("official_blog", "T1") > primary_priority("article", "T2")


def test_cluster_groups_similar_titles_and_picks_official_primary():
    items = [
        item("a", "GPT-5 released today", "https://media.com/x", "T2", "article"),
        item("b", "GPT-5 is released today", "https://openai.com/g5", "T1", "official_blog"),
    ]
    clusters = cluster_items(items, threshold=0.6)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.primary.raw_id == "b"
    assert [m.raw_id for m in cluster.members] == ["a"] or [m.raw_id for m in cluster.members] == ["a", "b"]
    assert cluster.related_urls == ["https://media.com/x"]


def test_cluster_keeps_distinct_events_separate():
    items = [
        item("a", "vLLM new release", "https://github.com/vllm", "T1.5", "repo_index"),
        item("b", "New vision dataset", "https://hf.co/ds", "T1.5", "model_index"),
    ]
    clusters = cluster_items(items, threshold=0.6)
    assert len(clusters) == 2
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/pipeline/test_cluster.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.pipeline.cluster'`

- [ ] **Step 3: 实现 `pipeline/cluster.py`**

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/pipeline/test_cluster.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/pipeline/cluster.py tests/pipeline/test_cluster.py
git commit -m "feat: add event clustering with priority-based primary selection"
```

---

## Task 9: 过滤 (`pipeline/filter.py`)

**Files:**
- Create: `src/radar/pipeline/filter.py`
- Test: `tests/pipeline/test_filter.py`

代码化降噪：GitHub 低于 star 阈值过滤；RSS 标题/摘要不含关键词过滤；HF 全部保留（已由查询约束）。返回 `(kept, dropped)`。

- [ ] **Step 1: 写失败测试**

```python
from radar.models import TechItem
from radar.config import Settings
from radar.pipeline.filter import apply_filters


def settings():
    return Settings(weights={}, tier_weight={}, thresholds={"default": 4.0},
                    github_min_stars=500, github_min_weekly_growth=50,
                    keywords=["llm", "model"], title_similarity_threshold=0.6,
                    time_window_days=7)


def gh(stars, raw="github:a/b"):
    return TechItem(source="github", source_tier="T1.5", source_type="repo_index",
                    title="repo", url="u", description="", published_at=None,
                    metrics={"stars": stars}, raw_id=raw,
                    collected_at="2026-06-08T00:00:00")


def rss(title, desc, raw="rss:u"):
    return TechItem(source="rss", source_tier="T1", source_type="official_blog",
                    title=title, url="u", description=desc, published_at=None,
                    metrics={}, raw_id=raw, collected_at="2026-06-08T00:00:00")


def test_github_below_star_threshold_is_dropped():
    kept, dropped = apply_filters([gh(100)], settings())
    assert kept == [] and len(dropped) == 1


def test_github_above_threshold_is_kept():
    kept, _ = apply_filters([gh(900)], settings())
    assert len(kept) == 1


def test_rss_without_keyword_is_dropped():
    kept, dropped = apply_filters([rss("Cooking recipe", "no tech here")], settings())
    assert kept == [] and len(dropped) == 1


def test_rss_with_keyword_is_kept():
    kept, _ = apply_filters([rss("New LLM released", "great model")], settings())
    assert len(kept) == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/pipeline/test_filter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.pipeline.filter'`

- [ ] **Step 3: 实现 `pipeline/filter.py`**

```python
from __future__ import annotations

from radar.config import Settings
from radar.models import TechItem


def _keeps(item: TechItem, settings: Settings) -> bool:
    if item.source == "github":
        return item.metrics.get("stars", 0) >= settings.github_min_stars
    if item.source == "rss":
        text = f"{item.title} {item.description}".lower()
        return any(kw in text for kw in settings.keywords)
    return True


def apply_filters(items: list[TechItem],
                  settings: Settings) -> tuple[list[TechItem], list[TechItem]]:
    kept, dropped = [], []
    for it in items:
        (kept if _keeps(it, settings) else dropped).append(it)
    return kept, dropped
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/pipeline/test_filter.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/pipeline/filter.py tests/pipeline/test_filter.py
git commit -m "feat: add rule-based noise filtering"
```

---

## Task 10: LLM 客户端封装 (`llm/client.py`)

**Files:**
- Create: `src/radar/llm/__init__.py`（空文件）
- Create: `src/radar/llm/client.py`
- Test: `tests/llm/__init__.py`（空文件）
- Test: `tests/llm/test_client.py`

封装 OpenAI 兼容调用，只暴露 `complete_json(system, user) -> dict`。底层 SDK 通过构造器注入，测试用假对象。

- [ ] **Step 1: 写失败测试**

```python
import json
from radar.llm.client import LLMClient


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return type("Resp", (), {"choices": [FakeChoice(self._content)]})()


class FakeChat:
    def __init__(self, content):
        self.completions = FakeCompletions(content)


class FakeSDK:
    def __init__(self, content):
        self.chat = FakeChat(content)


def test_complete_json_parses_model_output():
    sdk = FakeSDK(json.dumps({"category": "tool_framework", "score": 5}))
    client = LLMClient(sdk=sdk, model="test-model")
    result = client.complete_json("sys", "user")
    assert result["category"] == "tool_framework"
    assert sdk.chat.completions.last_kwargs["model"] == "test-model"


def test_complete_json_strips_code_fences():
    sdk = FakeSDK("```json\n{\"ok\": true}\n```")
    client = LLMClient(sdk=sdk, model="m")
    assert client.complete_json("s", "u") == {"ok": True}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/llm/test_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.llm'`

- [ ] **Step 3: 实现 `llm/__init__.py` 和 `llm/client.py`**

`src/radar/llm/__init__.py`: 空文件。

`src/radar/llm/client.py`:

```python
from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    return _FENCE.sub("", text).strip()


class LLMClient:
    def __init__(self, sdk: Any | None = None, model: str = "gpt-4o-mini",
                 api_key: str = "", base_url: str = ""):
        if sdk is None:
            from openai import OpenAI
            kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            sdk = OpenAI(**kwargs)
        self.sdk = sdk
        self.model = model

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        resp = self.sdk.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(_strip_fences(content))
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/llm/test_client.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/llm/__init__.py src/radar/llm/client.py tests/llm/__init__.py tests/llm/test_client.py
git commit -m "feat: add injectable openai-compatible llm client"
```

---

## Task 11: AI 相关性预筛 (`llm/prescreen.py`)

**Files:**
- Create: `src/radar/llm/prescreen.py`
- Test: `tests/llm/test_prescreen.py`

低成本预筛：判断条目是否与 AI 技术相关。返回 `bool`。LLM 客户端注入（用假 client）。

- [ ] **Step 1: 写失败测试**

```python
from radar.models import TechItem
from radar.llm.prescreen import prescreen


class StubClient:
    def __init__(self, value):
        self.value = value
        self.last_user = None

    def complete_json(self, system, user):
        self.last_user = user
        return {"is_relevant": self.value}


def item(title="vLLM", desc="LLM inference"):
    return TechItem(source="github", source_tier="T1.5", source_type="repo_index",
                    title=title, url="u", description=desc, published_at=None,
                    metrics={}, raw_id="r", collected_at="2026-06-08T00:00:00")


def test_prescreen_returns_true_for_relevant():
    client = StubClient(True)
    assert prescreen(item(), client) is True
    assert "vLLM" in client.last_user


def test_prescreen_returns_false_for_irrelevant():
    assert prescreen(item("Cooking blog", "recipes"), StubClient(False)) is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/llm/test_prescreen.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.llm.prescreen'`

- [ ] **Step 3: 实现 `llm/prescreen.py`**

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/llm/test_prescreen.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/llm/prescreen.py tests/llm/test_prescreen.py
git commit -m "feat: add llm ai-relevance prescreen"
```

---

## Task 12: 维度评分 (`llm/scoring.py`)

**Files:**
- Create: `src/radar/llm/scoring.py`
- Test: `tests/llm/test_scoring.py`

对通过预筛的条目做分类、摘要、维度评分（实用性/影响力/跟进成本，各 1-5）、能力边界（good_for/not_good_for/risks），返回 `Analysis`。分数做 1-5 边界裁剪。

- [ ] **Step 1: 写失败测试**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/llm/test_scoring.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.llm.scoring'`

- [ ] **Step 3: 实现 `llm/scoring.py`**

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/llm/test_scoring.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/llm/scoring.py tests/llm/test_scoring.py
git commit -m "feat: add llm dimension scoring"
```

---

## Task 13: 代码化综合评分 (`ranking.py`)

**Files:**
- Create: `src/radar/ranking.py`
- Test: `tests/test_ranking.py`

确定性公式：`quality_score = 0.35*practicality + 0.30*influence + 0.20*follow_cost + 0.10*tier_weight + 0.05*freshness`，各项归一到 1-5 量纲。再按类别阈值给出推荐结论。

- [ ] **Step 1: 写失败测试**

```python
from radar.models import Analysis
from radar.config import Settings
from radar.ranking import freshness_score, compute_quality, recommend


def settings():
    return Settings(
        weights={"practicality": 0.35, "influence": 0.30, "follow_cost": 0.20,
                 "source_tier": 0.10, "freshness": 0.05},
        tier_weight={"T1": 5, "T1.5": 4, "T2": 2},
        thresholds={"tool_framework": 3.8, "default": 4.0},
        github_min_stars=500, github_min_weekly_growth=50, keywords=[],
        title_similarity_threshold=0.6, time_window_days=7)


def test_freshness_full_for_today():
    assert freshness_score("2026-06-08", today="2026-06-08") == 5
    assert freshness_score(None, today="2026-06-08") == 3


def test_freshness_decays_with_age():
    assert freshness_score("2026-05-01", today="2026-06-08") < 5


def test_compute_quality_matches_formula():
    a = Analysis(item_id=1, is_relevant=True, practicality=5, influence=5,
                 follow_cost=4)
    score = compute_quality(a, source_tier="T1.5", published_at="2026-06-08",
                            settings=settings(), today="2026-06-08")
    # 0.35*5 + 0.30*5 + 0.20*4 + 0.10*4 + 0.05*5 = 4.7
    assert abs(score - 4.7) < 1e-6


def test_recommend_uses_category_threshold():
    s = settings()
    assert recommend(4.0, "tool_framework", s) == "建议跟进"   # >=3.8
    assert recommend(3.0, "tool_framework", s) == "保持观察"   # >=3.8-1.0
    assert recommend(2.0, "tool_framework", s) == "暂不投入"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_ranking.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.ranking'`

- [ ] **Step 3: 实现 `ranking.py`**

```python
from __future__ import annotations

from datetime import date

from radar.config import Settings
from radar.models import Analysis


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def freshness_score(published_at: str | None, today: str) -> int:
    d = _parse_date(published_at)
    if d is None:
        return 3
    age = (_parse_date(today) - d).days
    if age <= 1:
        return 5
    if age <= 7:
        return 4
    if age <= 30:
        return 3
    if age <= 90:
        return 2
    return 1


def compute_quality(analysis: Analysis, source_tier: str,
                    published_at: str | None, settings: Settings,
                    today: str) -> float:
    w = settings.weights
    tier_w = settings.tier_weight.get(source_tier, 2)
    fresh = freshness_score(published_at, today)
    score = (
        w["practicality"] * analysis.practicality
        + w["influence"] * analysis.influence
        + w["follow_cost"] * analysis.follow_cost
        + w["source_tier"] * tier_w
        + w["freshness"] * fresh
    )
    return round(score, 2)


def recommend(quality_score: float, category: str, settings: Settings) -> str:
    threshold = settings.threshold_for(category)
    if quality_score >= threshold:
        return "建议跟进"
    if quality_score >= threshold - 1.0:
        return "保持观察"
    return "暂不投入"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_ranking.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/ranking.py tests/test_ranking.py
git commit -m "feat: add code-based quality scoring and recommendation"
```

---

## Task 14: Markdown 周报生成 (`report.py`)

**Files:**
- Create: `src/radar/report.py`
- Test: `tests/test_report.py`

把已评分 + 已聚类的条目渲染成设计文档里的周报格式：本周结论统计 + Top 推荐（含主条目、信源等级、相关报道、综合分、能力边界）+ 观察列表。纯函数，输入数据结构，输出字符串。

- [ ] **Step 1: 写失败测试**

```python
from radar.report import ReportRow, render_report


def row(title, rec, score=4.65, related=None):
    return ReportRow(
        title=title, recommendation=rec, quality_score=score,
        category="tool_framework", source_tier="T1.5",
        summary="高吞吐推理框架", good_for="在线推理", not_good_for="训练",
        risks="兼容性", url="https://github.com/vllm-project/vllm",
        related_urls=related or [],
    )


def test_render_report_includes_week_and_counts():
    rows = [row("vLLM 更新", "建议跟进"),
            row("某模型", "保持观察", score=3.2),
            row("某文章", "暂不投入", score=2.0)]
    md = render_report(rows, week="2026-W23")
    assert "# AI 技术情报周报 2026-W23" in md
    assert "建议跟进：1 项" in md
    assert "保持观察：1 项" in md
    assert "暂不投入：1 项" in md


def test_render_report_lists_top_recommendations_with_details():
    rows = [row("vLLM 更新", "建议跟进", related=["https://media.com/a"])]
    md = render_report(rows, week="2026-W23")
    assert "vLLM 更新" in md
    assert "综合分：4.65" in md
    assert "信源等级：T1.5" in md
    assert "相关报道：1 条" in md
    assert "在线推理" in md


def test_render_report_handles_empty():
    md = render_report([], week="2026-W23")
    assert "本周无可推荐条目" in md
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.report'`

- [ ] **Step 3: 实现 `report.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReportRow:
    title: str
    recommendation: str
    quality_score: float
    category: str
    source_tier: str
    summary: str
    good_for: str
    not_good_for: str
    risks: str
    url: str
    related_urls: list[str] = field(default_factory=list)


def render_report(rows: list[ReportRow], week: str) -> str:
    follow = [r for r in rows if r.recommendation == "建议跟进"]
    watch = [r for r in rows if r.recommendation == "保持观察"]
    skip = [r for r in rows if r.recommendation == "暂不投入"]

    lines = [f"# AI 技术情报周报 {week}", "", "## 本周结论", "",
             f"- 建议跟进：{len(follow)} 项",
             f"- 保持观察：{len(watch)} 项",
             f"- 暂不投入：{len(skip)} 项", ""]

    lines.append("## Top 推荐")
    lines.append("")
    top = sorted(follow, key=lambda r: r.quality_score, reverse=True)
    if not top:
        lines.append("本周无可推荐条目。")
        lines.append("")
    else:
        for i, r in enumerate(top, 1):
            lines += [
                f"### {i}. {r.title}", "",
                f"- 事件主条目：{r.url}",
                f"- 信源等级：{r.source_tier}",
                f"- 相关报道：{len(r.related_urls)} 条，已折叠",
                f"- 分类：{r.category}",
                f"- 综合建议：{r.recommendation}",
                f"- 综合分：{r.quality_score}/5",
                f"- 摘要：{r.summary}",
                f"- 能力边界：适合 {r.good_for}；不适合 {r.not_good_for}；"
                f"风险 {r.risks}", "",
            ]

    if watch:
        lines += ["## 观察列表", ""]
        for r in sorted(watch, key=lambda x: x.quality_score, reverse=True):
            lines.append(f"- {r.title}（{r.quality_score}/5）- {r.summary}")
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_report.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/report.py tests/test_report.py
git commit -m "feat: add markdown weekly report renderer"
```

---

## Task 15: CLI 编排 (`cli.py`)

**Files:**
- Create: `src/radar/cli.py`
- Test: `tests/test_cli.py`

把各阶段串成子命令：`collect`（采集入库）、`process`（去重+聚类+过滤+标记）、`analyze`（LLM 预筛+评分+代码评分入库）、`report`（生成周报）、`review`（人工标注）。用 `argparse`。`analyze` 接受可注入的 `client_factory`，便于测试。这里给出可测试的核心编排函数 + 薄 `main`。

- [ ] **Step 1: 写失败测试**

```python
from radar.models import TechItem
from radar.config import Settings
from radar.storage import Repository
from radar import cli


def settings():
    return Settings(
        weights={"practicality": 0.35, "influence": 0.30, "follow_cost": 0.20,
                 "source_tier": 0.10, "freshness": 0.05},
        tier_weight={"T1": 5, "T1.5": 4, "T2": 2},
        thresholds={"tool_framework": 3.8, "default": 4.0},
        github_min_stars=500, github_min_weekly_growth=50,
        keywords=["llm", "model", "inference"],
        title_similarity_threshold=0.6, time_window_days=7)


class StubClient:
    def complete_json(self, system, user):
        if "is_relevant" in system:
            return {"is_relevant": True}
        return {"category": "tool_framework", "summary": "高吞吐推理框架",
                "scores": {"practicality": 5, "influence": 5, "follow_cost": 4},
                "boundary": {"good_for": "推理", "not_good_for": "训练",
                             "risks": "兼容性"}}


def make_repo_with_item():
    repo = Repository(":memory:")
    repo.init_schema()
    repo.upsert_item(TechItem(
        source="github", source_tier="T1.5", source_type="repo_index",
        title="vLLM inference", url="https://github.com/vllm-project/vllm",
        description="High-throughput LLM inference", published_at="2026-06-08",
        metrics={"stars": 85000}, raw_id="github:vllm-project/vllm",
        collected_at="2026-06-08T00:00:00"))
    return repo


def test_run_process_marks_clusters():
    repo = make_repo_with_item()
    kept = cli.run_process(repo, settings())
    assert kept == 1
    assert len(repo.list_items(only_unique=True)) == 1


def test_run_analyze_scores_items():
    repo = make_repo_with_item()
    cli.run_process(repo, settings())
    cli.run_analyze(repo, settings(), client=StubClient(), today="2026-06-08")
    scored = repo.list_scored()
    assert len(scored) == 1
    assert scored[0].recommendation == "建议跟进"


def test_run_report_renders_markdown():
    repo = make_repo_with_item()
    cli.run_process(repo, settings())
    cli.run_analyze(repo, settings(), client=StubClient(), today="2026-06-08")
    md = cli.run_report(repo, week="2026-W23")
    assert "AI 技术情报周报 2026-W23" in md
    assert "vLLM inference" in md
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `AttributeError: module 'radar.cli' has no attribute 'run_process'`（或 ModuleNotFound）

- [ ] **Step 3: 实现 `cli.py`**

```python
from __future__ import annotations

import argparse
from datetime import date, datetime

from dotenv import load_dotenv

from radar.collectors.github import GithubCollector
from radar.collectors.huggingface import HuggingFaceCollector
from radar.collectors.rss import RssCollector
from radar.config import (RuntimeConfig, Settings, load_runtime, load_settings,
                          load_sources)
from radar.llm.client import LLMClient
from radar.llm.prescreen import prescreen
from radar.llm.scoring import score_item
from radar.models import Analysis
from radar.pipeline.cluster import cluster_items
from radar.pipeline.filter import apply_filters
from radar.ranking import compute_quality, recommend
from radar.report import ReportRow, render_report
from radar.storage import Repository

from pathlib import Path

CONFIG_DIR = Path("config")


def run_collect(repo: Repository, settings: Settings, runtime: RuntimeConfig,
                now: str) -> int:
    sources = load_sources(CONFIG_DIR / "sources.yaml")
    collectors = {
        "github": GithubCollector(token=runtime.github_token),
        "huggingface": HuggingFaceCollector(),
        "rss": RssCollector(),
    }
    count = 0
    for source in sources:
        collector = collectors.get(source.kind)
        if collector is None:
            continue
        for item in collector.collect(source, now=now):
            repo.upsert_item(item)
            count += 1
    return count


def run_process(repo: Repository, settings: Settings) -> int:
    items = repo.list_items()
    kept, dropped = apply_filters(items, settings)
    for it in dropped:
        item_id = repo.item_id_by_raw(it.raw_id)
        if item_id:
            repo.set_cluster(item_id, cluster_id=-1, is_duplicate=True)
    clusters = cluster_items(kept, threshold=settings.title_similarity_threshold)
    kept_count = 0
    for cid, cluster in enumerate(clusters):
        for member in cluster.members:
            item_id = repo.item_id_by_raw(member.raw_id)
            if item_id is None:
                continue
            is_dup = member.raw_id != cluster.primary.raw_id
            repo.set_cluster(item_id, cluster_id=cid, is_duplicate=is_dup)
        kept_count += 1
    return kept_count


def run_analyze(repo: Repository, settings: Settings, client: LLMClient,
                today: str) -> int:
    primaries = repo.list_items(only_unique=True)
    analyzed = 0
    for item in primaries:
        item_id = repo.item_id_by_raw(item.raw_id)
        if item_id is None:
            continue
        if not prescreen(item, client):
            repo.save_analysis(Analysis(item_id=item_id, is_relevant=False),
                               quality_score=0.0, recommendation="暂不投入",
                               created_at=today)
            continue
        analysis = score_item(item_id, item, client)
        quality = compute_quality(analysis, item.source_tier, item.published_at,
                                  settings, today)
        rec = recommend(quality, analysis.category, settings)
        repo.save_analysis(analysis, quality_score=quality, recommendation=rec,
                           created_at=today)
        analyzed += 1
    return analyzed


def run_report(repo: Repository, week: str) -> str:
    rows: list[ReportRow] = []
    for item in repo.list_items(only_unique=True):
        item_id = repo.item_id_by_raw(item.raw_id)
        a = repo.get_analysis_row(item_id) if item_id else None
        if not a or not a["is_relevant"]:
            continue
        rows.append(ReportRow(
            title=item.title, recommendation=a["recommendation"],
            quality_score=a["quality_score"], category=a["category"],
            source_tier=item.source_tier, summary=a["summary"],
            good_for=a["good_for"], not_good_for=a["not_good_for"],
            risks=a["risks"], url=item.url, related_urls=[]))
    return render_report(rows, week=week)


def _iso_week(today: str) -> str:
    d = date.fromisoformat(today)
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="radar")
    parser.add_argument("command",
                        choices=["collect", "process", "analyze", "report", "all"])
    parser.add_argument("--out", default="report.md")
    args = parser.parse_args(argv)

    runtime = load_runtime()
    settings = load_settings(CONFIG_DIR / "settings.yaml")
    repo = Repository(runtime.db_path)
    repo.init_schema()
    now = datetime.now().isoformat(timespec="seconds")
    today = date.today().isoformat()

    if args.command in ("collect", "all"):
        print("collected:", run_collect(repo, settings, runtime, now))
    if args.command in ("process", "all"):
        print("clusters:", run_process(repo, settings))
    if args.command in ("analyze", "all"):
        client = LLMClient(model=runtime.model, api_key=runtime.openai_api_key,
                           base_url=runtime.openai_base_url)
        print("analyzed:", run_analyze(repo, settings, client, today))
    if args.command in ("report", "all"):
        md = run_report(repo, week=_iso_week(today))
        Path(args.out).write_text(md, encoding="utf-8")
        print("report written:", args.out)
    repo.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_cli.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 运行全量测试**

Run: `pytest`
Expected: PASS（全部通过）

- [ ] **Step 6: Commit**

```bash
git add src/radar/cli.py tests/test_cli.py
git commit -m "feat: add cli orchestration for collect/process/analyze/report"
```

---

## Task 16: 人工审核命令 (`review` 子命令)

**Files:**
- Modify: `src/radar/cli.py`（新增 `run_review` 与 `review` 子命令分支）
- Test: `tests/test_cli.py`（追加审核测试）

人工审核在 MVP 用 CLI 完成：列出候选 → 对某条记录写入 verdict（如 `推荐正确/推荐过高/遗漏重要信息`）和备注，存入 `reviews` 表，供后续回测。

- [ ] **Step 1: 追加失败测试到 `tests/test_cli.py`**

```python
def test_run_review_persists_verdict():
    repo = make_repo_with_item()
    item_id = repo.item_id_by_raw("github:vllm-project/vllm")
    cli.run_review(repo, item_id=item_id, verdict="推荐正确",
                   note="已安排复现", reviewed_at="2026-06-08")
    row = repo.conn.execute(
        "SELECT verdict, note FROM reviews WHERE item_id=?", (item_id,)
    ).fetchone()
    assert row["verdict"] == "推荐正确"
    assert row["note"] == "已安排复现"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_cli.py::test_run_review_persists_verdict -v`
Expected: FAIL with `AttributeError: module 'radar.cli' has no attribute 'run_review'`

- [ ] **Step 3: 在 `cli.py` 新增 `run_review`（放在 `run_report` 之后）**

```python
def run_review(repo: Repository, item_id: int, verdict: str, note: str,
               reviewed_at: str) -> None:
    repo.save_review(item_id, verdict=verdict, note=note, reviewed_at=reviewed_at)
```

- [ ] **Step 4: 在 `main` 的 `parser` 中扩展（替换 `command` 与新增参数）**

把 `choices` 改为包含 `review`，并新增审核参数：

```python
    parser.add_argument("command",
                        choices=["collect", "process", "analyze", "report",
                                 "review", "all"])
    parser.add_argument("--out", default="report.md")
    parser.add_argument("--item-id", type=int)
    parser.add_argument("--verdict", default="")
    parser.add_argument("--note", default="")
```

并在 `main` 末尾（`report` 分支之后、`repo.close()` 之前）加入：

```python
    if args.command == "review":
        if args.item_id is None:
            parser.error("--item-id is required for review")
        run_review(repo, item_id=args.item_id, verdict=args.verdict,
                   note=args.note, reviewed_at=today)
        print("review saved for item", args.item_id)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_cli.py -v`
Expected: PASS（含新增的 review 测试）

- [ ] **Step 6: Commit**

```bash
git add src/radar/cli.py tests/test_cli.py
git commit -m "feat: add human review cli command"
```

---

## Task 17: 端到端冒烟测试与使用文档

**Files:**
- Create: `tests/test_end_to_end.py`
- Modify: `README.md`（追加"运行方式"章节）

用全 mock（注入假采集器/假 LLM）验证 `collect→process→analyze→report` 完整链路产出周报，不触网。

- [ ] **Step 1: 写端到端测试**

```python
from radar.models import TechItem
from radar.config import Settings
from radar.storage import Repository
from radar import cli


def settings():
    return Settings(
        weights={"practicality": 0.35, "influence": 0.30, "follow_cost": 0.20,
                 "source_tier": 0.10, "freshness": 0.05},
        tier_weight={"T1": 5, "T1.5": 4, "T2": 2},
        thresholds={"tool_framework": 3.8, "default": 4.0},
        github_min_stars=500, github_min_weekly_growth=50,
        keywords=["llm", "model", "inference"],
        title_similarity_threshold=0.6, time_window_days=7)


class StubClient:
    def complete_json(self, system, user):
        if "is_relevant" in system:
            return {"is_relevant": True}
        return {"category": "tool_framework", "summary": "高吞吐推理框架",
                "scores": {"practicality": 5, "influence": 5, "follow_cost": 4},
                "boundary": {"good_for": "推理", "not_good_for": "训练",
                             "risks": "兼容性"}}


def seed(repo):
    items = [
        TechItem(source="github", source_tier="T1.5", source_type="repo_index",
                 title="vLLM inference", url="https://github.com/vllm-project/vllm",
                 description="High-throughput LLM inference", published_at="2026-06-08",
                 metrics={"stars": 85000}, raw_id="github:vllm-project/vllm",
                 collected_at="2026-06-08T00:00:00"),
        TechItem(source="rss", source_tier="T1", source_type="official_blog",
                 title="vLLM inference released", url="https://media.com/vllm",
                 description="LLM inference news", published_at="2026-06-08",
                 metrics={}, raw_id="rss:https://media.com/vllm",
                 collected_at="2026-06-08T00:00:00"),
        TechItem(source="github", source_tier="T1.5", source_type="repo_index",
                 title="tiny repo", url="https://github.com/x/tiny",
                 description="not relevant", published_at="2026-06-08",
                 metrics={"stars": 10}, raw_id="github:x/tiny",
                 collected_at="2026-06-08T00:00:00"),
    ]
    for it in items:
        repo.upsert_item(it)


def test_full_pipeline_produces_report():
    repo = Repository(":memory:")
    repo.init_schema()
    seed(repo)
    cli.run_process(repo, settings())
    cli.run_analyze(repo, settings(), client=StubClient(), today="2026-06-08")
    md = cli.run_report(repo, week="2026-W23")

    assert "AI 技术情报周报 2026-W23" in md
    assert "vLLM inference" in md
    assert "建议跟进：1 项" in md       # 低 star repo 被过滤，两条 vLLM 聚为一簇
    assert "tiny repo" not in md
```

- [ ] **Step 2: 运行测试确认通过**

Run: `pytest tests/test_end_to_end.py -v`
Expected: PASS（1 passed）

> 若聚类未把两条 vLLM 合并（标题相似度边界），把 `seed` 中 RSS 标题调整得更接近，或确认 `title_similarity_threshold` 设置；这是预期内的可调点，不要改业务逻辑去迁就测试。

- [ ] **Step 3: 在 `README.md` 末尾追加运行说明**

```markdown
## 运行方式（MVP）

```bash
pip install -e ".[dev]"
cp .env.example .env   # 填入 OPENAI_API_KEY / GITHUB_TOKEN

radar collect   # 采集三类信源入库
radar process   # 去重、聚类、过滤
radar analyze   # LLM 预筛 + 维度评分 + 代码化综合评分
radar report --out report.md   # 生成 Markdown 周报
radar review --item-id 1 --verdict 推荐正确 --note "已安排复现"
# 或一次跑完：radar all
```

测试：`pytest`
```

- [ ] **Step 4: 运行全量测试**

Run: `pytest`
Expected: PASS（全部通过）

- [ ] **Step 5: Commit**

```bash
git add tests/test_end_to_end.py README.md
git commit -m "test: add end-to-end smoke test and usage docs"
```

---

## Task 18: 回测脚手架（Week 4 规则调优）

**Files:**
- Create: `src/radar/backtest.py`
- Test: `tests/test_backtest.py`

对照人工 `reviews`（verdict）与系统 `recommendation`，统计采纳率/误报率，支撑"调权重而不是堆 Prompt"的调优闭环。

- [ ] **Step 1: 写失败测试**

```python
from radar.backtest import evaluate


def test_evaluate_computes_precision_and_droprate():
    # (recommendation, verdict)
    records = [
        ("建议跟进", "推荐正确"),
        ("建议跟进", "推荐过高"),
        ("建议跟进", "推荐正确"),
        ("保持观察", "遗漏重要信息"),
    ]
    metrics = evaluate(records)
    assert metrics["recommended_total"] == 3
    assert metrics["recommended_correct"] == 2
    assert abs(metrics["precision"] - 2 / 3) < 1e-6
    assert metrics["missed"] == 1


def test_evaluate_handles_empty():
    metrics = evaluate([])
    assert metrics["precision"] == 0.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_backtest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'radar.backtest'`

- [ ] **Step 3: 实现 `backtest.py`**

```python
from __future__ import annotations


def evaluate(records: list[tuple[str, str]]) -> dict[str, float]:
    recommended = [(rec, verdict) for rec, verdict in records
                   if rec == "建议跟进"]
    correct = sum(1 for _, v in recommended if v == "推荐正确")
    missed = sum(1 for rec, v in records
                 if v == "遗漏重要信息" and rec != "建议跟进")
    total = len(recommended)
    return {
        "recommended_total": total,
        "recommended_correct": correct,
        "precision": (correct / total) if total else 0.0,
        "missed": missed,
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_backtest.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add src/radar/backtest.py tests/test_backtest.py
git commit -m "feat: add backtest metrics for recommendation quality"
```

---

## 与设计文档的映射（Spec 覆盖核查）

| 设计文档模块 | 实现任务 |
| --- | --- |
| Collector：GitHub / Hugging Face / RSS | Task 4 / 5 / 6 |
| Source Tier：信源分层（配置） | Task 2（`sources.yaml` + tier） |
| Normalizer：统一 `TechItem` | Task 1 + 各采集器归一化 |
| Filter & Cluster：去重 / 聚类 / 主条目 | Task 7 / 8 / 9 |
| LLM Prescreen + Dimension Scoring | Task 11 / 12 |
| Code Ranking：综合评分公式 + 阈值 | Task 13 |
| Human Review：人工审核 | Task 16 |
| Reporter：Markdown 周报 | Task 14 |
| 4 周计划 Week1-4 | Task 4（单源闭环）→ 5/6/7/8/9（多源降噪）→ 11/12/13/14（LLM+周报）→ 18（回测调优） |
| SQLite 存储 | Task 3 |

---

## 执行顺序建议

Task 0 → 1 → 2 → 3 是基础设施，必须先做且彼此依赖。Task 4/5/6（采集器）可并行。Task 7/8/9（pipeline 纯函数）可并行。Task 10 → 11/12（LLM）。Task 13/14 依赖前面的模型。Task 15 编排依赖几乎所有模块。Task 16/17/18 收尾。

每个 Task 自带 TDD（红-绿-提交），完成后即是一次可验证、可回滚的小步提交。

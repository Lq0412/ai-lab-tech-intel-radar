# 雷达精选与采集均衡化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 解决"周报里 33 条建议跟进太多、且分析资源全被 GitHub/HF 占据、RSS 几乎不参与"两个问题。改造为：周报只精选综合分 Top 8 作为「建议跟进」，候选分析按信源配额分配（GitHub/HF/RSS 都有名额），并适度扩大 GitHub 采集量。

**Architecture:** 三层改动，全部可配置、向后兼容：
1. **报告层 Top-N 精选**：`render_report` 把「建议跟进」按综合分排序后只保留前 N 名，其余降级进「观察列表」；阈值仍作为质量地板。
2. **候选层分源配额**：`run_analyze` 支持按 `{github, huggingface, rss}` 配额各取 signal_score 最高的若干条，取代单一 `--limit` 一刀切。
3. **采集层扩容**：GitHub 每源 `per_page` 默认 30→50，并在 `sources.yaml` 增加 GitHub 主题源。

**Tech Stack:** 现有 Python 项目（`src/radar/`），pytest TDD。所有新配置项带默认值，确保旧测试与旧 yaml 不被破坏。

**关键约束（必须遵守）：**
- 现有大量测试手动构造 `Settings(...)`（不含新字段），所以 **Settings 新增字段必须有默认值，且放在所有无默认值字段之后**。
- 现有 `render_report(rows, week=...)`、`run_report(repo, week=...)` 调用不带新参数，**新参数必须有默认值并保持旧行为**（默认 `max_recommendations=None` 时不截断）。
- `load_settings` 解析新配置项 **必须用 `.get` 带默认值**，确保旧 `settings.yaml` 仍能加载。

---

## 文件结构（涉及文件）

```text
src/radar/
├── config.py            # 修改：Settings 增 3 个字段；load_settings 解析新配置
├── report.py            # 修改：render_report 支持 max_recommendations 截断
├── ranking.py           # 修改：新增 select_by_quota
├── cli.py               # 修改：run_analyze 支持 quota；run_report 传 max_recommendations；main 接线 + --no-quota
└── collectors/github.py # 修改：per_page 默认 30→50
config/
├── settings.yaml        # 修改：增 max_recommendations / github_per_page / analyze.quota
└── sources.yaml         # 修改：增 GitHub 主题源
tests/
├── test_config.py             # 追加：新字段默认值测试
├── test_report.py             # 追加：Top-N 截断测试
├── test_ranking_candidates.py # 追加：select_by_quota 测试
└── test_cli.py                # 追加：run_analyze quota 测试
```

---

## Task 1: 扩展 Settings 与配置文件

**Files:**
- Modify: `src/radar/config.py`
- Modify: `config/settings.yaml`
- Test: `tests/test_config.py`

新增三个可调参数：`max_recommendations`（周报精选上限）、`github_per_page`（GitHub 单源采集条数）、`analyze_quota`（分源分析配额）。

- [ ] **Step 1: 写失败测试**（追加到 `tests/test_config.py` 末尾）

```python
def test_settings_has_tuning_defaults():
    from radar.config import Settings
    s = Settings(
        weights={}, tier_weight={}, thresholds={"default": 4.0},
        github_min_stars=500, github_min_weekly_growth=50, keywords=[],
        title_similarity_threshold=0.6, time_window_days=7)
    assert s.max_recommendations == 8
    assert s.github_per_page == 50
    assert s.analyze_quota == {"github": 20, "huggingface": 15, "rss": 15}


def test_load_settings_reads_tuning_fields():
    from pathlib import Path
    from radar.config import load_settings
    s = load_settings(Path("config/settings.yaml"))
    assert s.max_recommendations == 8
    assert s.github_per_page == 50
    assert s.analyze_quota["github"] >= 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `TypeError`/`AttributeError`（Settings 无 `max_recommendations` 等字段）

- [ ] **Step 3: 修改 `Settings` 数据类**（`src/radar/config.py`）

把现有 `Settings` 定义替换为（新增 3 个带默认值字段，放在 `time_window_days` 之后、`threshold_for` 之前）：

```python
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
```

（`field` 已在文件顶部 `from dataclasses import dataclass, field` 导入，无需新增 import。）

- [ ] **Step 4: 修改 `load_settings`**（`src/radar/config.py`）

把现有 `load_settings` 的 return 之前与 return 替换为：

```python
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
```

- [ ] **Step 5: 更新 `config/settings.yaml`**

在 `ranking:` 块末尾（`thresholds` 之后）增加 `max_recommendations`；在 `filter:` 块增加 `github_per_page`；在文件末尾新增 `analyze:` 块。改完后完整文件如下：

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
  max_recommendations: 8

filter:
  github_min_stars: 500
  github_min_weekly_growth: 50
  github_per_page: 50
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

analyze:
  quota:
    github: 20
    huggingface: 15
    rss: 15
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_config.py -v`
Expected: PASS（含新增 2 个测试）

- [ ] **Step 7: 跑全量回归**

Run: `pytest -q`
Expected: 全部 PASS（确认新字段默认值未破坏其它手动构造 Settings 的测试）

- [ ] **Step 8: Commit**

```bash
git add src/radar/config.py config/settings.yaml tests/test_config.py
git commit -m "feat: add tuning settings (max_recommendations, quota, github_per_page)"
```

---

## Task 2: 报告层 Top-N 精选

**Files:**
- Modify: `src/radar/report.py`
- Modify: `src/radar/cli.py`（`run_report` 传参 + `main` 接线）
- Test: `tests/test_report.py`

`render_report` 增加 `max_recommendations` 参数：「建议跟进」按综合分排序后只保留前 N 名，超出的降级进「观察列表」。本周结论统计反映精选后的数字。`max_recommendations=None` 时保持旧行为（不截断）。

- [ ] **Step 1: 写失败测试**（追加到 `tests/test_report.py` 末尾）

```python
def test_render_report_caps_recommendations():
    rows = [row(f"工具{i}", "建议跟进", score=4.9 - i * 0.1) for i in range(12)]
    md = render_report(rows, week="2026-W23", max_recommendations=8)
    assert "建议跟进：8 项" in md
    assert "保持观察：4 项" in md
    # 第 9-12 名降级到观察列表，不出现在 Top 推荐编号里
    assert "### 9." not in md


def test_render_report_no_cap_keeps_all():
    rows = [row(f"工具{i}", "建议跟进", score=4.5) for i in range(10)]
    md = render_report(rows, week="2026-W23")  # 不传 max_recommendations
    assert "建议跟进：10 项" in md
```

（说明：`row(...)` 辅助函数已在 `tests/test_report.py` 顶部定义，签名 `row(title, rec, score=4.65, related=None)`，可直接复用。）

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_report.py -v`
Expected: FAIL with `TypeError: render_report() got an unexpected keyword argument 'max_recommendations'`

- [ ] **Step 3: 修改 `render_report`**（`src/radar/report.py`）

把整个 `render_report` 函数替换为：

```python
def render_report(rows: list[ReportRow], week: str,
                  max_recommendations: int | None = None) -> str:
    follow_all = sorted(
        [r for r in rows if r.recommendation == "建议跟进"],
        key=lambda r: r.quality_score, reverse=True)
    if max_recommendations is not None and max_recommendations > 0:
        top = follow_all[:max_recommendations]
        demoted = follow_all[max_recommendations:]
    else:
        top, demoted = follow_all, []
    watch = sorted(
        [r for r in rows if r.recommendation == "保持观察"] + demoted,
        key=lambda r: r.quality_score, reverse=True)
    skip = [r for r in rows if r.recommendation == "暂不投入"]

    lines = [f"# AI 技术情报周报 {week}", "", "## 本周结论", "",
             f"- 建议跟进：{len(top)} 项",
             f"- 保持观察：{len(watch)} 项",
             f"- 暂不投入：{len(skip)} 项", ""]

    lines.append("## Top 推荐")
    lines.append("")
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
        for r in watch:
            lines.append(f"- {r.title}（{r.quality_score}/5）- {r.summary}")
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_report.py -v`
Expected: PASS（含新增 2 个测试；旧的 `test_render_report_*` 仍通过，因为默认不截断）

- [ ] **Step 5: 修改 `run_report` 接受并传递 `max_recommendations`**（`src/radar/cli.py`）

把现有 `run_report` 的函数签名与最后一行替换为：

```python
def run_report(repo: Repository, week: str,
               max_recommendations: int | None = None) -> str:
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
    return render_report(rows, week=week,
                         max_recommendations=max_recommendations)
```

- [ ] **Step 6: 修改 `main` 的 report 分支传入配置值**（`src/radar/cli.py`）

把 `main` 中 report 分支：

```python
    if args.command in ("report", "all"):
        md = run_report(repo, week=_iso_week(today))
        Path(args.out).write_text(md, encoding="utf-8")
        print("report written:", args.out)
```

替换为：

```python
    if args.command in ("report", "all"):
        md = run_report(repo, week=_iso_week(today),
                        max_recommendations=settings.max_recommendations)
        Path(args.out).write_text(md, encoding="utf-8")
        print("report written:", args.out)
```

- [ ] **Step 7: 跑全量回归**

Run: `pytest -q`
Expected: 全部 PASS

- [ ] **Step 8: Commit**

```bash
git add src/radar/report.py src/radar/cli.py tests/test_report.py
git commit -m "feat: cap weekly recommendations to top-N by quality score"
```

---

## Task 3: 候选层分源配额

**Files:**
- Modify: `src/radar/ranking.py`（新增 `select_by_quota`）
- Modify: `src/radar/cli.py`（`run_analyze` 支持 `quota`；`main` 接线 + `--no-quota`）
- Test: `tests/test_ranking_candidates.py`
- Test: `tests/test_cli.py`

`select_by_quota` 按来源分组，每组取 `signal_score` 最高的 N 条，让 RSS/GitHub/HF 都有固定分析名额。`run_analyze` 优先用 `quota`，无 quota 时回退到原 `limit` 行为。

- [ ] **Step 1: 写失败测试**（追加到 `tests/test_ranking_candidates.py` 末尾）

```python
def test_select_by_quota_allocates_per_source():
    from radar.ranking import select_by_quota
    s = settings()
    items = (
        [item("github", f"gh{i}", stars=1000 * (i + 1)) for i in range(5)]
        + [item("huggingface", f"hf{i}", downloads=1000 * (i + 1)) for i in range(5)]
        + [item("rss", f"rss{i}", tier="T1") for i in range(5)]
    )
    picked = select_by_quota(
        items, {"github": 2, "huggingface": 3, "rss": 1},
        today="2026-06-08", settings=s)
    by_source = {}
    for it in picked:
        by_source[it.source] = by_source.get(it.source, 0) + 1
    assert by_source == {"github": 2, "huggingface": 3, "rss": 1}


def test_select_by_quota_picks_highest_signal():
    from radar.ranking import select_by_quota
    s = settings()
    items = [
        item("github", "low", stars=600),
        item("github", "high", stars=90000),
    ]
    picked = select_by_quota(items, {"github": 1}, today="2026-06-08", settings=s)
    assert len(picked) == 1
    assert picked[0].title == "high"
```

（说明：`settings()` 与 `item(...)` 辅助函数已在 `tests/test_ranking_candidates.py` 顶部定义，直接复用。）

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_ranking_candidates.py -v`
Expected: FAIL with `ImportError: cannot import name 'select_by_quota'`

- [ ] **Step 3: 新增 `select_by_quota`**（`src/radar/ranking.py` 文件末尾追加）

```python
def select_by_quota(items: list[TechItem], quota: dict[str, int],
                    today: str, settings: Settings) -> list[TechItem]:
    """Pick top signal_score items per source according to quota."""
    selected: list[TechItem] = []
    for source, n in quota.items():
        if n <= 0:
            continue
        group = sorted(
            [it for it in items if it.source == source],
            key=lambda it: signal_score(it, settings, today),
            reverse=True,
        )
        selected.extend(group[:n])
    return selected
```

- [ ] **Step 4: 运行 ranking 测试确认通过**

Run: `pytest tests/test_ranking_candidates.py -v`
Expected: PASS（含新增 2 个测试）

- [ ] **Step 5: 写 `run_analyze` quota 失败测试**（追加到 `tests/test_cli.py` 末尾）

```python
def test_run_analyze_uses_quota():
    repo = Repository(":memory:")
    repo.init_schema()
    repo.upsert_item(TechItem(
        source="github", source_tier="T1.5", source_type="repo_index",
        title="gh-llm", url="https://github.com/x/gh",
        description="LLM inference", published_at="2026-06-08",
        metrics={"stars": 9000}, raw_id="github:gh",
        collected_at="2026-06-08T00:00:00"))
    repo.upsert_item(TechItem(
        source="huggingface", source_tier="T1.5", source_type="model_index",
        title="hf-model", url="https://huggingface.co/x/hf",
        description="LLM model", published_at="2026-06-08",
        metrics={"downloads": 50000, "likes": 100}, raw_id="huggingface:hf",
        collected_at="2026-06-08T00:00:00"))
    cli.run_process(repo, settings())
    cli.run_analyze(repo, settings(), client=StubClient(), today="2026-06-08",
                    quota={"github": 1, "huggingface": 0, "rss": 0})
    assert len(repo.list_scored()) == 1
```

- [ ] **Step 6: 运行测试确认失败**

Run: `pytest tests/test_cli.py::test_run_analyze_uses_quota -v`
Expected: FAIL with `TypeError: run_analyze() got an unexpected keyword argument 'quota'`

- [ ] **Step 7: 修改 `run_analyze` 支持 quota**（`src/radar/cli.py`）

先更新 import 行（把 ranking 的 import 替换）：

```python
from radar.ranking import compute_quality, recommend, select_by_quota, select_candidates
```

再把 `run_analyze` 函数开头替换为（保留函数体其余逻辑不变）：

```python
def run_analyze(repo: Repository, settings: Settings, client: LLMClient,
                today: str, limit: int | None = None,
                quota: dict[str, int] | None = None) -> int:
    items = repo.list_items(only_unique=True)
    if quota:
        primaries = select_by_quota(items, quota, today, settings)
    else:
        primaries = select_candidates(items, limit, today, settings)
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
```

- [ ] **Step 8: 在 `main` 接线 quota 与 `--no-quota`**（`src/radar/cli.py`）

在 argparse 参数区（`--limit` 之后）新增：

```python
    parser.add_argument("--no-quota", action="store_true",
                        help="忽略分源配额，改用 --limit 一刀切")
```

把 `main` 中 analyze 分支：

```python
    if args.command in ("analyze", "all"):
        client = LLMClient(model=runtime.model, api_key=runtime.openai_api_key,
                           base_url=runtime.openai_base_url)
        limit = args.limit if args.limit > 0 else None
        print("analyzed:", run_analyze(repo, settings, client, today, limit=limit))
```

替换为：

```python
    if args.command in ("analyze", "all"):
        client = LLMClient(model=runtime.model, api_key=runtime.openai_api_key,
                           base_url=runtime.openai_base_url)
        limit = args.limit if args.limit > 0 else None
        quota = None if args.no_quota else settings.analyze_quota
        print("analyzed:",
              run_analyze(repo, settings, client, today, limit=limit, quota=quota))
```

- [ ] **Step 9: 运行测试确认通过**

Run: `pytest tests/test_cli.py -v`
Expected: PASS（含新增 quota 测试；旧的 `test_run_analyze_*` 仍通过）

- [ ] **Step 10: 跑全量回归**

Run: `pytest -q`
Expected: 全部 PASS

- [ ] **Step 11: Commit**

```bash
git add src/radar/ranking.py src/radar/cli.py tests/test_ranking_candidates.py tests/test_cli.py
git commit -m "feat: allocate analysis candidates by per-source quota"
```

---

## Task 4: GitHub 采集扩容

**Files:**
- Modify: `src/radar/collectors/github.py`（`per_page` 默认 30→50）
- Modify: `src/radar/cli.py`（`run_collect` 传入 `settings.github_per_page`）
- Modify: `config/sources.yaml`（新增 GitHub 主题源）
- Test: `tests/collectors/test_github.py`

让 GitHub 候选池更有代表性：单源采集量提到 50，并新增 `llm`、`agent` 两个主题源。

- [ ] **Step 1: 写失败测试**（追加到 `tests/collectors/test_github.py` 末尾）

```python
def test_github_collector_default_per_page_is_50():
    collector = GithubCollector(client=FakeClient({"items": []}), token="")
    assert collector.per_page == 50


def test_github_collector_passes_per_page_param():
    fake = FakeClient({"items": []})
    source = Source(name="gh", url="topic:llm stars:>500",
                    tier="T1.5", type="repo_index", kind="github")
    GithubCollector(client=fake, token="", per_page=50).collect(
        source, now="2026-06-08T00:00:00")
    assert fake.last_params["per_page"] == 50
```

（说明：`FakeClient` 已在 `tests/collectors/test_github.py` 顶部定义并记录 `last_params`，`Source` 已 import，直接复用。）

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/collectors/test_github.py -v`
Expected: FAIL（默认 `per_page` 仍为 30）

- [ ] **Step 3: 修改 `GithubCollector` 默认 per_page**（`src/radar/collectors/github.py`）

把构造函数签名：

```python
    def __init__(self, client: Any | None = None, token: str = "",
                 per_page: int = 30):
```

替换为：

```python
    def __init__(self, client: Any | None = None, token: str = "",
                 per_page: int = 50):
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/collectors/test_github.py -v`
Expected: PASS

- [ ] **Step 5: 让 `run_collect` 使用配置的 per_page**（`src/radar/cli.py`）

把 `run_collect` 中 collectors 字典：

```python
    collectors = {
        "github": GithubCollector(token=runtime.github_token),
        "huggingface": HuggingFaceCollector(),
        "rss": RssCollector(),
    }
```

替换为：

```python
    collectors = {
        "github": GithubCollector(token=runtime.github_token,
                                  per_page=settings.github_per_page),
        "huggingface": HuggingFaceCollector(),
        "rss": RssCollector(),
    }
```

- [ ] **Step 6: 新增 GitHub 主题源**（`config/sources.yaml`）

在 `sources:` 列表末尾追加两条（保持现有 4 条不动）：

```yaml
  - name: GitHub Trending LLM
    url: "topic:llm stars:>500"
    tier: T1.5
    type: repo_index
    kind: github
  - name: GitHub Trending Agent
    url: "topic:agent stars:>300"
    tier: T1.5
    type: repo_index
    kind: github
```

- [ ] **Step 7: 跑全量回归**

Run: `pytest -q`
Expected: 全部 PASS

- [ ] **Step 8: Commit**

```bash
git add src/radar/collectors/github.py src/radar/cli.py config/sources.yaml tests/collectors/test_github.py
git commit -m "feat: expand github collection (per_page 50 + more topic sources)"
```

---

## Task 5: 真实数据验证（重跑流水线）

**Files:** 无代码改动，仅运行验证。需要 `.env` 已配置 `DEEPSEEK_API_KEY` 与 `GITHUB_TOKEN`。

> 注意：本步会真实调用 DeepSeek，约 50 条候选 ≈ 100 次调用，耗时数分钟、产生 API 费用。若执行者无密钥或不便联网，可跳过本 Task 并向调用者说明。

- [ ] **Step 1: 清库重采（避免旧数据干扰配额验证）**

```bash
# Windows PowerShell
Remove-Item radar.db -ErrorAction SilentlyContinue
radar collect
radar process
```

Expected: `collected:` 数百~上千；`clusters:` 输出聚类数

- [ ] **Step 2: 按配额分析**

Run: `radar analyze`
Expected: `analyzed:` 约 50（= 配额 20+15+15 内的实际命中数）

- [ ] **Step 3: 生成周报并人工查看**

Run: `radar report --out report.md`
然后用编辑器打开 `report.md`，确认：
- 「本周结论」中 **建议跟进 ≤ 8 项**
- 「Top 推荐」编号最多到 8
- 来源不再全是 GitHub（应能看到 RSS / HF 条目进入分析）

- [ ] **Step 4: 统计来源分布（可选，确认配额生效）**

```bash
python -c "import sqlite3; c=sqlite3.connect('radar.db'); c.row_factory=sqlite3.Row; rows=c.execute('SELECT i.source, COUNT(*) n FROM analyses a JOIN items i ON i.id=a.item_id GROUP BY i.source').fetchall(); [print(r['source'], r['n']) for r in rows]"
```

Expected: github / huggingface / rss 三类都有非零计数（不再是 RSS 仅 1 条）

- [ ] **Step 5: 报告结果**

无需 commit（`radar.db` 与 `report.md` 已在 `.gitignore` / 为产物）。向调用者汇报：建议跟进条数、三源分布、是否符合预期。

---

## 与问题的映射（覆盖核查）

| 原问题 | 解决任务 |
| --- | --- |
| 33 条「建议跟进」太多，决策者无从下手 | Task 2（Top-8 精选）|
| 分析资源全被 GitHub/HF 占据，RSS 973 条几乎不参与 | Task 3（分源配额）|
| GitHub 仅采集 30 条（一页），候选池代表性不足 | Task 4（per_page 50 + 主题源）|
| 上述参数需可调、不硬编码 | Task 1（settings.yaml + Settings 字段）|
| 改动不能破坏现有 47 个测试 | 各 Task 新字段/参数均带默认值 + 每步全量回归 |

## 执行顺序与依赖

Task 1 是基础（其它任务依赖新 Settings 字段），**必须最先完成**。Task 2、3、4 相互独立，可按顺序做。Task 5 依赖 1-4 全部完成且需要 API 密钥，放最后。

每个 Task 自带 TDD（红-绿-提交）。完成 Task 1-4 后，全量 `pytest -q` 应为：原 47 个测试 + 新增约 8 个测试全部通过。

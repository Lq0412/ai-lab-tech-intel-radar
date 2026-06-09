# 雷达「从榜单到情报」升级 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: 用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 按 Task 逐个实现。步骤用 `- [ ]` 跟踪。**务必串行执行 Task，前一个 Task 提交后再开下一个**（历史上并行派发导致过 Settings 字段冲突）。

**Goal:** 把当前「GitHub 高星榜单复读机」改造成真正的「技术情报雷达」。核心是从 **存量（绝对 star/下载量）** 转向 **增量（周增长 + 时效 + 新颖性）**，并清除教程/资源汇总类噪音，让周报体现「这周发生了什么新变化」。

---

## 背景：当前周报为什么「没意思」（诊断结论）

跑出来的周报本质是 GitHub 历史高星榜单，证据与根因：

| 症状 | 报告中的证据 | 代码根因 |
|------|------------|---------|
| 全是常青老项目 | spaCy / fairseq / GPT-2 / OPT-125m / DistilGPT2 | `collectors/github.py` 用 `sort=stars desc` 拉历史最高星；`published_at` 取 `pushed_at` |
| 没有增长信号 | 无任何「本周新增 star」 | 配置有 `github_min_weekly_growth` 但**从未被使用**；`signal_score` 用 `log10(stars)` 绝对量 |
| 打分趋同无区分 | 前 20 条挤在 4.4–4.9 | `scoring.py` prompt 无校准要求，LLM 对名气大者一律高分 |
| 「相关报道」恒为 0 | 每条都 `0 条，已折叠` | `cluster.py` 仅按标题相似度聚合，跨源（仓库名 vs RSS 标题）永不匹配 |
| 噪音进推荐 | Deep-Live-Cam、AIHawk、h4cker、AI-For-Beginners、LLMs-from-scratch、prompts.chat | `filter.py` 只判断 `stars>=500`，无类型/主题降噪 |
| 摘要是 README 翻译 | 每条只说「是什么」，无「这周为何值得看」 | prompt 只要一句话摘要，无「变化/亮点」字段 |

**一句话：情报的本质是 delta，而系统全靠绝对量。**

---

## Architecture（五层改动，全部可配置、向后兼容）

1. **指标快照基础设施**：新增 `metric_snapshots` 表，每次 collect 记录每条目的 star/下载量快照；提供「周增长」查询。这是 delta 的数据地基。
2. **时效性采集**：`sources.yaml` 增加「近期新增/活跃」GitHub 源（`created:>` / `sort=updated`）；`Source` 支持可选 `sort`；采集层按时间窗过滤。
3. **信号重排**：`signal_score` 改为以「周增长 + 时效」为主、绝对量为辅，让上升中的新项目击败常青巨头。
4. **降噪**：`filter.py` 按标题/主题关键词剔除教程/awesome/书籍/路线图类；`recommend` 对低价值类目提高门槛。
5. **打分锚定 + 增量呈现**：`scoring.py` prompt 要求拉满 1–5 区间、加「新颖性」维度与「本周变化」字段；`report.py` 展示周增长、时效、新颖性。

可选（性价比较低，放最后）：**真聚类** 按实体名跨源归并，让「相关报道」真正出现。

**Tech Stack:** 现有 Python 项目（`src/radar/`），pytest TDD。

---

## 关键约束（必须遵守，否则破坏现有 56 个测试）

- **`Settings` 新增字段必须带默认值，且放在现有所有字段之后**（大量测试手动构造 `Settings(...)`）。
- **`Source` 新增字段必须带默认值**（`Source(**entry)` 从 yaml 反序列化，旧 yaml 无该键）。
- **`load_settings` / `load_sources` 解析新配置必须用 `.get` 带默认**，旧 yaml 仍能加载。
- **DB 用 `CREATE TABLE IF NOT EXISTS`**：新增表安全；**不要给现有表加列**（无迁移机制，旧库会缺列）。新数据一律进新表。
- **`signal_score`、`compute_quality`、`render_report` 等函数签名变更必须保持旧调用兼容**（新参数带默认值）。
- 每个 Task：先写失败测试 → 跑确认失败 → 实现 → 跑通 → 跑全量 `pytest -q` 确认无回归 → commit。

---

## 文件结构（涉及文件）

```text
src/radar/
├── storage.py            # Task 1: 新增 metric_snapshots 表 + 快照写入/周增长查询
├── cli.py                # Task 1/3: run_collect 写快照；analyze 用增长
├── collectors/github.py  # Task 3: 支持 source.sort；published_at 改用 created_at
├── collectors/huggingface.py # Task 3: 支持 source.sort
├── config.py             # Task 3/4/5: Source 增 sort 字段；Settings 增降噪/信号配置
├── ranking.py            # Task 3: signal_score 改用增长+时效；compute_quality 加新颖性
├── pipeline/filter.py    # Task 4: 噪音类目剔除
├── llm/scoring.py        # Task 5: prompt 校准 + novelty + 本周变化字段
├── models.py             # Task 5: Analysis 增 novelty / highlight 字段
└── report.py             # Task 5: 呈现周增长/时效/新颖性
config/
├── sources.yaml          # Task 3: 增时效性源
└── settings.yaml         # Task 3/4/5: 增信号/降噪/权重配置
tests/                    # 各 Task 对应追加测试
```

---

## Task 1: 指标快照表 + 周增长查询（delta 地基）

**Files:** Modify `src/radar/storage.py`, `src/radar/cli.py`；Test `tests/test_storage.py`

**意图：** 每次采集记录每条目的核心指标快照（GitHub star / HF 下载量），从而能算出「相比约 7 天前增长了多少」。首次运行无历史时增长为 0（不报错），多周运行后产生真实 delta。

- [ ] **Step 1: 写失败测试**（追加到 `tests/test_storage.py`）

```python
def test_metric_snapshot_and_weekly_growth(tmp_path):
    from radar.storage import Repository
    repo = Repository(str(tmp_path / "t.db"))
    repo.init_schema()
    repo.record_snapshot("github:a/b", 1000, captured_at="2026-06-01")
    repo.record_snapshot("github:a/b", 1500, captured_at="2026-06-09")
    # 最新值 1500，约一周前 1000 → 增长 500
    assert repo.weekly_growth("github:a/b", today="2026-06-09") == 500
    # 无历史的条目增长为 0
    assert repo.weekly_growth("github:x/y", today="2026-06-09") == 0
```

- [ ] **Step 2: 跑确认失败** `pytest tests/test_storage.py -k snapshot -v`（无 `record_snapshot`）

- [ ] **Step 3: 实现**（`src/radar/storage.py`）

在 `SCHEMA` 末尾追加表：

```python
CREATE TABLE IF NOT EXISTS metric_snapshots (
    raw_id TEXT NOT NULL,
    value INTEGER NOT NULL,
    captured_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snap_raw ON metric_snapshots(raw_id);
```

在 `Repository` 增加方法：

```python
def record_snapshot(self, raw_id: str, value: int, captured_at: str) -> None:
    self.conn.execute(
        "INSERT INTO metric_snapshots (raw_id, value, captured_at) VALUES (?,?,?)",
        (raw_id, int(value), captured_at))
    self.conn.commit()

def weekly_growth(self, raw_id: str, today: str) -> int:
    rows = self.conn.execute(
        "SELECT value, captured_at FROM metric_snapshots WHERE raw_id=? "
        "ORDER BY captured_at", (raw_id,)).fetchall()
    if len(rows) < 2:
        return 0
    latest = rows[-1]["value"]
    # 取截止 today-7 的最近一条作为基线；没有则用最早一条
    from datetime import date, timedelta
    cutoff = (date.fromisoformat(today) - timedelta(days=7)).isoformat()
    baseline = rows[0]["value"]
    for r in rows:
        if r["captured_at"] <= cutoff:
            baseline = r["value"]
    return max(0, latest - baseline)
```

- [ ] **Step 4: collect 写快照**（`src/radar/cli.py` 的 `run_collect`，在 `repo.upsert_item(item)` 之后）

```python
            repo.upsert_item(item)
            metric = item.metrics.get("stars") or item.metrics.get("downloads") or 0
            if metric:
                repo.record_snapshot(item.raw_id, metric, captured_at=now[:10])
            count += 1
```

- [ ] **Step 5: 验证** `pytest tests/test_storage.py -v` 通过；`pytest -q` 全绿。
- [ ] **Step 6: commit** `feat: add metric snapshots and weekly growth tracking`

---

## Task 2: signal_score 改用增长 + 时效（候选排序去存量化）

**Files:** Modify `src/radar/ranking.py`, `src/radar/cli.py`；Test `tests/test_ranking.py`

**意图：** 候选优先级不再由绝对 star 主导，而是「周增长（log 放大）+ 时效 + 适度绝对量」。让 `run_analyze` 优先把 LLM 预算花在「正在上升 / 新出现」的条目上。

- [ ] **Step 1: 写失败测试**（追加到 `tests/test_ranking.py`）

```python
def test_signal_score_rewards_growth():
    from radar.ranking import signal_score
    from radar.config import Settings
    from radar.models import TechItem
    s = Settings(weights={}, tier_weight={"T1.5": 4}, thresholds={"default": 4.0},
                 github_min_stars=500, github_min_weekly_growth=50, keywords=[],
                 title_similarity_threshold=0.6, time_window_days=7)
    base = dict(source="github", source_tier="T1.5", source_type="repo_index",
                description="", metrics={"stars": 5000}, collected_at="2026-06-09",
                published_at="2026-06-09")
    old_giant = TechItem(title="giant", url="u1", raw_id="github:giant", **base)
    rising = TechItem(title="rising", url="u2", raw_id="github:rising",
                      **{**base, "metrics": {"stars": 1200}})
    # giant 无增长(0)，rising 本周 +800 → rising 信号更高
    sg = signal_score(old_giant, s, "2026-06-09", growth=0)
    sr = signal_score(rising, s, "2026-06-09", growth=800)
    assert sr > sg
```

- [ ] **Step 2: 跑确认失败**（`signal_score` 无 `growth` 参数）

- [ ] **Step 3: 实现**（`src/radar/ranking.py`）— 给 `signal_score` 增 `growth` 参数，增长为主：

```python
def signal_score(item: TechItem, settings: Settings, today: str,
                 growth: int = 0) -> float:
    tier = settings.tier_weight.get(item.source_tier, 2)
    fresh = freshness_score(item.published_at, today)
    growth_signal = math.log10(max(growth, 1)) * 12  # 增长为主导信号
    if item.source == "github":
        stars = item.metrics.get("stars", 0)
        return tier * 6 + growth_signal + math.log10(max(stars, 1)) * 2 + fresh * 2
    if item.source == "huggingface":
        downloads = item.metrics.get("downloads", 0)
        return (tier * 6 + growth_signal
                + math.log10(max(downloads, 1)) * 2 + fresh * 2)
    return tier * 8 + fresh * 3
```

- [ ] **Step 4: 让 `select_candidates` / `select_by_quota` 接受按 raw_id 取增长的回调**

为最小改动，给两函数增可选 `growth_of: Callable[[str], int] | None = None`，在排序 key 里 `growth=growth_of(it.raw_id) if growth_of else 0`。保持旧调用（不传）行为不变。

- [ ] **Step 5: `run_analyze` 注入增长**（`src/radar/cli.py`）：定义 `growth_of = lambda rid: repo.weekly_growth(rid, today)` 传入 `select_by_quota` / `select_candidates`。

- [ ] **Step 6: 验证** `pytest tests/test_ranking.py tests/test_ranking_candidates.py -v` + `pytest -q` 全绿。
- [ ] **Step 7: commit** `feat: prioritize candidates by weekly growth over absolute stars`

---

## Task 3: 时效性采集源（抓「新增/上升」而非「历史最高」）

**Files:** Modify `src/radar/config.py`, `src/radar/collectors/github.py`, `src/radar/collectors/huggingface.py`, `config/sources.yaml`；Test `tests/collectors/test_github.py`

**意图：** 让采集本身就偏向新鲜事物。GitHub 增加按 `created:>`（近期新建）和 `sort=updated`（近期活跃）的查询；`published_at` 改用 `created_at`（真实诞生时间）而非 `pushed_at`。

- [ ] **Step 1: `Source` 增可选 `sort` 字段**（`src/radar/config.py`，带默认值，置于末尾）

```python
@dataclass
class Source:
    name: str
    url: str
    tier: str
    type: str
    kind: str
    sort: str = ""   # github: stars|updated; hf: downloads|trending；空=采集器默认
```

`load_sources` 用 `Source(**entry)` 仍可工作（旧 yaml 无 `sort` → 默认空）。

- [ ] **Step 2: 写失败测试**（`tests/collectors/test_github.py`，用 fake client 断言请求参数）

```python
def test_github_collector_respects_sort_and_records_created():
    # 用现有 fake client 模式：source.sort="updated" 时 params["sort"]=="updated"
    # 且 TechItem.published_at 来自 created_at
    ...
```

（按该测试文件现有 fake client 写法补全；断言 `params["sort"] == source.sort or "stars"`，且条目 `published_at` 取 `repo["created_at"][:10]`。）

- [ ] **Step 3: 实现**（`src/radar/collectors/github.py`）

```python
params = {"q": source.url, "sort": source.sort or "stars",
          "order": "desc", "per_page": self.per_page}
...
published_at=(repo.get("created_at") or repo.get("pushed_at") or "")[:10] or None,
metrics={"stars": repo.get("stargazers_count", 0),
         "language": repo.get("language") or "",
         "pushed_at": (repo.get("pushed_at") or "")[:10]},
```

- [ ] **Step 4: HF 采集器支持 `source.sort`**（`huggingface.py`：`_parse_query` 接受 sort 覆盖，默认 downloads）。

- [ ] **Step 5: `sources.yaml` 增时效源**（保留原有，新增）：

```yaml
  - name: GitHub New & Rising LLM
    url: "topic:llm created:>2026-04-01 stars:>100"
    tier: T1.5
    type: repo_index
    kind: github
    sort: stars
  - name: GitHub Recently Active Agents
    url: "topic:agent stars:>300"
    tier: T1.5
    type: repo_index
    kind: github
    sort: updated
```

> 注：`created:>` 日期是动态的。MVP 先硬编码近 2 个月；后续可在 collect 时用「今天-60 天」自动生成（记为可选优化）。

- [ ] **Step 6: 验证** `pytest tests/collectors -v` + `pytest -q` 全绿。
- [ ] **Step 7: commit** `feat: add recency-biased github sources and source-level sort`

---

## Task 4: 降噪（剔除教程/资源汇总/书籍类）

**Files:** Modify `src/radar/config.py`, `src/radar/pipeline/filter.py`, `config/settings.yaml`；Test `tests/pipeline/test_filter.py`

**意图：** 把对 AI Lab 无工程情报价值的「学习资源/清单/教程」类在过滤阶段剔除，不占分析预算、不进周报。

- [ ] **Step 1: `Settings` 增 `noise_keywords`**（`config.py`，默认值，置末尾）

```python
    noise_keywords: list[str] = field(default_factory=lambda: [
        "awesome", "tutorial", "tutorials", "roadmap", "for-beginners",
        "from-scratch", "course", "courses", "book", "books", "cookbook",
        "examples", "cheatsheet", "interview", "100-days", "learn",
        "study", "curriculum", "guide", "papers", "paper-list", "collection"])
```

`load_settings` 增 `noise_keywords=flt.get("noise_keywords", <同上默认>)`。

- [ ] **Step 2: 写失败测试**（`tests/pipeline/test_filter.py`）

```python
def test_filter_drops_noise_repos():
    from radar.pipeline.filter import apply_filters
    # 一个 awesome-list 仓库（star 够高）应被丢弃
    # 一个正常工具仓库应保留
    ...
    assert any("awesome" in d.title.lower() for d in dropped)
    assert all("awesome" not in k.title.lower() for k in kept)
```

- [ ] **Step 3: 实现**（`src/radar/pipeline/filter.py`）在 `_keeps` 里，对 github 条目先判噪音：

```python
def _is_noise(item: TechItem, settings: Settings) -> bool:
    text = f"{item.title} {item.description}".lower()
    return any(kw in text for kw in settings.noise_keywords)

def _keeps(item: TechItem, settings: Settings) -> bool:
    if item.source == "github":
        if _is_noise(item, settings):
            return False
        return item.metrics.get("stars", 0) >= settings.github_min_stars
    ...
```

- [ ] **Step 4: 验证** `pytest tests/pipeline/test_filter.py -v` + `pytest -q` 全绿。
- [ ] **Step 5: commit** `feat: filter out tutorial/awesome-list noise from github`

---

## Task 5: 打分锚定 + 新颖性维度 + 增量呈现

**Files:** Modify `src/radar/llm/scoring.py`, `src/radar/models.py`, `src/radar/ranking.py`, `src/radar/report.py`, `src/radar/cli.py`, `config/settings.yaml`；Test `tests/llm/test_scoring.py`, `tests/test_report.py`

**意图：** 解决「分数趋同 + 摘要无洞察」。给 LLM 增「新颖性」维度并要求拉满 1–5 区间、明确「名气大但陈旧应低分」；新增「本周亮点/变化」字段；周报展示周增长、时效与新颖性。

- [ ] **Step 1: `Analysis` 增字段**（`src/radar/models.py`，带默认值）

```python
    novelty: int = 0
    highlight: str = ""   # 这周为何值得关注 / 有何变化
```

- [ ] **Step 2: 写失败测试**（`tests/llm/test_scoring.py`）：fake client 返回含 `novelty` 与 `highlight`，断言 `score_item` 解析到 `analysis.novelty` 与 `analysis.highlight`。

- [ ] **Step 3: 改 prompt + 解析**（`src/radar/llm/scoring.py`）

```python
SYSTEM = (
    "你是 AI 技术情报分析助手，服务于一个 AI Lab 的技术选型。"
    "对给定条目输出结构化分析，只返回 JSON：\n"
    "{\n"
    '  "category": "model|tool_framework|paper|article|other",\n'
    '  "summary": "一句话中文摘要",\n'
    '  "highlight": "这周为何值得关注/有何新变化，没有则写\'无明显新进展\'",\n'
    '  "scores": {"practicality":1-5,"influence":1-5,"follow_cost":1-5,"novelty":1-5},\n'
    '  "boundary": {"good_for":"","not_good_for":"","risks":""}\n'
    "}\n"
    "评分务必拉开区分度、用满 1-5：novelty=新颖度/近期是否有实质进展，"
    "知名但陈旧的项目 novelty 应给低分（1-2）；practicality=能否真实工程试用；"
    "influence=社区/厂商关注度；follow_cost=跟进成本，分越高成本越低。"
)
```

解析处增 `novelty=_clamp(scores.get("novelty"))`、`highlight=r.get("highlight", "")`。

- [ ] **Step 4: `compute_quality` 纳入 novelty**（`src/radar/ranking.py`）

`Settings.weights` 增 `novelty` 权重；`compute_quality` 增 `+ w.get("novelty",0)*analysis.novelty`。`config/settings.yaml` 重新分配权重（示例）：

```yaml
  weights:
    practicality: 0.30
    influence: 0.20
    novelty: 0.20
    follow_cost: 0.15
    source_tier: 0.10
    freshness: 0.05
```

（用 `w.get` 读取，确保旧测试里无 novelty 权重的 `Settings` 不报错。）

- [ ] **Step 5: 报告呈现增量**（`src/radar/report.py`）— `ReportRow` 增 `weekly_growth:int=0`、`novelty:int=0`、`highlight:str=""`、`freshness_days` 可选；Top 条目模板增：

```python
                f"- 本周亮点：{r.highlight}",
                f"- 本周增长：+{r.weekly_growth}（star/下载）",
                f"- 新颖度：{r.novelty}/5",
```

`run_report`（`cli.py`）填充：`weekly_growth=repo.weekly_growth(item.raw_id, today)`、`novelty=a["novelty"]`、`highlight=a["highlight"]`。

> 注意：`a` 来自 `get_analysis_row`，需确认 `analyses` 表已存这两列。**因 Task 5 给 analyses 增了字段**，而旧库无该列——所以：要么本次改造后用全新库重跑（推荐），要么给 `save_analysis`/SCHEMA 增列。MVP 直接重跑新库，无需迁移。⚠️ 若给 `analyses` 表加列，必须用新库（旧 `radar.db` 删除重建）。

- [ ] **Step 6: 验证** `pytest tests/llm/test_scoring.py tests/test_report.py -v` + `pytest -q` 全绿。
- [ ] **Step 7: commit** `feat: add novelty scoring, weekly highlight, and delta in report`

---

## Task 6（可选）: 真聚类——跨源实体归并

**Files:** Modify `src/radar/pipeline/dedup.py`, `src/radar/pipeline/cluster.py`；Test `tests/pipeline/test_cluster.py`

**意图：** 让「相关报道」真正出现。GitHub `owner/repo`、HF `org/model`、RSS 标题里出现的同名实体应归为一个事件。

- [ ] **Step 1: 实体名提取**：从 url/title 提取规范名（如 `meta-llama/Llama-3.1-8B` → `llama-3.1-8b`），RSS 标题做包含匹配。
- [ ] **Step 2: 写测试**：HF 模型 + 提到该模型的 RSS 博客应聚为一簇，`related_urls` 非空。
- [ ] **Step 3: 实现**：`same_event` 增「实体名包含/相等」分支。
- [ ] **Step 4: 验证 + commit** `feat: cluster items by canonical entity across sources`

---

## 全局验收（改造完成的标准）

- [ ] `pytest -q` 全绿（应 ≥ 56，含新增测试）。
- [ ] 全新库重跑：`Remove-Item radar.db; radar collect; radar process; radar analyze; radar report --out report.md`
- [ ] 周报应满足：
  - 「建议跟进」≤ 8 且**不含**教程/awesome/书籍类
  - 出现「本周增长 +N」「本周亮点」「新颖度」字段
  - 含近期新建/上升的项目，而非清一色常青老库
  - 分数有明显区分度（不再全挤在 4.4–4.9）
- [ ] 更新 `docs/superpowers/plans/2026-06-08-radar-progress.md` 进度日志。

---

## 面试叙事（这次改造正是最好的素材）

可在面试中讲的完整闭环：

> 「MVP 跑通后第一份周报让我意识到一个根本问题：我做的是**存量排行**而非**增量情报**——推荐的全是高 star 的常青项目和教程，这些打开 GitHub Trending 就能看到，系统没有创造增量价值。情报的核心应该是**变化量**：这周新出现了什么、谁在快速上升、官方发布了什么。于是我做了四件事：①引入 star 周增长快照，把候选排序从绝对量改为 delta；②采集端从『历史最高星』改为『近期新建/活跃』；③在过滤层剔除教程/资源汇总类噪音；④给 LLM 评分加『新颖性』维度并要求拉开区分度。改完后周报从『榜单』变成了『本周值得关注的新动态』。」

这段话体现的是**产品 sense + 工程反思 + 闭环执行**，远强于「我做了个能跑的 pipeline」。

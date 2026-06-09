# AI 技术情报雷达 · 开发进度

> 最后更新：2026-06-08
> 工作目录：仓库根目录（`main` 分支，已弃用 worktree）
> 分支：`main`（已合并 `feature/radar-mvp`）
> 最新提交：`6afb4fe`（main）

---

## 一、当前状态总览

| 维度 | 状态 |
|------|------|
| MVP 代码 | ✅ 完成（Task 0–18） |
| 测试 | ✅ 56 passed |
| DeepSeek 配置 | ✅ 默认 `deepseek-v4-pro` |
| 精选改造（Top 8 + 分源配额） | ✅ 已提交 `f94f2e6` |
| feature/radar-mvp 合并到 main | ✅ 已合并 |
| 真实数据全量验证 | ✅ 完成（1966→1104→45→8推荐+36观察） |
| 飞书推送 | ✅ 已验证通过 |
| GitHub Secrets 配置 | ✅ `DEEPSEEK_API_KEY` / `GH_TOKEN` / `FEISHU_WEBHOOK_URL` |
| GitHub Actions 验证 | ⏳ 手动触发中，等待结果 |
| report.md 移除 git 跟踪 | ✅ 已加入 .gitignore |

---

## 二、已完成里程碑

### 阶段 A：MVP 落地（`ba567ac` → `6afc755`）

- Python 项目骨架、数据模型、配置、SQLite 仓储
- 三类采集器：GitHub / Hugging Face / RSS
- Pipeline：去重、聚类、过滤
- LLM 两阶段：预筛 + 维度评分（DeepSeek）
- 代码化综合评分 + Markdown 周报
- CLI：`collect` / `process` / `analyze` / `report` / `review` / `all`
- 回测脚手架 `backtest.evaluate()`
- 端到端冒烟测试

### 阶段 B：部署与配置（`eb1f28e` → `99963db`）

- 默认 LLM 切换为 DeepSeek `deepseek-v4-pro`
- `radar notify` 飞书 Webhook 推送
- `.github/workflows/radar-weekly.yml` 每周定时流水线
- 本地 `.env` 已配置 `DEEPSEEK_API_KEY`、`GITHUB_TOKEN`（用户自行维护，勿提交）

### 阶段 C：精选与均衡化（`f94f2e6`）

解决「33 条建议跟进太多 + RSS 几乎不参与分析」：

| 改动 | 说明 | 配置位置 |
|------|------|-----------|
| Top-N 精选 | 周报「建议跟进」最多 8 条，其余降级观察列表 | `ranking.max_recommendations: 8` |
| 分源配额 | 分析候选按源分配：GitHub 20 + HF 15 + RSS 15 | `analyze.quota` |
| GitHub 扩容 | `per_page` 50，新增 `topic:llm`、`topic:agent` 源 | `filter.github_per_page` + `sources.yaml` |
| `--no-quota` | 回退旧行为（单一 `--limit`） | CLI 参数 |

相关计划文档：[2026-06-08-radar-precision-tuning.md](./2026-06-08-radar-precision-tuning.md)

---

## 三、全量验证数据（新机器重跑）

方案 B 全量重来，结果如下：

| 指标 | 数值 |
|------|------|
| 采集条目 | 1966 |
| 去重聚类后 | 1104 |
| 已 LLM 分析 | **45**（GitHub 20 + HF 15 + RSS 10） |
| 周报「建议跟进」 | **8**（符合 Top 8 限制） |
| 周报「观察列表」 | 36 |
| 三源覆盖 | ✅ GitHub / HuggingFace / RSS 均有 |
| 飞书推送 | ✅ 已验证 |

> `radar.db` 在 `.gitignore` 中，不随 git 提交；换机器需重跑 `collect`。

---

## 四、续做清单

### 必做（完成雏形演示）

- [x] **Step 1**：新机器环境搭建，安装依赖
- [x] **Step 2**：全量重来（方案 B）`collect → process → analyze → report`
- [x] **Step 3**：验收周报（8 条推荐、三源覆盖、摘要/分数/边界齐全）

### 选做（上线自动化）

- [x] 飞书推送验证通过 `radar notify --out report.md`
- [x] `feature/radar-mvp` 合并到 `main`，推送远程
- [x] GitHub Secrets 配置：`DEEPSEEK_API_KEY`、`GH_TOKEN`、`FEISHU_WEBHOOK_URL`
- [ ] Actions 手动 `workflow_dispatch` 验证（已触发，等待结果）

### 可选优化（不阻塞演示）

- [ ] 调整数据源（加入中文源、arXiv 等）
- [x] 从 git 移除已跟踪的 `report.md`（生成物）
- [x] 主仓库 `main` 同步代码（已合并 feature/radar-mvp）

---

## 五、关键路径与命令速查

```text
工作目录  仓库根目录（main）
配置      config/settings.yaml  config/sources.yaml  .env
数据库    radar.db（本地，不提交）
输出      report.md
测试      pytest -q   # 期望 56 passed
```

```powershell
pip install -e ".[dev]"
radar collect
radar process
radar analyze          # 默认分源配额，非 --limit
radar report --out report.md
radar notify --out report.md   # 需 FEISHU_WEBHOOK_URL
radar all              # 一次跑完（analyze 仍用配额）
radar analyze --no-quota --limit 50   # 旧行为
```

---

## 六、Git 提交历史（近期）

```text
803f743 docs: update progress log with handoff commit ref
1f6f8da docs: add development progress handoff document
f94f2e6 feat: precision tuning with top-8 report, per-source quota, and expanded github collection
99963db feat: add analyze limit, feishu notify, and weekly github action
eb1f28e feat: switch default llm to deepseek-v4-pro
6afc755 feat: add backtest metrics for recommendation quality
5260c8b test: add end-to-end smoke test and usage docs
...
ba567ac chore: scaffold tech-intel-radar python project
```

工作区状态：**干净**（进度文档已落盘，见下方更新日志）。

---

## 七、已知问题与决策记录

| 问题 | 原因 | 已采取措施 |
|------|------|-----------|
| 首版周报 33 条「建议跟进」 | LLM 对高星 GitHub 普遍打高分 + 阈值偏低 | Top 8 精选 + 分源配额 |
| RSS 973 条几乎未分析 | 候选排序偏向 star/下载量 | `analyze.quota` 为 RSS 保留 15 名额 |
| 全量分析 1105 条不现实 | ~2000+ 次 LLM 调用 | 配额总量约 50 条/周 |
| `analyze` 中断可续跑 | `save_analysis` 为 upsert | 直接再跑 `radar analyze` 即可补全 |

---

## 八、相关文档索引

| 文档 | 用途 |
|------|------|
| [2026-06-08-tech-intel-radar-mvp.md](./2026-06-08-tech-intel-radar-mvp.md) | MVP 原始实现计划（已完成） |
| [2026-06-08-radar-precision-tuning.md](./2026-06-08-radar-precision-tuning.md) | 精选改造计划（已完成） |
| [../../AI技术情报雷达-方案设计.md](../../AI技术情报雷达-方案设计.md) | 方案设计交付物 |
| [../../reference/提交与面试准备规划.md](../../reference/提交与面试准备规划.md) | 面试与落地规划 |

---

## 九、进度更新日志

| 日期 | 内容 |
|------|------|
| 2026-06-08 | MVP 19 个 Task 全部实现，43→56 测试通过 |
| 2026-06-08 | 本地联调：collect 1846、DeepSeek API 验证通过 |
| 2026-06-08 | 精选改造 `f94f2e6` 完成；Task 5 重采 1966 条后 analyze 中断于 31/50 |
| 2026-06-08 | 进度文档创建并提交 `1f6f8da`，README 增加进度链接，暂停开发 |
| 2026-06-08 | 主仓库同步进度文档副本（`docs/superpowers/plans/`） |
| 2026-06-08 | 新机器：合并 feature/radar-mvp → main，全量验证通过（1966→1104→45→8推荐） |
| 2026-06-08 | 飞书推送验证通过，GitHub Secrets 配置完成，Actions 手动触发 |
| 2026-06-08 | 清理 `.worktrees/radar-mvp`，统一在 `main` 根目录开发 |

**下次更新时**：在「九、进度更新日志」追加一行，并修改文首「最后更新」日期与第三节数据库数字。

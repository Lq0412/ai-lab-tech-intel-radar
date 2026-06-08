# AI 技术情报雷达 · 开发进度

> 最后更新：2026-06-08  
> 工作目录：`C:\Users\EDY\Desktop\ai-lab-tech-intel-radar\.worktrees\radar-mvp`  
> 分支：`feature/radar-mvp`  
> 最新提交：`1f6f8da`

---

## 一、当前状态总览

| 维度 | 状态 |
|------|------|
| MVP 代码 | ✅ 完成（Task 0–18） |
| 测试 | ✅ 56 passed |
| DeepSeek 配置 | ✅ 默认 `deepseek-v4-pro` |
| 精选改造（Top 8 + 分源配额） | ✅ 已提交 `f94f2e6` |
| 飞书推送 + GitHub Actions | ✅ 代码就绪，待配置 Secrets |
| 真实数据全量验证（Task 5） | ⏸️ **进行中，已中断** |

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

## 三、中断时的现场数据（`radar.db`）

Task 5 真实验证跑了一半后手动中断：

| 指标 | 数值 |
|------|------|
| 采集条目 | 1945 |
| 去重后唯一条目 | 1105 |
| 已 LLM 分析 | **31**（目标配额约 50） |
| 已分析 · GitHub | 20 |
| 已分析 · Hugging Face | 11 |
| 已分析 · RSS | **0**（配额 15，尚未轮到或中断前未完成） |
| 周报 `report.md` | ❌ 未基于本次新数据重新生成 |

> `radar.db` 在 `.gitignore` 中，不随 git 提交；换机器需重跑 `collect`。

---

## 四、回家后续做清单

### 必做（完成雏形演示）

- [ ] **Step 1**：进入 worktree

```powershell
cd C:\Users\EDY\Desktop\ai-lab-tech-intel-radar\.worktrees\radar-mvp
```

- [ ] **Step 2**：续跑或重跑分析

```powershell
# 方案 A：接着分析（会 upsert 已分析条目，补全剩余配额）
radar analyze
radar report --out report.md

# 方案 B：全量重来（推荐，结果更干净）
Remove-Item radar.db
radar collect
radar process
radar analyze    # 约 15–20 分钟，~50 条配额
radar report --out report.md
```

- [ ] **Step 3**：验收周报

打开 `report.md`，确认：

- 「建议跟进」**≤ 8 项**
- Top 推荐含 GitHub 工具 / HF 模型
- 观察列表中有 RSS 官方博客条目（若 RSS 配额分析完成）
- 条目有摘要、综合分、能力边界

### 选做（上线自动化）

- [ ] `.env` 填入 `FEISHU_WEBHOOK_URL`，测试 `radar notify --out report.md`
- [ ] `git push -u origin feature/radar-mvp`，创建 PR 合并 `main`
- [ ] GitHub 仓库 Secrets：`DEEPSEEK_API_KEY`、`GITHUB_TOKEN`、`FEISHU_WEBHOOK_URL`
- [ ] Actions 页手动 `workflow_dispatch` 触发一次验证

### 可选优化（不阻塞演示）

- [ ] 若「建议跟进」仍偏多：调高 `tool_framework` 阈值（如 3.8 → 4.0）
- [ ] 从 git 移除已跟踪的 `report.md`（生成物）
- [ ] 主仓库 `main` 同步 worktree 代码（当前 main 仅有文档）

---

## 五、关键路径与命令速查

```text
工作目录  .worktrees/radar-mvp
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
1f6f8da docs: add development progress handoff document
f94f2e6 feat: precision tuning with top-8 report, per-source quota, and expanded github collection
99963db feat: add analyze limit, feishu notify, and weekly github action
eb1f28e feat: switch default llm to deepseek-v4-pro
6afc755 feat: add backtest metrics for recommendation quality
5260c8b test: add end-to-end smoke test and usage docs
...
ba567ac chore: scaffold tech-intel-radar python project
```

工作区状态：**干净**（`1f6f8da` 之后无未提交改动）。

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

**下次更新时**：在「九、进度更新日志」追加一行，并修改文首「最后更新」日期与第三节数据库数字。

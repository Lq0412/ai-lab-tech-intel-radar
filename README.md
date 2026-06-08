# AI 技术情报雷达

为 AI Lab 设计的技术情报 MVP 方案：持续扫描 AI 社区动态，评测工程价值与能力边界，输出可审核的决策周报。

## 文档目录

| 文档 | 说明 |
| --- | --- |
| [方案设计](docs/AI技术情报雷达-方案设计.md) | 正式交付物：质疑与假设、架构设计、关键决策、LLM 使用说明 |
| [架构图](docs/assets/architecture.png) | 系统架构示意图 |

## 参考材料

| 文档 | 说明 |
| --- | --- |
| [笔试题目](docs/reference/笔试题目.md) | 原始招聘任务描述与交付要求 |
| [提交与面试准备规划](docs/reference/提交与面试准备规划.md) | 提交前检查清单、面试准备与 4 周落地规划 |
| [参考：AIHOT 产品思路](docs/reference/参考-AIHOT产品思路.md) | 卡兹克 AIHOT 产品的信源分级与精选机制参考 |

## 项目结构

```text
.
├── README.md
└── docs/
    ├── AI技术情报雷达-方案设计.md   # 主文档
    ├── assets/
    │   └── architecture.png         # 架构图
    └── reference/                   # 参考与过程文档
        ├── 笔试题目.md
        ├── 提交与面试准备规划.md
        └── 参考-AIHOT产品思路.md
```

## 方案摘要

- **定位**：人机协同的技术情报降噪工具，而非全自动决策系统
- **信息源**：GitHub、Hugging Face、RSS（首版收敛）
- **输出**：Markdown 周报 + 人工审核
- **架构**：固定 Pipeline，非 Agent 主链路
- **落地周期**：4 周 MVP，1-2 人可交付

## 运行方式（MVP）

```bash
pip install -e ".[dev]"
cp .env.example .env   # 填入 DEEPSEEK_API_KEY / GITHUB_TOKEN

radar collect   # 采集三类信源入库
radar process   # 去重、聚类、过滤
radar analyze --limit 50   # LLM 分析 Top 50 候选（默认 50）
radar report --out report.md   # 生成 Markdown 周报
radar notify --out report.md   # 推送到飞书机器人（需 FEISHU_WEBHOOK_URL）
radar review --item-id 1 --verdict 推荐正确 --note "已安排复现"
# 或一次跑完：radar all

GitHub Actions 需在仓库 Secrets 配置：`DEEPSEEK_API_KEY`、`GITHUB_TOKEN`、（可选）`FEISHU_WEBHOOK_URL`。
```

测试：`pytest`

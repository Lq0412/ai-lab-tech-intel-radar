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

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


def test_render_report_caps_recommendations():
    rows = [row(f"工具{i}", "建议跟进", score=4.9 - i * 0.1) for i in range(12)]
    md = render_report(rows, week="2026-W23", max_recommendations=8)
    assert "建议跟进：8 项" in md
    assert "保持观察：4 项" in md
    assert "### 9." not in md


def test_render_report_no_cap_keeps_all():
    rows = [row(f"工具{i}", "建议跟进", score=4.5) for i in range(10)]
    md = render_report(rows, week="2026-W23")
    assert "建议跟进：10 项" in md


def test_render_report_shows_delta_fields():
    r = ReportRow(
        title="acme/new-agent", recommendation="建议跟进", quality_score=4.2,
        category="tool_framework", source_tier="T1.5",
        summary="新兴 Agent 框架", good_for="原型", not_good_for="生产",
        risks="早期", url="https://github.com/acme/new-agent",
        highlight="本周 star 突破 1000", weekly_growth=420, novelty=5,
    )
    md = render_report([r], week="2026-W24")
    assert "本周亮点：本周 star 突破 1000" in md
    assert "本周增长：+420" in md
    assert "新颖度：5/5" in md

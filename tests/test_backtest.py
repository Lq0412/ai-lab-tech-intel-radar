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

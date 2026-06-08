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

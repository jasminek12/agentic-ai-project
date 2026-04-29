import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def _by_run_average(rows: list[dict[str, str]], metric_field: str) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for row in rows:
        run = row.get("run_label", "").strip().lower() or "unknown"
        buckets.setdefault(run, []).append(_to_float(row.get(metric_field, "0")))
    return {
        run: round(sum(values) / len(values), 2) if values else 0.0
        for run, values in buckets.items()
    }


def _write_summary(path: Path, headers: list[str], row: list[object]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerow(row)


def correctness_summary() -> dict[str, float]:
    rows = _read_rows(ROOT / "correctness-benchmark" / "benchmark_questions.csv")
    total = len(rows)
    correct = sum(1 for r in rows if _to_float(r.get("correctness_score", "0")) >= 1.0)
    overall = _safe_pct(correct, total)
    by_run = _by_run_average(rows, "correctness_score")
    baseline = round(by_run.get("baseline", 0.0) * 100.0, 2)
    improved = round(by_run.get("improved", 0.0) * 100.0, 2)
    delta = round(improved - baseline, 2)

    _write_summary(
        ROOT / "correctness-benchmark" / "summary.csv",
        [
            "total_rows",
            "correct_rows",
            "correctness_pct",
            "baseline_correctness_pct",
            "improved_correctness_pct",
            "delta_pct_points",
        ],
        [total, correct, overall, baseline, improved, delta],
    )
    return {
        "overall": overall,
        "baseline": baseline,
        "improved": improved,
        "delta": delta,
    }


def clarity_summary() -> dict[str, float]:
    rows = _read_rows(ROOT / "clarity-structure-review" / "scored_responses.csv")
    total = len(rows)
    avg_by_run = _by_run_average(rows, "overall_clarity_score")
    baseline = avg_by_run.get("baseline", 0.0)
    improved = avg_by_run.get("improved", 0.0)
    meets = sum(1 for r in rows if r.get("meets_minimum_standard", "").strip().lower() == "yes")
    meets_pct = _safe_pct(meets, total)
    delta = round(improved - baseline, 2)

    _write_summary(
        ROOT / "clarity-structure-review" / "summary.csv",
        [
            "total_rows",
            "avg_clarity_baseline",
            "avg_clarity_improved",
            "delta_points",
            "meets_minimum_standard_pct",
        ],
        [total, baseline, improved, delta, meets_pct],
    )
    return {
        "baseline": baseline,
        "improved": improved,
        "delta": delta,
        "meets_pct": meets_pct,
    }


def depth_summary() -> dict[str, float]:
    rows = _read_rows(ROOT / "depth-analysis" / "scored_depth.csv")
    total = len(rows)
    avg_by_run = _by_run_average(rows, "depth_score_1_to_5")
    baseline = avg_by_run.get("baseline", 0.0)
    improved = avg_by_run.get("improved", 0.0)
    delta = round(improved - baseline, 2)

    reasoning_rate = _safe_pct(
        sum(1 for r in rows if _to_float(r.get("gives_reasoning", "0")) >= 1.0),
        total,
    )
    examples_rate = _safe_pct(
        sum(1 for r in rows if _to_float(r.get("includes_examples", "0")) >= 1.0),
        total,
    )
    tradeoffs_rate = _safe_pct(
        sum(1 for r in rows if _to_float(r.get("includes_tradeoffs", "0")) >= 1.0),
        total,
    )

    _write_summary(
        ROOT / "depth-analysis" / "summary.csv",
        [
            "total_rows",
            "avg_depth_baseline",
            "avg_depth_improved",
            "delta_points",
            "reasoning_present_pct",
            "examples_present_pct",
            "tradeoffs_present_pct",
        ],
        [total, baseline, improved, delta, reasoning_rate, examples_rate, tradeoffs_rate],
    )
    return {
        "baseline": baseline,
        "improved": improved,
        "delta": delta,
    }


def relevance_summary() -> dict[str, float]:
    rows = _read_rows(ROOT / "relevance-alignment" / "jd_alignment.csv")
    avg_relevance_by_run = _by_run_average(rows, "relevance_score_1_to_5")
    avg_keyword_by_run = _by_run_average(rows, "keyword_coverage_pct")
    rel_baseline = avg_relevance_by_run.get("baseline", 0.0)
    rel_improved = avg_relevance_by_run.get("improved", 0.0)
    key_baseline = avg_keyword_by_run.get("baseline", 0.0)
    key_improved = avg_keyword_by_run.get("improved", 0.0)

    _write_summary(
        ROOT / "relevance-alignment" / "summary.csv",
        [
            "avg_relevance_baseline",
            "avg_relevance_improved",
            "relevance_delta_points",
            "avg_keyword_coverage_baseline",
            "avg_keyword_coverage_improved",
            "keyword_coverage_delta_points",
        ],
        [
            rel_baseline,
            rel_improved,
            round(rel_improved - rel_baseline, 2),
            key_baseline,
            key_improved,
            round(key_improved - key_baseline, 2),
        ],
    )
    return {
        "relevance_baseline": rel_baseline,
        "relevance_improved": rel_improved,
        "keyword_baseline": key_baseline,
        "keyword_improved": key_improved,
    }


def write_overall_report(
    correctness: dict[str, float],
    clarity: dict[str, float],
    depth: dict[str, float],
    relevance: dict[str, float],
) -> None:
    lines = [
        "# Overall Evaluation Summary",
        "",
        "## Correctness",
        f"- Baseline: {correctness['baseline']}%",
        f"- Improved: {correctness['improved']}%",
        f"- Delta: {correctness['delta']} percentage points",
        "",
        "## Clarity and Structure",
        f"- Baseline avg (1-5): {clarity['baseline']}",
        f"- Improved avg (1-5): {clarity['improved']}",
        f"- Delta: {clarity['delta']} points",
        f"- Responses meeting minimum standard: {clarity['meets_pct']}%",
        "",
        "## Depth",
        f"- Baseline avg (1-5): {depth['baseline']}",
        f"- Improved avg (1-5): {depth['improved']}",
        f"- Delta: {depth['delta']} points",
        "",
        "## Relevance",
        f"- Relevance baseline (1-5): {relevance['relevance_baseline']}",
        f"- Relevance improved (1-5): {relevance['relevance_improved']}",
        f"- Keyword coverage baseline (%): {relevance['keyword_baseline']}",
        f"- Keyword coverage improved (%): {relevance['keyword_improved']}",
        "",
    ]
    (ROOT / "overall_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    correctness = correctness_summary()
    clarity = clarity_summary()
    depth = depth_summary()
    relevance = relevance_summary()
    write_overall_report(correctness, clarity, depth, relevance)
    print("Evaluation summaries generated in the evaluation folder.")


if __name__ == "__main__":
    main()

import csv
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT.parent / "job-agent-backend" / "storage" / "raw-evaluation-data"
RAW_DATASET = RAW_DIR / "evaluation_dataset.csv"
RAW_RESULTS = RAW_DIR / "evaluation_results.csv"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _normalize_1_to_5(score_0_100: float) -> float:
    normalized = score_0_100 / 20.0
    return round(max(1.0, min(5.0, normalized)), 2)


def _derive_run_labels(dataset_rows: list[dict[str, str]], results_rows: list[dict[str, str]]) -> dict[str, str]:
    ordered_sessions: list[str] = []
    seen: set[str] = set()

    for row in results_rows + dataset_rows:
        session_id = (row.get("session_id") or "").strip()
        if session_id and session_id not in seen:
            ordered_sessions.append(session_id)
            seen.add(session_id)

    if not ordered_sessions:
        return {}

    cutoff = max(1, len(ordered_sessions) // 2)
    labels: dict[str, str] = {}
    for idx, session_id in enumerate(ordered_sessions):
        labels[session_id] = "baseline" if idx < cutoff else "improved"
    return labels


def _keyword_seed(text: str, limit: int = 8) -> str:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_+\-/#\.]*", (text or "").lower())
    stop = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "you",
        "your",
        "role",
        "work",
        "team",
        "years",
        "year",
        "experience",
        "required",
        "preferred",
        "about",
        "join",
        "our",
        "are",
    }
    selected: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if len(token) < 4 or token in stop or token in seen:
            continue
        selected.append(token)
        seen.add(token)
        if len(selected) >= limit:
            break
    return ";".join(selected)


def _write_csv(path: Path, headers: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)


def build_correctness(dataset_rows: list[dict[str, str]], run_labels: dict[str, str]) -> None:
    out_rows: list[list[Any]] = []
    for idx, row in enumerate(dataset_rows, start=1):
        question = (row.get("question") or "").strip()
        answer = (row.get("answer") or "").strip()
        if not question or not answer:
            continue
        score = _to_float(row.get("correctness_score"))
        binary_score = 1 if score >= 70 else 0
        label = "correct" if score >= 70 else ("partially_correct" if score >= 40 else "incorrect")
        run_label = run_labels.get((row.get("session_id") or "").strip(), "baseline")
        out_rows.append(
            [
                f"q{idx}",
                question,
                "",  # ground truth can be manually filled later
                "from_raw_data",
                "from_raw_data",
                run_label,
                answer,
                label,
                binary_score,
            ]
        )

    _write_csv(
        ROOT / "correctness-benchmark" / "benchmark_questions.csv",
        [
            "question_id",
            "question",
            "ground_truth_answer",
            "model_version",
            "prompt_version",
            "run_label",
            "model_answer",
            "correctness_label",
            "correctness_score",
        ],
        out_rows,
    )


def build_clarity(dataset_rows: list[dict[str, str]], run_labels: dict[str, str]) -> None:
    out_rows: list[list[Any]] = []
    for idx, row in enumerate(dataset_rows, start=1):
        question = (row.get("question") or "").strip()
        if not question:
            continue
        clarity_100 = _to_float(row.get("clarity_score"))
        clarity_5 = _normalize_1_to_5(clarity_100)
        run_label = run_labels.get((row.get("session_id") or "").strip(), "baseline")
        meets = "yes" if clarity_5 >= 3.5 else "no"
        out_rows.append(
            [
                f"r{idx}",
                question,
                run_label,
                "reviewer_auto",
                clarity_5,
                clarity_5,
                clarity_5,
                clarity_5,
                meets,
                "Auto-seeded from raw clarity_score.",
            ]
        )

    _write_csv(
        ROOT / "clarity-structure-review" / "scored_responses.csv",
        [
            "response_id",
            "question",
            "run_label",
            "reviewer_id",
            "logical_flow_score",
            "readability_score",
            "formatting_consistency_score",
            "overall_clarity_score",
            "meets_minimum_standard",
            "notes",
        ],
        out_rows,
    )


def build_depth(dataset_rows: list[dict[str, str]], run_labels: dict[str, str]) -> None:
    out_rows: list[list[Any]] = []
    for idx, row in enumerate(dataset_rows, start=1):
        question = (row.get("question") or "").strip()
        answer = (row.get("answer") or "").lower()
        if not question or not answer:
            continue

        depth_100 = _to_float(row.get("depth_score"))
        depth_5 = _normalize_1_to_5(depth_100)
        run_label = run_labels.get((row.get("session_id") or "").strip(), "baseline")

        gives_reasoning = 1 if ("because" in answer or "therefore" in answer or "so that" in answer) else 0
        includes_examples = 1 if ("for example" in answer or "e.g." in answer or "example" in answer) else 0
        includes_tradeoffs = 1 if ("trade-off" in answer or "however" in answer or "alternative" in answer) else 0

        out_rows.append(
            [
                f"d{idx}",
                question,
                run_label,
                gives_reasoning,
                includes_examples,
                includes_tradeoffs,
                depth_5,
                "Auto-seeded from raw depth_score + answer heuristics.",
            ]
        )

    _write_csv(
        ROOT / "depth-analysis" / "scored_depth.csv",
        [
            "response_id",
            "question",
            "run_label",
            "gives_reasoning",
            "includes_examples",
            "includes_tradeoffs",
            "depth_score_1_to_5",
            "notes",
        ],
        out_rows,
    )


def build_relevance(dataset_rows: list[dict[str, str]], run_labels: dict[str, str]) -> None:
    out_rows: list[list[Any]] = []
    for idx, row in enumerate(dataset_rows, start=1):
        question = (row.get("question") or "").strip()
        response_text = (row.get("answer") or "").strip()
        jd = (row.get("job_description") or "").strip()
        if not question or not response_text:
            continue
        run_label = run_labels.get((row.get("session_id") or "").strip(), "baseline")
        relevance_100 = _to_float(row.get("relevance_score"))
        out_rows.append(
            [
                f"rel{idx}",
                (row.get("mode") or "Target Role").strip().title(),
                _keyword_seed(jd),
                question,
                run_label,
                response_text,
                _normalize_1_to_5(relevance_100),
                round(max(0.0, min(100.0, relevance_100)), 2),
                "Auto-seeded from raw relevance_score and job description text.",
            ]
        )

    _write_csv(
        ROOT / "relevance-alignment" / "jd_alignment.csv",
        [
            "response_id",
            "job_role",
            "job_description_keywords",
            "question",
            "run_label",
            "response_text",
            "relevance_score_1_to_5",
            "keyword_coverage_pct",
            "notes",
        ],
        out_rows,
    )


def main() -> None:
    dataset_rows = _read_csv(RAW_DATASET)
    results_rows = _read_csv(RAW_RESULTS)
    if not dataset_rows:
        raise SystemExit(f"No dataset rows found at: {RAW_DATASET}")

    run_labels = _derive_run_labels(dataset_rows, results_rows)
    build_correctness(dataset_rows, run_labels)
    build_clarity(dataset_rows, run_labels)
    build_depth(dataset_rows, run_labels)
    build_relevance(dataset_rows, run_labels)
    print("Seeded evaluation CSVs from raw-evaluation-data.")


if __name__ == "__main__":
    main()

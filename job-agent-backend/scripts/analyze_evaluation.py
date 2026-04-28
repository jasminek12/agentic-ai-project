import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_DIR = REPO_ROOT / "job-agent-backend" / "storage" / "evaluation"
DATASET_PATH = EVALUATION_DIR / "evaluation_dataset.jsonl"
RESULTS_PATH = EVALUATION_DIR / "evaluation_results.json"


def _load_dataset_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    rows.append(parsed)
            except json.JSONDecodeError:
                continue
    return rows


def _load_result_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(parsed, list):
            return [row for row in parsed if isinstance(row, dict)]
    except json.JSONDecodeError:
        return []
    return []


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _print_header(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def analyze() -> None:
    dataset_rows = _load_dataset_rows(DATASET_PATH)
    result_rows = _load_result_rows(RESULTS_PATH)

    _print_header("Overview")
    print(f"Dataset path: {DATASET_PATH}")
    print(f"Results path: {RESULTS_PATH}")
    print(f"Turn rows: {len(dataset_rows)}")
    print(f"Completed sessions: {len(result_rows)}")

    turn_scores = [float(row["score"]) for row in dataset_rows if isinstance(row.get("score"), int)]
    _print_header("Turn-Level Metrics")
    print(f"Average turn score: {_mean(turn_scores)}")
    relevance_scores = [float(row["relevance_score"]) for row in dataset_rows if isinstance(row.get("relevance_score"), (int, float))]
    correctness_scores = [float(row["correctness_score"]) for row in dataset_rows if isinstance(row.get("correctness_score"), (int, float))]
    clarity_scores = [float(row["clarity_score"]) for row in dataset_rows if isinstance(row.get("clarity_score"), (int, float))]
    depth_scores = [float(row["depth_score"]) for row in dataset_rows if isinstance(row.get("depth_score"), (int, float))]
    confidence_scores = [float(row["confidence_score"]) for row in dataset_rows if isinstance(row.get("confidence_score"), (int, float))]
    technical_accuracy_scores = [
        float(row["technical_accuracy_pct"])
        for row in dataset_rows
        if isinstance(row.get("technical_accuracy_pct"), (int, float)) and float(row.get("technical_accuracy_pct", 0.0)) > 0
    ]
    star_scores = [
        float(row["star_format_usage_pct"])
        for row in dataset_rows
        if isinstance(row.get("star_format_usage_pct"), (int, float)) and float(row.get("star_format_usage_pct", 0.0)) > 0
    ]
    response_times = [
        float(row["response_time_seconds"])
        for row in dataset_rows
        if isinstance(row.get("response_time_seconds"), (int, float))
    ]
    print(f"Average relevance score: {_mean(relevance_scores)}")
    print(f"Average correctness score: {_mean(correctness_scores)}")
    print(f"Average clarity score: {_mean(clarity_scores)}")
    print(f"Average depth score: {_mean(depth_scores)}")
    print(f"Average confidence score (0-1): {_mean(confidence_scores)}")
    print(f"Average technical accuracy %: {_mean(technical_accuracy_scores)}")
    print(f"Average STAR usage % (behavioral): {_mean(star_scores)}")
    print(f"Average response time (seconds): {_mean(response_times)}")

    mode_scores: dict[str, list[float]] = defaultdict(list)
    for row in dataset_rows:
        mode = str(row.get("mode", "unknown")).strip() or "unknown"
        score = row.get("score")
        if isinstance(score, int):
            mode_scores[mode].append(float(score))

    if mode_scores:
        print("Average turn score by mode:")
        for mode in sorted(mode_scores):
            print(f"  - {mode}: {_mean(mode_scores[mode])}")
    else:
        print("Average turn score by mode: None")

    weak_topic_counter: Counter[str] = Counter()
    for row in dataset_rows:
        weak_topics = row.get("weak_topics", [])
        if isinstance(weak_topics, list):
            for topic in weak_topics:
                if isinstance(topic, str) and topic.strip():
                    weak_topic_counter.update([topic.strip()])

    print("Top weak topics:")
    if weak_topic_counter:
        for topic, count in weak_topic_counter.most_common(10):
            print(f"  - {topic}: {count}")
    else:
        print("  - None")

    _print_header("Session-Level Metrics")
    session_scores = [
        float(row["average_score"])
        for row in result_rows
        if isinstance(row.get("average_score"), (int, float))
    ]
    print(f"Average completed-session score: {_mean(session_scores)}")
    skill_overlap_scores = [
        float(row["skill_overlap_pct"])
        for row in result_rows
        if isinstance(row.get("skill_overlap_pct"), (int, float))
    ]
    keyword_match_scores = [
        float(row["keyword_match_score"])
        for row in result_rows
        if isinstance(row.get("keyword_match_score"), (int, float))
    ]
    experience_alignment_scores = [
        float(row["experience_alignment_score"])
        for row in result_rows
        if isinstance(row.get("experience_alignment_score"), (int, float))
    ]
    ats_scores = [
        float(row["ats_style_score"])
        for row in result_rows
        if isinstance(row.get("ats_style_score"), (int, float))
    ]
    latency_scores = [
        float(row["latency_ms_avg"])
        for row in result_rows
        if isinstance(row.get("latency_ms_avg"), (int, float))
    ]
    consistency_scores = [
        float(row["consistency_score"])
        for row in result_rows
        if isinstance(row.get("consistency_score"), (int, float))
    ]
    drift_scores = [
        float(row["drift_score"])
        for row in result_rows
        if isinstance(row.get("drift_score"), (int, float))
    ]
    print(f"Average skill overlap %: {_mean(skill_overlap_scores)}")
    print(f"Average keyword match score: {_mean(keyword_match_scores)}")
    print(f"Average experience alignment score: {_mean(experience_alignment_scores)}")
    print(f"Average ATS-style score: {_mean(ats_scores)}")
    print(f"Average evaluation latency (ms): {_mean(latency_scores)}")
    print(f"Average consistency score: {_mean(consistency_scores)}")
    print(f"Average drift score: {_mean(drift_scores)}")

    buckets = {"low(<6)": 0, "mid(6-7.9)": 0, "high(>=8)": 0}
    for score in session_scores:
        if score < 6:
            buckets["low(<6)"] += 1
        elif score < 8:
            buckets["mid(6-7.9)"] += 1
        else:
            buckets["high(>=8)"] += 1
    print("Score buckets:")
    for label, count in buckets.items():
        print(f"  - {label}: {count}")

    action_counter: Counter[str] = Counter()
    for row in result_rows:
        actions = row.get("debrief_actions", [])
        if isinstance(actions, list):
            for action in actions:
                if isinstance(action, str) and action.strip():
                    action_counter.update([action.strip()])

    print("Most common debrief actions:")
    if action_counter:
        for action, count in action_counter.most_common(10):
            print(f"  - {action}: {count}")
    else:
        print("  - None")


if __name__ == "__main__":
    analyze()

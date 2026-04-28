import json
import re
from statistics import pstdev
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
STORAGE_DIR = REPO_ROOT / "job-agent-backend" / "storage"
EVALUATION_DIR = STORAGE_DIR / "evaluation"
DATASET_PATH = EVALUATION_DIR / "evaluation_dataset.jsonl"
RESULTS_PATH = EVALUATION_DIR / "evaluation_results.json"


def _tokenize_text(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9_+\-/\.#]*", text.lower())


def _keyword_set(text: str) -> set[str]:
    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "your",
        "have",
        "will",
        "you",
        "about",
        "role",
        "work",
        "team",
        "years",
        "year",
        "experience",
        "required",
        "preferred",
        "ability",
    }
    return {tok for tok in _tokenize_text(text) if len(tok) >= 3 and tok not in stop_words}


def _bounded_percentage(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _fallback_answer_metrics(question: str, answer: str, score: int | None, mode: str) -> dict[str, float | int]:
    qk = _keyword_set(question)
    ak = _keyword_set(answer)
    overlap = len(qk & ak)
    relevance = _bounded_percentage((overlap / len(qk) * 100.0) if qk else 0.0)
    safe_score = score if isinstance(score, int) else 0
    correctness = _bounded_percentage(safe_score * 10.0 if mode != "technical" else safe_score * 9.5 + (5.0 if safe_score >= 6 else 0.0))
    clarity = _bounded_percentage(min(100.0, max(20.0, safe_score * 10 + 10)))
    depth = _bounded_percentage(min(100.0, 15.0 + (len(answer.split()) / 2.0)))
    confidence = round(safe_score / 10.0, 3)
    technical_accuracy_pct = correctness if mode == "technical" else 0.0
    return {
        "relevance_score": relevance,
        "correctness_score": correctness,
        "clarity_score": clarity,
        "depth_score": depth,
        "confidence_score": confidence,
        "technical_accuracy_pct": technical_accuracy_pct,
        "star_format_usage_pct": 0.0,
        "answer_length_words": len(answer.split()),
        "response_time_seconds": float(max(5, len(answer.split()) // 3)),
        "evaluation_latency_ms": 0.0,
    }


def _fallback_resume_job_match(resume: str, job_description: str) -> dict[str, float]:
    resume_keywords = _keyword_set(resume)
    job_keywords = _keyword_set(job_description)
    overlap = resume_keywords & job_keywords
    skill_overlap_pct = (len(overlap) / len(job_keywords) * 100.0) if job_keywords else 0.0
    keyword_match_score = skill_overlap_pct
    experience_match = re.search(r"(\d+)\+?\s*(?:years|year|yrs|yr)", resume.lower())
    has_experience_signal = 1.0 if experience_match else 0.0
    role_alignment_terms = ["engineer", "developer", "analyst", "manager", "scientist", "intern"]
    role_overlap = 1.0 if any(t in resume.lower() and t in job_description.lower() for t in role_alignment_terms) else 0.0
    experience_alignment_score = _bounded_percentage((0.65 * has_experience_signal + 0.35 * role_overlap) * 100.0)
    ats_style_score = _bounded_percentage((0.7 * keyword_match_score) + (0.3 * experience_alignment_score))
    return {
        "skill_overlap_pct": _bounded_percentage(skill_overlap_pct),
        "keyword_match_score": _bounded_percentage(keyword_match_score),
        "experience_alignment_score": experience_alignment_score,
        "ats_style_score": ats_style_score,
    }


def _load_session(memory_path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(memory_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
        return raw
    except (OSError, json.JSONDecodeError):
        return None


def _build_dataset_rows(session_id: str, memory: dict[str, Any]) -> list[dict[str, Any]]:
    mode = str(memory.get("mode", ""))
    job_description = str(memory.get("job_description", ""))
    resume = str(memory.get("resume", ""))
    completed_at = str(memory.get("completed_at", ""))
    rows: list[dict[str, Any]] = []
    history = memory.get("history", [])
    if not isinstance(history, list):
        return rows
    for idx, item in enumerate(history, start=1):
        if not isinstance(item, dict):
            continue
        answer = str(item.get("answer", "")).strip()
        question = str(item.get("question", "")).strip()
        if not question or not answer:
            continue
        score = item.get("score")
        fallback_metrics = _fallback_answer_metrics(question, answer, score if isinstance(score, int) else None, mode)
        rows.append(
            {
                "session_id": session_id,
                "mode": mode,
                "completed_at": completed_at,
                "turn_index": idx,
                "question": question,
                "answer": answer,
                "score": score if isinstance(score, int) else None,
                "feedback": str(item.get("feedback", "")),
                "critique": str(item.get("critique", "")),
                "rewrite": str(item.get("rewrite", "")),
                "weak_topics": item.get("weak_topics", []),
                "relevance_score": item.get("relevance_score", fallback_metrics["relevance_score"]),
                "correctness_score": item.get("correctness_score", fallback_metrics["correctness_score"]),
                "clarity_score": item.get("clarity_score", fallback_metrics["clarity_score"]),
                "depth_score": item.get("depth_score", fallback_metrics["depth_score"]),
                "confidence_score": item.get("confidence_score", fallback_metrics["confidence_score"]),
                "technical_accuracy_pct": item.get("technical_accuracy_pct", fallback_metrics["technical_accuracy_pct"]),
                "star_format_usage_pct": item.get("star_format_usage_pct", fallback_metrics["star_format_usage_pct"]),
                "answer_length_words": item.get("answer_length_words", fallback_metrics["answer_length_words"]),
                "response_time_seconds": item.get("response_time_seconds", fallback_metrics["response_time_seconds"]),
                "evaluation_latency_ms": item.get("evaluation_latency_ms", fallback_metrics["evaluation_latency_ms"]),
                "job_description": job_description,
                "resume": resume,
            }
        )
    return rows


def _build_result_row(session_id: str, memory: dict[str, Any]) -> dict[str, Any]:
    scores: list[int] = []
    history = memory.get("history", [])
    if isinstance(history, list):
        for item in history:
            if isinstance(item, dict) and isinstance(item.get("score"), int):
                scores.append(int(item["score"]))

    avg_score = round(sum(scores) / len(scores), 2) if scores else None
    resume_job_match = memory.get("resume_job_match", _fallback_resume_job_match(str(memory.get("resume", "")), str(memory.get("job_description", ""))))
    system_metrics = memory.get("system_metrics", {})
    if not isinstance(system_metrics, dict):
        system_metrics = {}
    fallback_drift_risks = []
    if isinstance(history, list):
        for item in history:
            if isinstance(item, dict):
                if isinstance(item.get("drift_risk_score"), (int, float)):
                    fallback_drift_risks.append(float(item["drift_risk_score"]))
                elif isinstance(item.get("weak_topics"), list):
                    fallback_drift_risks.append(_bounded_percentage(len(item.get("weak_topics", [])) * 8.0))
    fallback_consistency = _bounded_percentage(max(0.0, 100.0 - (pstdev(scores) * 12.0))) if len(scores) > 1 else 100.0
    fallback_drift = _bounded_percentage(sum(fallback_drift_risks) / len(fallback_drift_risks)) if fallback_drift_risks else 0.0
    return {
        "session_id": session_id,
        "mode": str(memory.get("mode", "")),
        "interview_complete": bool(memory.get("interview_complete", False)),
        "answered_count": int(memory.get("answered_count", 0)),
        "target_question_count": int(memory.get("target_question_count", 0)),
        "average_score": avg_score,
        "weak_topic_memory": memory.get("weak_topic_memory", []),
        "final_evaluation": str(memory.get("final_evaluation", "")),
        "debrief_actions": memory.get("debrief_actions", []),
        "next_round_target": str(memory.get("next_round_target", "")),
        "curriculum_plan": memory.get("curriculum_plan", []),
        "skill_overlap_pct": float(resume_job_match.get("skill_overlap_pct", 0.0)),
        "keyword_match_score": float(resume_job_match.get("keyword_match_score", 0.0)),
        "experience_alignment_score": float(resume_job_match.get("experience_alignment_score", 0.0)),
        "ats_style_score": float(resume_job_match.get("ats_style_score", 0.0)),
        "latency_ms_avg": float(system_metrics.get("latency_ms_avg", 0.0)),
        "consistency_score": float(system_metrics.get("consistency_score", fallback_consistency)),
        "drift_score": float(system_metrics.get("drift_score", fallback_drift)),
        "completed_at": str(memory.get("completed_at", "")),
    }


def export_artifacts() -> None:
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    dataset_rows: list[dict[str, Any]] = []
    results_rows: list[dict[str, Any]] = []

    session_files = sorted(STORAGE_DIR.glob("memory_*.json"), key=lambda p: p.name.lower())
    for memory_path in session_files:
        session_id = memory_path.stem.replace("memory_", "", 1)
        memory = _load_session(memory_path)
        if memory is None:
            continue
        dataset_rows.extend(_build_dataset_rows(session_id, memory))
        if bool(memory.get("interview_complete", False)):
            results_rows.append(_build_result_row(session_id, memory))

    with DATASET_PATH.open("w", encoding="utf-8") as dataset_file:
        for row in dataset_rows:
            dataset_file.write(json.dumps(row, ensure_ascii=False) + "\n")

    RESULTS_PATH.write_text(json.dumps(results_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(dataset_rows)} dataset rows to {DATASET_PATH}")
    print(f"Wrote {len(results_rows)} result rows to {RESULTS_PATH}")


if __name__ == "__main__":
    export_artifacts()

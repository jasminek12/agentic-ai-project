from __future__ import annotations

from typing import Any

from interview_helper.llm_client import chat_completion, model_for
from interview_helper.models import EvaluationResult, RoundQaItem
from interview_helper.parse_json import extract_json_array, extract_json_object
from interview_helper.prompts import (
    answer_key_system,
    answer_key_user,
    coach_system,
    coach_user,
    coding_assistant_system,
    coding_assistant_user,
    critic_system,
    critic_user,
    evaluator_system,
    evaluator_system_clarity,
    evaluator_system_strict,
    evaluator_user,
    interviewer_system,
    interviewer_user,
    reflection_system,
    reflection_user,
    round_batch_system,
    round_batch_user,
    supervisor_system,
    supervisor_user,
)


def _normalize_evaluation_payload(data: dict) -> dict:
    """
    Accept slight schema drift from models, e.g. nested wrapper objects like:
    {"evaluation": {...}} or {"result": {...}}.
    """
    if not isinstance(data, dict):
        return data
    for key in ("evaluation", "result", "scores"):
        wrapped = data.get(key)
        if isinstance(wrapped, dict):
            return wrapped
    return data


def _num_like(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        txt = value.strip()
        try:
            return float(txt)
        except Exception:
            return None
    return None


def _normalize_10_scale(value: Any) -> float:
    n = _num_like(value)
    if n is None:
        return 6.0
    # Some models return 0-1 scale despite instructions; map to 1-10.
    if 0.0 <= n <= 1.0:
        n *= 10.0
    return max(1.0, min(10.0, n))


def _coerce_evaluation_result(data: dict, *, raw_fallback: str = "") -> EvaluationResult:
    """
    Convert imperfect model schemas into strict EvaluationResult.
    This prevents long user flows from failing at the final step.
    """
    d = _normalize_evaluation_payload(data if isinstance(data, dict) else {})
    # Common alternative key names from model drift.
    tech = d.get("technical_accuracy", d.get("correctness", d.get("technical", d.get("accuracy"))))
    comp = d.get("completeness", d.get("coverage"))
    clar = d.get("clarity", d.get("conciseness"))
    depth = d.get("depth", d.get("detail"))
    comm = d.get("communication", d.get("communication_quality", d.get("communication_clarity")))
    overall = d.get("overall_score", d.get("score", d.get("overall")))

    overall_10 = _normalize_10_scale(overall if overall is not None else tech)
    overall_i = int(round(overall_10))
    out = {
        "technical_accuracy": int(round(_normalize_10_scale(tech if tech is not None else overall_i))),
        "completeness": int(round(_normalize_10_scale(comp if comp is not None else overall_i))),
        "clarity": int(round(_normalize_10_scale(clar if clar is not None else overall_i))),
        "depth": int(round(_normalize_10_scale(depth if depth is not None else overall_i))),
        "communication": int(round(_normalize_10_scale(comm if comm is not None else overall_i))),
        "overall_score": round(overall_10, 1),
        "missed_points": d.get("missed_points") if isinstance(d.get("missed_points"), list) else [],
        "strengths": d.get("strengths") if isinstance(d.get("strengths"), list) else [],
        "feedback_summary": str(d.get("feedback_summary", "")).strip(),
    }
    if not out["feedback_summary"]:
        out["feedback_summary"] = (
            str(raw_fallback).strip()[:280] if str(raw_fallback).strip() else "Evaluation generated with fallback normalization."
        )
    return EvaluationResult.model_validate(out)


def interviewer_agent(
    *,
    role: str,
    interview_type: str = "General",
    difficulty: str,
    topic: str,
    weak_topics: list[str],
    last_feedback_hint: str,
    recent_responses: list[str] | None = None,
    question_style: str = "balanced",
) -> str:
    recent = recent_responses or []
    raw = chat_completion(
        model=model_for("interview"),
        system=interviewer_system(),
        user=interviewer_user(
            role=role,
            interview_type=interview_type,
            difficulty=difficulty,
            topic=topic,
            weak_topics=weak_topics,
            last_feedback_hint=last_feedback_hint,
            recent_responses=recent,
            question_style=question_style,
        ),
        temperature=0.7,
    )
    return raw.strip()


def evaluator_agent(*, question: str, answer: str) -> EvaluationResult:
    model = model_for("evaluator")
    system = evaluator_system()
    user = evaluator_user(question=question, answer=answer)

    raw = chat_completion(model=model, system=system, user=user, temperature=0.2)
    try:
        data = _normalize_evaluation_payload(extract_json_object(raw))
        return _coerce_evaluation_result(data, raw_fallback=raw)
    except Exception:
        # One repair attempt: ask the same model to output *only* valid JSON.
        repair = chat_completion(
            model=model,
            system=system,
            user=(
                "Your previous output was not valid JSON for the required schema. "
                "Output ONLY a single corrected JSON object for the same question/answer.\n\n"
                + user
            ),
            temperature=0.0,
        )
        try:
            data2 = _normalize_evaluation_payload(extract_json_object(repair))
            return _coerce_evaluation_result(data2, raw_fallback=repair)
        except Exception:
            return _coerce_evaluation_result({}, raw_fallback=repair)


def _evaluator_with_system(*, question: str, answer: str, system: str) -> EvaluationResult:
    user = evaluator_user(question=question, answer=answer)
    model = model_for("evaluator")
    raw = chat_completion(model=model, system=system, user=user, temperature=0.2)
    try:
        data = _normalize_evaluation_payload(extract_json_object(raw))
        return _coerce_evaluation_result(data, raw_fallback=raw)
    except Exception:
        # Keep jury mode resilient to minor JSON format drift.
        repair = chat_completion(
            model=model,
            system=system,
            user=(
                "Your previous output was not valid JSON for the required schema. "
                "Output ONLY a single corrected JSON object for the same question/answer.\n\n"
                + user
            ),
            temperature=0.0,
        )
        try:
            data2 = _normalize_evaluation_payload(extract_json_object(repair))
            return _coerce_evaluation_result(data2, raw_fallback=repair)
        except Exception:
            return _coerce_evaluation_result({}, raw_fallback=repair)


def jury_evaluator_agent(*, question: str, answer: str) -> tuple[EvaluationResult, EvaluationResult, EvaluationResult, str]:
    strict = _evaluator_with_system(question=question, answer=answer, system=evaluator_system_strict())
    clarity = _evaluator_with_system(question=question, answer=answer, system=evaluator_system_clarity())
    final_overall = round((strict.overall_score * 0.65) + (clarity.overall_score * 0.35), 1)
    final = EvaluationResult(
        technical_accuracy=round((strict.technical_accuracy * 0.7) + (clarity.technical_accuracy * 0.3)),
        completeness=round((strict.completeness * 0.65) + (clarity.completeness * 0.35)),
        clarity=round((strict.clarity * 0.35) + (clarity.clarity * 0.65)),
        depth=round((strict.depth * 0.7) + (clarity.depth * 0.3)),
        communication=round((strict.communication * 0.3) + (clarity.communication * 0.7)),
        overall_score=max(1.0, min(10.0, final_overall)),
        missed_points=(strict.missed_points + clarity.missed_points)[:6],
        strengths=(strict.strengths + clarity.strengths)[:6],
        feedback_summary=(
            "Jury verdict: combines strict technical correctness with communication clarity."
        ),
    )
    summary = f"Strict {strict.overall_score}/10, Clarity {clarity.overall_score}/10, Final {final.overall_score}/10."
    return strict, clarity, final, summary


def answer_key_agent(*, role: str, interview_type: str, question: str) -> str:
    raw = chat_completion(
        model=model_for("interview"),
        system=answer_key_system(),
        user=answer_key_user(role=role, interview_type=interview_type, question=question),
        temperature=0.2,
    )
    return raw.strip()


def coaching_agent(*, role: str, topic: str, gap: str, mode: str) -> str:
    raw = chat_completion(
        model=model_for("interview"),
        system=coach_system(),
        user=coach_user(role=role, topic=topic, gap=gap, mode=mode),
        temperature=0.3,
    )
    return raw.strip()


def reflection_agent(*, topic: str, question: str, answer: str, feedback: str) -> tuple[str, str, str]:
    raw = chat_completion(
        model=model_for("interview"),
        system=reflection_system(),
        user=reflection_user(topic=topic, question=question, answer=answer, feedback=feedback),
        temperature=0.2,
    )
    try:
        data = extract_json_object(raw)
        pattern = str(data.get("mistake_pattern", "")).strip() or "Unclear pattern"
        style = str(data.get("recommended_style", "balanced")).strip() or "balanced"
        strategy = str(data.get("strategy_update", "")).strip() or "Keep practice adaptive."
        return pattern, style, strategy
    except Exception:
        return "Unclear pattern", "balanced", "Keep practice adaptive."


def coding_assistant_agent(*, challenge_title: str, prompt: str, user_code: str, question: str) -> str:
    raw = chat_completion(
        model=model_for("interview"),
        system=coding_assistant_system(),
        user=coding_assistant_user(
            challenge_title=challenge_title,
            prompt=prompt,
            user_code=user_code,
            question=question,
        ),
        temperature=0.2,
    )
    return raw.strip()


def supervisor_tool_agent(*, topic: str, missed_points: list[str], score: float) -> tuple[str, str]:
    raw = chat_completion(
        model=model_for("interview"),
        system=supervisor_system(),
        user=supervisor_user(topic=topic, missed_points=missed_points, score=score),
        temperature=0.1,
    )
    try:
        data = extract_json_object(raw)
        tool = str(data.get("tool", "none")).strip() or "none"
        reason = str(data.get("reason", "")).strip() or "No tool selected."
        return tool, reason
    except Exception:
        return "none", "No tool selected."


def critic_agent(
    *,
    topic: str,
    question: str,
    answer: str,
    evaluation: EvaluationResult,
    planner_action: str,
    planner_focus_topic: str,
    intervention_text: str,
    tool_name: str,
    tool_output: str,
) -> tuple[bool, float, str, str, str]:
    raw = chat_completion(
        model=model_for("evaluator"),
        system=critic_system(),
        user=critic_user(
            topic=topic,
            question=question,
            answer=answer,
            score=evaluation.overall_score,
            missed_points=evaluation.missed_points,
            planner_action=planner_action,
            planner_focus_topic=planner_focus_topic,
            intervention_text=intervention_text,
            tool_name=tool_name,
            tool_output=tool_output,
        ),
        temperature=0.1,
    )
    try:
        data = extract_json_object(raw)
        approved = bool(data.get("approved", False))
        c = _num_like(data.get("confidence"))
        confidence = max(0.0, min(1.0, c if c is not None else 0.5))
        reason = str(data.get("reason", "")).strip() or "No critic reason provided."
        suggested_action = str(data.get("suggested_action", "")).strip() or "give_lesson"
        suggested_focus = str(data.get("suggested_focus_topic", "")).strip() or planner_focus_topic
        return approved, confidence, reason, suggested_action, suggested_focus
    except Exception:
        fallback_approved = evaluation.overall_score >= 7.0 or (planner_action in {"give_lesson", "give_drill"} and bool(evaluation.missed_points))
        fallback_reason = "Fallback critic decision due to JSON parse failure."
        fallback_focus = evaluation.missed_points[0] if evaluation.missed_points else planner_focus_topic
        return fallback_approved, 0.35, fallback_reason, "give_lesson", fallback_focus


def _items_from_array(arr: list) -> list[RoundQaItem]:
    out: list[RoundQaItem] = []
    for x in arr:
        if not isinstance(x, dict):
            continue
        q = (x.get("question") or x.get("q") or "").strip()
        ref = (
            x.get("reference_answer")
            or x.get("answer")
            or x.get("reference")
            or ""
        )
        ref = str(ref).strip()
        if q and ref:
            out.append(RoundQaItem(question=q, reference_answer=ref))
    return out


def round_batch_agent(
    *,
    role: str,
    interview_type: str,
    topic: str,
    difficulty: str,
    count: int,
    question_style: str = "balanced",
) -> tuple[list[RoundQaItem], str]:
    """
    One LLM call: JSON array of {question, reference_answer}.
    Returns validated items and raw model text for debugging/display.
    """
    model = model_for("interview")
    system = round_batch_system()
    user = round_batch_user(
        role=role,
        interview_type=interview_type,
        topic=topic,
        difficulty=difficulty,
        count=count,
        question_style=question_style,
    )

    def _parse(raw: str) -> list[RoundQaItem]:
        arr = extract_json_array(raw)
        if not isinstance(arr, list):
            raise ValueError("Expected JSON array")
        items = _items_from_array(arr)
        if len(items) != count:
            raise ValueError(f"Expected {count} items, got {len(items)}")
        return items

    raw = chat_completion(model=model, system=system, user=user, temperature=0.55)
    try:
        items = _parse(raw)
        return items, raw.strip()
    except Exception:
        repair = chat_completion(
            model=model,
            system=system,
            user=(
                "Your previous reply was not valid JSON or had wrong length. "
                f"Output ONLY a JSON array of exactly {count} objects with keys "
                '"question" and "reference_answer". No markdown.\n\n'
                + user
            ),
            temperature=0.0,
        )
        items2 = _parse(repair)
        return items2, repair.strip()

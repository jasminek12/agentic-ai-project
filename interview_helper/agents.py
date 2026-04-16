from __future__ import annotations

from interview_helper.llm_client import chat_completion, model_for
from interview_helper.models import EvaluationResult, RoundQaItem
from interview_helper.parse_json import extract_json_array, extract_json_object
from interview_helper.prompts import (
    answer_key_system,
    answer_key_user,
    coach_system,
    coach_user,
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
        data = extract_json_object(raw)
        return EvaluationResult.model_validate(data)
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
        data2 = extract_json_object(repair)
        return EvaluationResult.model_validate(data2)


def _evaluator_with_system(*, question: str, answer: str, system: str) -> EvaluationResult:
    user = evaluator_user(question=question, answer=answer)
    model = model_for("evaluator")
    raw = chat_completion(model=model, system=system, user=user, temperature=0.2)
    data = extract_json_object(raw)
    return EvaluationResult.model_validate(data)


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

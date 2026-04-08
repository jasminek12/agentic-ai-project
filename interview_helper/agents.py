from __future__ import annotations

from interview_helper.llm_client import chat_completion, model_for
from interview_helper.models import EvaluationResult, RoundQaItem
from interview_helper.parse_json import extract_json_array, extract_json_object
from interview_helper.prompts import (
    answer_key_system,
    answer_key_user,
    evaluator_system,
    evaluator_user,
    interviewer_system,
    interviewer_user,
    round_batch_system,
    round_batch_user,
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


def answer_key_agent(*, role: str, interview_type: str, question: str) -> str:
    raw = chat_completion(
        model=model_for("interview"),
        system=answer_key_system(),
        user=answer_key_user(role=role, interview_type=interview_type, question=question),
        temperature=0.2,
    )
    return raw.strip()


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

from __future__ import annotations

from interview_helper.llm_client import chat_completion, model_for
from interview_helper.models import EvaluationResult
from interview_helper.parse_json import extract_json_object
from interview_helper.prompts import (
    evaluator_system,
    evaluator_user,
    interviewer_system,
    interviewer_user,
)


def interviewer_agent(
    *,
    role: str,
    difficulty: str,
    topic: str,
    weak_topics: list[str],
    last_feedback_hint: str,
) -> str:
    raw = chat_completion(
        model=model_for("interview"),
        system=interviewer_system(),
        user=interviewer_user(
            role=role,
            difficulty=difficulty,
            topic=topic,
            weak_topics=weak_topics,
            last_feedback_hint=last_feedback_hint,
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

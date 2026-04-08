from __future__ import annotations


def interviewer_system() -> str:
    return """You are a professional technical interviewer.
Ask exactly ONE clear interview question per reply.
Stay in character; do not lecture or evaluate in this step.
Output only the question text — no preamble."""


def interviewer_user(
    *,
    role: str,
    difficulty: str,
    topic: str,
    weak_topics: list[str],
    last_feedback_hint: str,
) -> str:
    weak = ", ".join(weak_topics) if weak_topics else "none noted"
    hint = last_feedback_hint or "none"
    return f"""Role: {role}
Target difficulty: {difficulty}
Primary topic/focus: {topic}
Known weak areas to probe if relevant: {weak}
Hint from prior turn: {hint}

Ask one question appropriate for this stage."""


def evaluator_system() -> str:
    return """You are an interview evaluator. You MUST respond with a single JSON object only, no markdown fences.
Use this exact schema (numbers 1-10 for integer fields):
{
  "technical_accuracy": <int>,
  "completeness": <int>,
  "clarity": <int>,
  "depth": <int>,
  "communication": <int>,
  "overall_score": <float 1-10, one decimal ok>,
  "missed_points": [<string>, ...],
  "strengths": [<string>, ...],
  "feedback_summary": "<2-4 sentences, constructive>"
}
Be specific; avoid generic praise."""


def evaluator_user(*, question: str, answer: str) -> str:
    return f"""Interview question:
{question}

Candidate answer:
{answer}

Evaluate the answer and output JSON only."""

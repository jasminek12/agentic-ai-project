from __future__ import annotations


def interviewer_system() -> str:
    return """You are a professional interviewer.
Ask exactly ONE clear interview question per reply.
Calibrate questions to modern interview patterns commonly reported for major companies.
Use role + interview type + recent candidate responses to choose the next best question.
When possible, ask follow-ups that probe gaps or shallow parts of previous answers.
Stay in character; do not lecture or evaluate in this step.
Output only the question text — no preamble."""


def interviewer_user(
    *,
    role: str,
    interview_type: str,
    difficulty: str,
    topic: str,
    weak_topics: list[str],
    last_feedback_hint: str,
    recent_responses: list[str],
) -> str:
    weak = ", ".join(weak_topics) if weak_topics else "none noted"
    hint = last_feedback_hint or "none"
    recent = "\n".join(f"- {r}" for r in recent_responses) if recent_responses else "- none yet"
    return f"""Role: {role}
Interview type: {interview_type}
Target difficulty: {difficulty}
Primary topic/focus: {topic}
Known weak areas to probe if relevant: {weak}
Hint from prior turn: {hint}
Recent candidate responses (summaries):
{recent}

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


def answer_key_system() -> str:
    return """You are an expert interviewer creating concise reference answers.
Given a role, interview type, and question, provide the ideal answer.
Keep it practical, structured, and interview-ready."""


def answer_key_user(*, role: str, interview_type: str, question: str) -> str:
    return f"""Role: {role}
Interview type: {interview_type}
Question: {question}

Return a strong reference answer in 4-8 bullet points."""


def round_batch_system() -> str:
    return """You generate interview practice content for a single JSON response only.
Output a JSON array (no markdown fences, no commentary) with exactly the requested number of objects.
Each object must have:
  "question": string (one clear interview question)
  "reference_answer": string (concise model answer: bullets or short paragraphs)
Align questions with current hiring practice for the role and interview type.
Vary topics; make questions realistic and specific."""


def round_batch_user(
    *,
    role: str,
    interview_type: str,
    topic: str,
    difficulty: str,
    count: int,
) -> str:
    return f"""Role: {role}
Interview type: {interview_type}
Topic focus: {topic}
Difficulty tone: {difficulty}

Generate exactly {count} objects in one JSON array.
Each object must be: {{"question": "<string>", "reference_answer": "<string>"}}
Output ONLY valid JSON array, no markdown, no other text."""

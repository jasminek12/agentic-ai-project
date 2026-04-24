import json
import re
from typing import Any, Dict, List

from app.utils.llm import call_llm


def _extract_json_object(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in LLM output.")
        return json.loads(match.group(0))


def next_question_logic(history: List[Dict[str, Any]]) -> str:
    """Return desired difficulty based on latest score."""
    if not history:
        return "medium"

    last_scored = next((item for item in reversed(history) if isinstance(item.get("score"), int)), None)
    if not last_scored:
        return "medium"

    score = last_scored["score"]
    if score < 5:
        return "easy"
    if 5 <= score <= 7:
        return "medium"
    return "hard"


def generate_question(mode: str, job_description: str, resume: str, history: List[Dict[str, Any]]) -> Dict[str, str]:
    print(f"[DEBUG] Generating interview question for mode={mode}")
    difficulty = next_question_logic(history)
    recent_history = history[-5:] if history else []

    if mode == "behavioral":
        mode_instructions = (
            "Generate one STAR-style behavioral interview question. "
            "Use resume context and focus on teamwork, leadership, or challenges."
        )
    elif mode == "technical":
        mode_instructions = (
            "Generate one technical interview question tied to the job description. "
            "Focus heavily on required skills/tools and practical implementation."
        )
    else:
        raise ValueError("Invalid interview mode. Must be 'behavioral' or 'technical'.")

    prompt = f"""
You are an interview coach.
Mode: {mode}
Difficulty target: {difficulty}

Instructions:
- {mode_instructions}
- Ask exactly one question.
- Adapt to candidate performance based on prior scores.
- Return STRICT JSON only:
  {{
    "question": "..."
  }}

Job Description:
{job_description}

Resume:
{resume}

Recent History:
{json.dumps(recent_history, ensure_ascii=False)}
""".strip()

    response = call_llm(prompt)
    parsed = _extract_json_object(response)
    question = parsed.get("question", "").strip()
    if not question:
        raise ValueError("Generated question is empty.")
    return {"question": question}


def evaluate_answer(question: str, answer: str) -> Dict[str, Any]:
    print("[DEBUG] Evaluating interview answer")
    prompt = f"""
You are an interview evaluator.
Score the answer from 0 to 10 and provide constructive feedback.
Identify weak topics.

Return STRICT JSON only:
{{
  "score": 0,
  "feedback": "...",
  "weak_topics": ["...", "..."]
}}

Question:
{question}

Answer:
{answer}
""".strip()

    response = call_llm(prompt)
    parsed = _extract_json_object(response)

    score = parsed.get("score")
    feedback = str(parsed.get("feedback", "")).strip()
    weak_topics = parsed.get("weak_topics", [])

    if not isinstance(score, int):
        raise ValueError("LLM returned non-integer score.")
    if score < 0 or score > 10:
        raise ValueError("LLM returned score outside 0-10 range.")
    if not feedback:
        raise ValueError("LLM returned empty feedback.")
    if not isinstance(weak_topics, list):
        weak_topics = []

    return {"score": score, "feedback": feedback, "weak_topics": weak_topics}

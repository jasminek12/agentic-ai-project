import json
import re
from collections import Counter
from datetime import date, datetime
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
    """Return desired difficulty based on last 3 scored answers."""
    if not history:
        return "medium"

    scored = [item.get("score") for item in history if isinstance(item.get("score"), int)]
    recent = scored[-3:]
    if not recent:
        return "medium"

    avg_score = sum(recent) / len(recent)
    if avg_score < 5:
        return "easy"
    if 5 <= avg_score <= 7.5:
        return "medium"
    return "hard"


def _get_recent_weak_topics(history: List[Dict[str, Any]]) -> List[str]:
    all_topics: List[str] = []
    for item in history[-8:]:
        topics = item.get("weak_topics", [])
        if isinstance(topics, list):
            all_topics.extend([str(topic).strip() for topic in topics if str(topic).strip()])
    return [topic for topic, _ in Counter(all_topics).most_common(4)]


def _next_panel_persona(panel_personas: List[str], turn_index: int) -> str:
    if not panel_personas:
        return "interviewer"
    return panel_personas[turn_index % len(panel_personas)]


def generate_question(
    mode: str,
    job_description: str,
    resume: str,
    history: List[Dict[str, Any]],
    panel_mode: bool = False,
    pressure_round: bool = False,
    company_context: str = "",
    role_context: str = "",
    panel_personas: List[str] | None = None,
    panel_turn_index: int = 0,
) -> Dict[str, str]:
    print(f"[DEBUG] Generating interview question for mode={mode}")
    difficulty = next_question_logic(history)
    recent_history = history[-5:] if history else []
    weak_topics = _get_recent_weak_topics(history)
    persona = _next_panel_persona(panel_personas or [], panel_turn_index)
    style = "challenging and probing" if pressure_round else "supportive and structured"

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
- Keep style {style}.
- If panel mode is true, ask in the voice of persona: "{persona}".
- If weak topics exist, target one of them with a tailored drill.
- Return STRICT JSON only:
  {{
    "question": "...",
    "focus_area": "..."
  }}

Panel Mode: {panel_mode}
Pressure Round: {pressure_round}
Persona: {persona}
Company Context: {company_context}
Role Context: {role_context}
Recent Weak Topics: {json.dumps(weak_topics, ensure_ascii=False)}

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
    focus_area = str(parsed.get("focus_area", "")).strip()
    if not question:
        raise ValueError("Generated question is empty.")
    return {"question": question, "focus_area": focus_area, "persona": persona}


def evaluate_answer(question: str, answer: str, mode: str = "behavioral") -> Dict[str, Any]:
    print("[DEBUG] Evaluating interview answer")
    prompt = f"""
You are an interview evaluator.
Score the answer from 0 to 10 and provide constructive feedback.
Identify weak topics.
Also provide a concise critique and a stronger rewrite in the candidate's voice.

Return STRICT JSON only:
{{
  "score": 0,
  "feedback": "...",
  "weak_topics": ["...", "..."],
  "critique": "...",
  "rewrite": "..."
}}

Mode:
{mode}

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
    critique = str(parsed.get("critique", "")).strip()
    rewrite = str(parsed.get("rewrite", "")).strip()

    if not isinstance(score, int):
        raise ValueError("LLM returned non-integer score.")
    if score < 0 or score > 10:
        raise ValueError("LLM returned score outside 0-10 range.")
    if not feedback:
        raise ValueError("LLM returned empty feedback.")
    if not isinstance(weak_topics, list):
        weak_topics = []
    if not critique:
        critique = "The answer addresses the prompt but needs tighter structure, evidence, and explicit impact."
    if not rewrite:
        rewrite = answer.strip()

    return {
        "score": score,
        "feedback": feedback,
        "weak_topics": weak_topics,
        "critique": critique,
        "rewrite": rewrite,
    }


def generate_follow_up(question: str, answer: str, weak_topics: List[str], pressure_round: bool = False) -> str:
    prompt = f"""
Generate one natural interviewer follow-up question based on the latest answer.
If pressure round is enabled, make it more challenging.
Target measurable impact, trade-offs, or clarity gaps.

Return STRICT JSON only:
{{
  "follow_up_question": "..."
}}

Pressure Round: {pressure_round}
Original Question: {question}
Candidate Answer: {answer}
Weak Topics: {json.dumps(weak_topics, ensure_ascii=False)}
""".strip()
    response = call_llm(prompt)
    parsed = _extract_json_object(response)
    return str(parsed.get("follow_up_question", "")).strip()


def build_debrief_actions(score: int, weak_topics: List[str]) -> Dict[str, Any]:
    prioritized = [topic for topic, _ in Counter(weak_topics).most_common(3)]
    while len(prioritized) < 3:
        fallback = ["quantification", "depth", "clarity"][len(prioritized)]
        if fallback not in prioritized:
            prioritized.append(fallback)

    actions = [
        f"Practice one answer focused on {prioritized[0]} and include a concrete metric.",
        f"Record and revise one answer focused on {prioritized[1]} using a clear STAR flow.",
        f"Run a timed drill targeting {prioritized[2]} in under 90 seconds with explicit outcomes.",
    ]
    next_target = (
        "Reach 8/10+ on the next answer with one metric, one trade-off, and a concise closing result."
        if score < 8
        else "Sustain 8/10+ while improving precision and adding clearer leadership signals."
    )
    return {"actions": actions, "target": next_target}


def build_curriculum_plan(weak_topic_memory: List[str], interview_date: str = "") -> List[str]:
    top_topics = [topic for topic, _ in Counter(weak_topic_memory).most_common(3)]
    if not top_topics:
        top_topics = ["quantification", "clarity", "trade-offs"]

    days = 7
    if interview_date:
        try:
            target = datetime.strptime(interview_date, "%Y-%m-%d").date()
            days_until = max(1, (target - date.today()).days)
            days = min(7, days_until)
        except ValueError:
            days = 7

    plan: List[str] = []
    for day_idx in range(days):
        topic = top_topics[day_idx % len(top_topics)]
        plan.append(f"Day {day_idx + 1}: 30-45 min focused drill on {topic} plus one timed mock answer.")
    return plan


def estimate_question_count(job_description: str, mode: str) -> int:
    text = job_description.lower()
    base = 6 if mode == "behavioral" else 7
    if any(keyword in text for keyword in ["senior", "staff", "lead", "principal", "architect"]):
        base += 2
    if any(keyword in text for keyword in ["intern", "junior", "entry-level", "graduate"]):
        base -= 1
    if len(job_description.split()) > 220:
        base += 1
    return max(4, min(10, base))


def summarize_final_evaluation(history: List[Dict[str, Any]], mode: str) -> str:
    scored_items = [item for item in history if isinstance(item.get("score"), int)]
    if not scored_items:
        return "No scored answers were completed."

    avg_score = sum(int(item["score"]) for item in scored_items) / len(scored_items)
    all_weak_topics: List[str] = []
    for item in scored_items:
        topics = item.get("weak_topics", [])
        if isinstance(topics, list):
            all_weak_topics.extend([str(topic).strip() for topic in topics if str(topic).strip()])
    top_topics = [topic for topic, _ in Counter(all_weak_topics).most_common(3)]
    strengths = "communication and structure" if avg_score >= 7 else "consistency and clarity growth potential"
    weak_summary = ", ".join(top_topics) if top_topics else "depth and quantification"

    return (
        f"Completed {len(scored_items)} {mode} questions with an average score of {avg_score:.1f}/10. "
        f"Current strengths include {strengths}. Primary improvement themes are {weak_summary}."
    )

from __future__ import annotations

from interview_helper.agents import answer_key_agent, coaching_agent
from interview_helper.models import SessionSnapshot


def concept_explainer(*, role: str, topic: str, gap: str) -> str:
    return coaching_agent(role=role, topic=topic, gap=gap, mode="lesson")


def generate_whiteboard_question(*, role: str, topic: str) -> str:
    return (
        f"Whiteboard drill for {role}: Design and explain a solution for '{topic}'. "
        "State trade-offs, complexity, and one edge case."
    )


def fetch_system_design_template(*, topic: str) -> str:
    return (
        f"System design template for '{topic}':\n"
        "1) Requirements\n2) Capacity estimates\n3) High-level architecture\n"
        "4) Data model\n5) APIs\n6) Bottlenecks\n7) Trade-offs"
    )


def retrieve_past_mistakes(*, session: SessionSnapshot) -> str:
    recent = session.missed_points_log[-5:]
    if not recent:
        return "No recurring mistakes logged yet."
    return "Recent mistakes to revisit: " + ", ".join(recent)


def compare_with_best_answer(*, role: str, interview_type: str, question: str, user_answer: str) -> str:
    best = answer_key_agent(role=role, interview_type=interview_type, question=question)
    return (
        "Best-answer comparison:\n"
        f"- Your answer length: {len(user_answer.split())} words\n"
        "- Compare your structure and missing points against this reference:\n"
        f"{best}"
    )

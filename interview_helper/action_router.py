from __future__ import annotations

from interview_helper.agents import coaching_agent
from interview_helper.models import NextPlan, SessionSnapshot
from interview_helper.tools_runtime import (
    compare_with_best_answer,
    concept_explainer,
    fetch_system_design_template,
    generate_whiteboard_question,
    retrieve_past_mistakes,
)


def execute_plan_action(plan: NextPlan, session: SessionSnapshot) -> str:
    """Execute planner-selected intervention and return display text."""
    action = plan.action
    payload = plan.action_payload or plan.focus_topic

    if action == "ask_question":
        return "Proceeding with the next interview question."
    if action == "give_lesson":
        return coaching_agent(
            role=session.role,
            topic=plan.focus_topic,
            gap=payload,
            mode="lesson",
        )
    if action == "give_drill":
        return coaching_agent(
            role=session.role,
            topic=plan.focus_topic,
            gap=payload,
            mode="drill",
        )
    if action == "review_mistakes":
        recent = ", ".join(session.missed_points_log[-3:]) or payload
        return (
            "Recurring gaps to review before continuing: "
            f"{recent}. Focus on explaining reasoning, not just final answers."
        )
    if action == "end_session":
        return (
            "Session goal reached. Consider ending now and reviewing strengths: "
            f"{', '.join(session.strong_topics) or 'steady improvement'}."
        )
    return "No action executed."


def execute_supervisor_tool(
    *,
    tool_name: str,
    session: SessionSnapshot,
    topic: str,
    missed_points: list[str],
    question: str,
    answer: str,
    interview_type: str,
) -> str:
    gap = missed_points[0] if missed_points else topic
    if tool_name == "concept_explainer":
        return concept_explainer(role=session.role, topic=topic, gap=gap)
    if tool_name == "generate_whiteboard_question":
        return generate_whiteboard_question(role=session.role, topic=topic)
    if tool_name == "fetch_system_design_template":
        return fetch_system_design_template(topic=topic)
    if tool_name == "retrieve_past_mistakes":
        return retrieve_past_mistakes(session=session)
    if tool_name == "compare_with_best_answer":
        return compare_with_best_answer(
            role=session.role,
            interview_type=interview_type,
            question=question,
            user_answer=answer,
        )
    return "No tool executed this turn."

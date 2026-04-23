from __future__ import annotations

from interview_helper.action_router import execute_plan_action, execute_supervisor_tool
from interview_helper.agents import (
    critic_agent,
    evaluator_agent,
    jury_evaluator_agent,
    reflection_agent,
    supervisor_tool_agent,
)
from interview_helper.models import EvaluationResult, NextPlan, SessionSnapshot
from interview_helper.planner import plan_next, update_memory


def _replan_from_critic(
    *,
    current: NextPlan,
    suggested_action: str,
    suggested_focus: str,
    evaluation: EvaluationResult,
) -> NextPlan:
    allowed = {"ask_question", "give_lesson", "give_drill", "review_mistakes", "end_session"}
    action = suggested_action if suggested_action in allowed else current.action
    focus = suggested_focus.strip() or current.focus_topic
    payload = evaluation.missed_points[0] if evaluation.missed_points else current.action_payload
    rationale = (
        f"Replanned after critic feedback. Prior action '{current.action}' replaced with '{action}'."
    )
    return NextPlan(
        next_difficulty=current.next_difficulty,
        focus_topic=focus,
        rationale=rationale,
        action=action,  # type: ignore[arg-type]
        action_payload=payload,
    )


def run_agentic_turn(
    *,
    session: SessionSnapshot,
    question: str,
    answer: str,
    topic: str,
    interview_type: str,
    jury_mode: bool,
    enable_reflection: bool,
    enable_tools: bool,
    max_steps: int = 3,
) -> dict:
    if jury_mode:
        strict_ev, clarity_ev, ev, jury_summary = jury_evaluator_agent(question=question, answer=answer)
    else:
        ev = evaluator_agent(question=question, answer=answer)
        strict_ev = ev
        clarity_ev = ev
        jury_summary = "Single evaluator mode."

    plan = plan_next(ev, session, default_topic=topic)
    intervention = "Proceeding with the next interview question."
    tool_name, tool_reason, tool_output = "none", "Not executed", ""
    reflection_pattern, reflection_style, reflection_strategy = (
        "Reflection disabled",
        session.preferred_question_style,
        "",
    )
    critic_notes: list[dict[str, str | float | bool]] = []

    for step in range(max(1, max_steps)):
        intervention = execute_plan_action(plan, session)
        if enable_tools:
            tool_name, tool_reason = supervisor_tool_agent(
                topic=plan.focus_topic,
                missed_points=ev.missed_points,
                score=ev.overall_score,
            )
            tool_output = execute_supervisor_tool(
                tool_name=tool_name,
                session=session,
                topic=plan.focus_topic,
                missed_points=ev.missed_points,
                question=question,
                answer=answer,
                interview_type=interview_type,
            )
        else:
            tool_name, tool_reason, tool_output = "none", "Tools disabled", ""

        if enable_reflection:
            reflection_pattern, reflection_style, reflection_strategy = reflection_agent(
                topic=plan.focus_topic,
                question=question,
                answer=answer,
                feedback=ev.feedback_summary,
            )
            session.preferred_question_style = reflection_style
        else:
            reflection_pattern = "Reflection disabled"
            reflection_style = session.preferred_question_style
            reflection_strategy = ""

        approved, confidence, reason, suggested_action, suggested_focus = critic_agent(
            topic=topic,
            question=question,
            answer=answer,
            evaluation=ev,
            planner_action=plan.action,
            planner_focus_topic=plan.focus_topic,
            intervention_text=intervention,
            tool_name=tool_name,
            tool_output=tool_output,
        )
        critic_notes.append(
            {
                "step": float(step + 1),
                "approved": approved,
                "confidence": confidence,
                "reason": reason,
                "suggested_action": suggested_action,
                "suggested_focus_topic": suggested_focus,
            }
        )
        if approved or step >= max_steps - 1:
            break
        plan = _replan_from_critic(
            current=plan,
            suggested_action=suggested_action,
            suggested_focus=suggested_focus,
            evaluation=ev,
        )

    update_memory(ev, session, plan.focus_topic)
    if session.reflections:
        session.reflections[-1].intervention_used = plan.action
        session.reflections[-1].mistake_pattern = reflection_pattern
        session.reflections[-1].recommended_style = reflection_style

    return {
        "evaluation": ev,
        "strict_evaluation": strict_ev,
        "clarity_evaluation": clarity_ev,
        "jury_summary": jury_summary,
        "plan": plan,
        "intervention": intervention,
        "tool_name": tool_name,
        "tool_reason": tool_reason,
        "tool_output": tool_output,
        "reflection_pattern": reflection_pattern,
        "reflection_style": reflection_style,
        "reflection_strategy": reflection_strategy,
        "critic_notes": critic_notes,
    }

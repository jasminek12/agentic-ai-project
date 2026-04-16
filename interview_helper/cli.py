"""
Terminal demo: role → adaptive questions → scored feedback → planner updates memory.

Usage:
  cd agentic-interview-helper
  copy .env.example .env   # then edit keys
  pip install -r requirements.txt
  python -m interview_helper.cli
"""

from __future__ import annotations

import argparse
from pathlib import Path

from interview_helper.action_router import execute_plan_action, execute_supervisor_tool
from interview_helper.agents import (
    evaluator_agent,
    interviewer_agent,
    jury_evaluator_agent,
    reflection_agent,
    supervisor_tool_agent,
)
from interview_helper.memory import load_session, save_session
from interview_helper.models import SessionSnapshot
from interview_helper.planner import plan_next, update_memory


def main() -> None:
    p = argparse.ArgumentParser(description="Agentic interview helper (CLI demo)")
    p.add_argument("--role", default="Software Engineer", help="Target role")
    p.add_argument(
        "--topic",
        default="data structures and algorithms",
        help="Starting topic focus",
    )
    p.add_argument(
        "--session-file",
        type=Path,
        default=Path(".interview_session.json"),
        help="Where to persist memory",
    )
    p.add_argument("--jury", action="store_true", help="Use jury evaluation (strict + clarity)")
    p.add_argument("--no-tools", action="store_true", help="Disable supervisor tool calls")
    p.add_argument("--no-reflection", action="store_true", help="Disable reflection loop")
    args = p.parse_args()

    session = load_session(args.session_file) or SessionSnapshot(role=args.role)
    if args.role and session.role != args.role:
        session.role = args.role

    difficulty = "medium"
    topic = args.topic
    last_hint = ""

    print("Agentic Interview Helper — adaptive, goal-driven interview loop.")
    print("Commands: /quit to exit, /reset to clear saved memory.\n")

    while True:
        q = interviewer_agent(
            role=session.role,
            interview_type="General",
            difficulty=difficulty,
            topic=topic,
            weak_topics=session.weak_topics,
            last_feedback_hint=last_hint,
            recent_responses=[],
            question_style=session.preferred_question_style,
        )
        print(f"\n[Interviewer | {difficulty} | focus: {topic}]\n{q}\n")

        ans = input("Your answer: ").strip()
        if ans.lower() == "/quit":
            save_session(args.session_file, session)
            print("Session saved. Bye.")
            return
        if ans.lower() == "/reset":
            session = SessionSnapshot(role=args.role)
            difficulty = "medium"
            topic = args.topic
            last_hint = ""
            if args.session_file.exists():
                args.session_file.unlink()
            print("Memory cleared.\n")
            continue
        if not ans:
            print("(Skipped — ask again with a real answer.)")
            continue

        if args.jury:
            strict_ev, clarity_ev, ev, jury_summary = jury_evaluator_agent(question=q, answer=ans)
            print(f"\n[Jury]\n{jury_summary}\n")
        else:
            ev = evaluator_agent(question=q, answer=ans)
            strict_ev = ev
            clarity_ev = ev
        print(
            f"\n[Evaluator]\n"
            f"Overall: {ev.overall_score}/10\n"
            f"Technical {ev.technical_accuracy} | Complete {ev.completeness} | "
            f"Clarity {ev.clarity} | Depth {ev.depth} | Comm {ev.communication}\n"
            f"Strengths: {', '.join(ev.strengths) or '—'}\n"
            f"Missed: {', '.join(ev.missed_points) or '—'}\n"
            f"\n{ev.feedback_summary}\n"
        )

        plan = plan_next(ev, session, default_topic=topic)
        update_memory(ev, session, plan.focus_topic)
        difficulty = plan.next_difficulty
        topic = plan.focus_topic
        last_hint = ev.feedback_summary[:400]

        intervention = execute_plan_action(plan, session)
        if session.reflections:
            session.reflections[-1].intervention_used = plan.action

        if not args.no_reflection:
            pattern, style, strategy = reflection_agent(
                topic=topic,
                question=q,
                answer=ans,
                feedback=ev.feedback_summary,
            )
            session.preferred_question_style = style
            print(f"\n[Reflection]\nPattern: {pattern}\nNext style: {style}\nStrategy: {strategy}\n")
        if not args.no_tools:
            tool_name, tool_reason = supervisor_tool_agent(
                topic=topic,
                missed_points=ev.missed_points,
                score=ev.overall_score,
            )
            tool_output = execute_supervisor_tool(
                tool_name=tool_name,
                session=session,
                topic=topic,
                missed_points=ev.missed_points,
                question=q,
                answer=ans,
                interview_type="General",
            )
            print(f"\n[Supervisor tool: {tool_name}]\nReason: {tool_reason}\n{tool_output}\n")

        print(
            f"\n[Planner] Action: {plan.action} | Next difficulty: {plan.next_difficulty} | "
            f"Next focus: {plan.focus_topic}\n→ {plan.rationale}\n"
        )
        print(f"[Intervention]\n{intervention}\n")
        if plan.action == "end_session" or session.completed:
            print("Target achieved. End this session or continue for extra practice.")

        save_session(args.session_file, session)


if __name__ == "__main__":
    main()

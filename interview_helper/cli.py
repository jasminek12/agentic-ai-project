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

from interview_helper.agents import evaluator_agent, interviewer_agent
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
    args = p.parse_args()

    session = load_session(args.session_file) or SessionSnapshot(role=args.role)
    if args.role and session.role != args.role:
        session.role = args.role

    difficulty = "medium"
    topic = args.topic
    last_hint = ""

    print("Agentic Interview Helper — type your answer after each question.")
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

        ev = evaluator_agent(question=q, answer=ans)
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

        print(
            f"\n[Planner] Next difficulty: {plan.next_difficulty} | "
            f"Next focus: {plan.focus_topic}\n→ {plan.rationale}\n"
        )

        save_session(args.session_file, session)


if __name__ == "__main__":
    main()

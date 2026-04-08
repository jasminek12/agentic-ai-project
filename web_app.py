from __future__ import annotations

from pathlib import Path

import streamlit as st

from interview_helper.agents import evaluator_agent, interviewer_agent
from interview_helper.memory import load_session, save_session
from interview_helper.models import SessionSnapshot
from interview_helper.planner import plan_next, update_memory


SESSION_FILE = Path(".interview_session.json")


def _ensure_state() -> None:
    if "session" not in st.session_state:
        persisted = load_session(SESSION_FILE)
        st.session_state.session = persisted or SessionSnapshot(role="Software Engineer")
    if "difficulty" not in st.session_state:
        st.session_state.difficulty = "medium"
    if "topic" not in st.session_state:
        st.session_state.topic = "data structures and algorithms"
    if "last_hint" not in st.session_state:
        st.session_state.last_hint = ""
    if "current_question" not in st.session_state:
        st.session_state.current_question = ""
    if "history" not in st.session_state:
        st.session_state.history = []
    if "last_error" not in st.session_state:
        st.session_state.last_error = ""


def _generate_question() -> None:
    session: SessionSnapshot = st.session_state.session
    st.session_state.current_question = interviewer_agent(
        role=session.role,
        difficulty=st.session_state.difficulty,
        topic=st.session_state.topic,
        weak_topics=session.weak_topics,
        last_feedback_hint=st.session_state.last_hint,
    )


def _reset_all() -> None:
    role = st.session_state.session.role if "session" in st.session_state else "Software Engineer"
    st.session_state.session = SessionSnapshot(role=role)
    st.session_state.difficulty = "medium"
    st.session_state.topic = "data structures and algorithms"
    st.session_state.last_hint = ""
    st.session_state.current_question = ""
    st.session_state.history = []
    st.session_state.last_error = ""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def main() -> None:
    st.set_page_config(page_title="Agentic Interview Helper", page_icon="🎯", layout="wide")
    st.title("🎯 Agentic Interview Helper")
    st.caption("Interviewer agent + Evaluator agent + Planner + Memory")

    _ensure_state()

    with st.sidebar:
        st.header("Session Setup")
        role = st.text_input("Target role", value=st.session_state.session.role)
        topic = st.text_input("Starting topic", value=st.session_state.topic)
        if st.button("Apply Settings"):
            st.session_state.session.role = role.strip() or "Software Engineer"
            st.session_state.topic = topic.strip() or "data structures and algorithms"
            save_session(SESSION_FILE, st.session_state.session)
            st.success("Settings updated.")

        col1, col2 = st.columns(2)
        if col1.button("New Question", use_container_width=True):
            try:
                _generate_question()
                st.session_state.last_error = ""
            except Exception as e:  # pragma: no cover
                st.session_state.last_error = f"Could not generate question: {e}"
        if col2.button("Reset Session", use_container_width=True):
            _reset_all()
            st.success("Session reset.")

        s: SessionSnapshot = st.session_state.session
        st.divider()
        st.subheader("Memory")
        st.write(f"Questions asked: **{s.questions_asked}**")
        st.write(f"Current difficulty: **{st.session_state.difficulty}**")
        st.write(f"Current focus: **{st.session_state.topic}**")
        st.write(f"Weak topics: {', '.join(s.weak_topics) or '—'}")
        st.write(f"Strong topics: {', '.join(s.strong_topics) or '—'}")

    if not st.session_state.current_question:
        st.info("Click **New Question** in the sidebar to start.")
    else:
        st.subheader("Current Question")
        st.write(st.session_state.current_question)

    answer = st.text_area("Your answer", height=180, placeholder="Type your interview answer here...")
    if st.button("Evaluate Answer", type="primary", disabled=not st.session_state.current_question):
        if not answer.strip():
            st.warning("Please enter an answer first.")
        else:
            try:
                ev = evaluator_agent(question=st.session_state.current_question, answer=answer.strip())
                plan = plan_next(ev, st.session_state.session, default_topic=st.session_state.topic)
                update_memory(ev, st.session_state.session, plan.focus_topic)

                st.session_state.difficulty = plan.next_difficulty
                st.session_state.topic = plan.focus_topic
                st.session_state.last_hint = ev.feedback_summary[:400]
                save_session(SESSION_FILE, st.session_state.session)

                st.session_state.history.append(
                    {
                        "question": st.session_state.current_question,
                        "answer": answer.strip(),
                        "evaluation": ev,
                        "plan": plan,
                    }
                )
                st.session_state.current_question = ""
                st.session_state.last_error = ""
                st.success("Answer evaluated. Generate the next question from the sidebar.")
            except Exception as e:  # pragma: no cover
                st.session_state.last_error = f"Evaluation failed: {e}"

    if st.session_state.last_error:
        st.error(st.session_state.last_error)

    if st.session_state.history:
        st.subheader("Interview History")
        for idx, item in enumerate(reversed(st.session_state.history), start=1):
            ev = item["evaluation"]
            plan = item["plan"]
            with st.expander(f"Round {len(st.session_state.history) - idx + 1}: {plan.focus_topic}"):
                st.markdown(f"**Q:** {item['question']}")
                st.markdown(f"**Your answer:** {item['answer']}")
                st.markdown(
                    f"**Score:** {ev.overall_score}/10  \n"
                    f"Technical {ev.technical_accuracy} | "
                    f"Completeness {ev.completeness} | "
                    f"Clarity {ev.clarity} | "
                    f"Depth {ev.depth} | "
                    f"Communication {ev.communication}"
                )
                st.markdown(f"**Strengths:** {', '.join(ev.strengths) or '—'}")
                st.markdown(f"**Missed points:** {', '.join(ev.missed_points) or '—'}")
                st.markdown(f"**Feedback:** {ev.feedback_summary}")
                st.markdown(
                    f"**Planner:** next difficulty `{plan.next_difficulty}`, "
                    f"focus `{plan.focus_topic}`. {plan.rationale}"
                )


if __name__ == "__main__":
    main()

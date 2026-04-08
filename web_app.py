from __future__ import annotations

from pathlib import Path

import streamlit as st

from interview_helper.agents import evaluator_agent, round_batch_agent
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
    if "history" not in st.session_state:
        st.session_state.history = []
    if "last_error" not in st.session_state:
        st.session_state.last_error = ""
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "interview_type" not in st.session_state:
        st.session_state.interview_type = "Technical"
    if "profile_complete" not in st.session_state:
        st.session_state.profile_complete = False
    if "round_size" not in st.session_state:
        st.session_state.round_size = 5
    if "round_items" not in st.session_state:
        st.session_state.round_items = []
    if "round_json_raw" not in st.session_state:
        st.session_state.round_json_raw = ""
    if "round_index" not in st.session_state:
        st.session_state.round_index = 0
    if "user_answers" not in st.session_state:
        st.session_state.user_answers = []
    if "show_reference" not in st.session_state:
        st.session_state.show_reference = False
    if "answer_draft" not in st.session_state:
        st.session_state.answer_draft = ""


def _generate_round() -> None:
    n = st.session_state.round_size
    items, raw = round_batch_agent(
        role=st.session_state.session.role,
        interview_type=st.session_state.interview_type,
        topic=st.session_state.topic,
        difficulty=st.session_state.difficulty,
        count=n,
    )
    st.session_state.round_items = [i.model_dump() for i in items]
    st.session_state.round_json_raw = raw
    st.session_state.round_index = 0
    st.session_state.user_answers = [""] * n
    st.session_state.show_reference = False
    st.session_state.answer_draft = ""
    st.session_state.last_error = ""


def _evaluate_round() -> None:
    items = st.session_state.round_items
    answers = st.session_state.user_answers
    n = st.session_state.round_size
    if len(items) != n or len(answers) != n:
        st.session_state.last_error = "Generate a full round first."
        return
    missing = [i + 1 for i, a in enumerate(answers) if not str(a).strip()]
    if missing:
        st.session_state.last_error = f"Answer all questions before evaluating. Missing: {missing}"
        return

    for i in range(n):
        q = items[i]["question"]
        ua = str(answers[i]).strip()
        ref = items[i].get("reference_answer", "")
        ev = evaluator_agent(question=q, answer=ua)
        plan = plan_next(ev, st.session_state.session, default_topic=st.session_state.topic)
        update_memory(ev, st.session_state.session, plan.focus_topic)

        st.session_state.difficulty = plan.next_difficulty
        st.session_state.topic = plan.focus_topic
        st.session_state.last_hint = ev.feedback_summary[:400]
        st.session_state.history.append(
            {
                "question": q,
                "answer": ua,
                "correct_answer": ref,
                "evaluation": ev,
                "plan": plan,
            }
        )

    st.session_state.round_items = []
    st.session_state.round_json_raw = ""
    st.session_state.round_index = 0
    st.session_state.user_answers = []
    st.session_state.show_reference = False
    st.session_state.answer_draft = ""
    st.session_state.last_error = ""
    save_session(SESSION_FILE, st.session_state.session)


def _reset_all() -> None:
    role = st.session_state.session.role if "session" in st.session_state else "Software Engineer"
    st.session_state.session = SessionSnapshot(role=role)
    st.session_state.difficulty = "medium"
    st.session_state.topic = "data structures and algorithms"
    st.session_state.last_hint = ""
    st.session_state.history = []
    st.session_state.last_error = ""
    st.session_state.profile_complete = False
    st.session_state.round_items = []
    st.session_state.round_json_raw = ""
    st.session_state.round_index = 0
    st.session_state.user_answers = []
    st.session_state.show_reference = False
    st.session_state.answer_draft = ""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def main() -> None:
    st.set_page_config(page_title="Agentic Interview Helper", page_icon="🎯", layout="wide")
    st.title("🎯 Agentic Interview Helper")
    st.caption("Batch JSON round → step through questions → evaluate after the round")

    _ensure_state()

    if not st.session_state.profile_complete:
        st.subheader("Start Interview Session")
        with st.form("onboarding_form"):
            user_name = st.text_input("Your name")
            role = st.text_input("Role you are interviewing for", value="Software Engineer")
            interview_type = st.selectbox(
                "Type of interview help",
                options=["Technical", "Behavioral", "System Design", "General"],
                index=0,
            )
            topic = st.text_input("Starting topic (optional)", value="data structures and algorithms")
            submitted = st.form_submit_button("Start")
        if submitted:
            st.session_state.user_name = user_name.strip()
            st.session_state.session.role = role.strip() or "Software Engineer"
            st.session_state.interview_type = interview_type
            st.session_state.topic = topic.strip() or "data structures and algorithms"
            st.session_state.profile_complete = True
            st.session_state.last_error = ""
            save_session(SESSION_FILE, st.session_state.session)
            st.rerun()
        return

    with st.sidebar:
        st.header("Session Setup")
        role = st.text_input("Target role", value=st.session_state.session.role)
        topic = st.text_input("Starting topic", value=st.session_state.topic)
        interview_options = ["Technical", "Behavioral", "System Design", "General"]
        current_type = (
            st.session_state.interview_type
            if st.session_state.interview_type in interview_options
            else "Technical"
        )
        interview_type = st.selectbox(
            "Interview type",
            options=interview_options,
            index=interview_options.index(current_type),
        )
        if st.button("Apply Settings"):
            st.session_state.session.role = role.strip() or "Software Engineer"
            st.session_state.topic = topic.strip() or "data structures and algorithms"
            st.session_state.interview_type = interview_type
            save_session(SESSION_FILE, st.session_state.session)
            st.success("Settings updated.")

        col1, col2 = st.columns(2)
        if col1.button("Generate round (JSON)", use_container_width=True):
            try:
                _generate_round()
                st.session_state.last_error = ""
            except Exception as e:  # pragma: no cover
                st.session_state.last_error = f"Could not generate round: {e}"
        if col2.button("Reset Session", use_container_width=True):
            _reset_all()
            st.success("Session reset.")

        s: SessionSnapshot = st.session_state.session
        st.divider()
        st.subheader("Memory")
        if st.session_state.user_name:
            st.write(f"Candidate: **{st.session_state.user_name}**")
        st.write(f"Interview type: **{st.session_state.interview_type}**")
        st.write(f"Questions asked: **{s.questions_asked}**")
        st.write(f"Current difficulty: **{st.session_state.difficulty}**")
        st.write(f"Current focus: **{st.session_state.topic}**")
        st.write(f"Weak topics: {', '.join(s.weak_topics) or '—'}")
        st.write(f"Strong topics: {', '.join(s.strong_topics) or '—'}")

        items = st.session_state.round_items
        n = st.session_state.round_size
        if items and len(items) == n:
            st.write(f"Step: **{min(st.session_state.round_index + 1, n)}/{n}**")

    items = st.session_state.round_items
    n = st.session_state.round_size
    idx = st.session_state.round_index

    if st.session_state.round_json_raw:
        with st.expander("Generated JSON (questions + reference answers)", expanded=False):
            st.code(st.session_state.round_json_raw, language="json")
            st.download_button(
                "Download JSON",
                data=st.session_state.round_json_raw.encode("utf-8"),
                file_name="interview_round.json",
                mime="application/json",
            )

    if not items or len(items) != n:
        st.info('Click **Generate round (JSON)** in the sidebar. One LLM call returns all questions and reference answers.')
    elif idx >= n:
        st.success("You finished all questions in this round. Click **Evaluate 5 answers** below.")
        st.text_area(
            "Your answer (last question — already saved)",
            value=st.session_state.answer_draft,
            height=120,
            disabled=True,
            key="answer_done",
        )
    else:
        st.subheader(f"Question {idx + 1} of {n}")
        st.write(items[idx]["question"])

        st.text_area(
            "Your answer",
            key="answer_draft",
            height=180,
            placeholder="Type your interview answer here...",
        )

        c1, c2 = st.columns(2)
        if c1.button("Show answer (from JSON)", disabled=not items):
            st.session_state.show_reference = True
            st.session_state.last_error = ""

        if c2.button("Next question", type="primary"):
            st.session_state.user_answers[idx] = st.session_state.get("answer_draft", "")
            st.session_state.show_reference = False
            st.session_state.round_index = idx + 1
            if st.session_state.round_index < n:
                st.session_state.answer_draft = st.session_state.user_answers[
                    st.session_state.round_index
                ]
            else:
                st.session_state.answer_draft = ""
            st.session_state.last_error = ""

        if st.session_state.show_reference and items and idx < n:
            st.markdown("### Reference answer (from generated JSON)")
            st.write(items[idx]["reference_answer"])

    if items and len(items) == n and idx >= n:
        c_eval, _ = st.columns([1, 3])
        if c_eval.button("Evaluate 5 answers", type="primary", key="eval_bottom"):
            try:
                _evaluate_round()
                st.success("Round evaluated. See detailed feedback below.")
            except Exception as e:  # pragma: no cover
                st.session_state.last_error = f"Evaluation failed: {e}"

    if st.session_state.last_error:
        st.error(st.session_state.last_error)

    if st.session_state.history:
        st.subheader("Interview History")
        for idx_h, item in enumerate(reversed(st.session_state.history), start=1):
            ev = item["evaluation"]
            plan = item["plan"]
            with st.expander(f"Round {len(st.session_state.history) - idx_h + 1}: {plan.focus_topic}"):
                st.markdown(f"**Q:** {item['question']}")
                st.markdown(f"**Your answer:** {item['answer']}")
                if item.get("correct_answer"):
                    st.markdown(f"**Reference (from JSON):** {item['correct_answer']}")
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

from __future__ import annotations

import random
from pathlib import Path

import streamlit as st

from interview_helper.behavioral_flashcards import CARDS as BEHAVIORAL_CARDS
from interview_helper.tools_runtime import (
    extract_jd_keywords,
    generate_followup_reminder,
    generate_networking_message,
    tailor_resume_bullets,
)
from interview_helper.ui_facts import INTERVIEW_FACTS

from interview_helper.action_router import execute_plan_action, execute_supervisor_tool
from interview_helper.agents import (
    evaluator_agent,
    jury_evaluator_agent,
    reflection_agent,
    round_batch_agent,
    supervisor_tool_agent,
)
from interview_helper.memory import load_session, save_session
from interview_helper.models import SessionSnapshot
from interview_helper.planner import plan_next, update_memory

SESSION_FILE = Path(".interview_session.json")


def _answer_draft_key(idx: int) -> str:
    """Per-question key so Streamlit does not block updates after `text_area` mounts."""
    return f"answer_draft_q{idx}"


def _clear_answer_draft_keys() -> None:
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith("answer_draft_q"):
            st.session_state.pop(k, None)


def _sync_drafts_to_user_answers() -> None:
    """Copy every visible `text_area` draft into `user_answers` (fixes missing slots if Next was skipped)."""
    n = int(st.session_state.round_size)
    items = st.session_state.round_items
    if not items or len(items) != n:
        return
    ua = list(st.session_state.user_answers or [])
    if len(ua) < n:
        ua.extend([""] * (n - len(ua)))
    else:
        ua = ua[:n]
    for i in range(n):
        dk = _answer_draft_key(i)
        if dk in st.session_state:
            ua[i] = str(st.session_state[dk]).strip()
    st.session_state.user_answers = ua


def _filled_answer_count() -> tuple[int, int]:
    """How many non-empty answers we have (draft widget or saved list)."""
    n = int(st.session_state.round_size)
    items = st.session_state.round_items
    if not items or len(items) != n:
        return (0, max(n, 1))
    c = 0
    for j in range(n):
        dk = _answer_draft_key(j)
        if dk in st.session_state and str(st.session_state[dk]).strip():
            c += 1
        elif j < len(st.session_state.user_answers) and str(st.session_state.user_answers[j]).strip():
            c += 1
    return (c, n)


def _inject_app_styles() -> None:
    """Typography + light-touch CSS. Theme colors come from .streamlit/config.toml."""
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400..700;1,400..700&display=swap" rel="stylesheet" />
        <style>
        /* App shell: readable line length on wide screens */
        .block-container {
            font-family: "Plus Jakarta Sans", ui-sans-serif, system-ui, sans-serif;
            max-width: 1100px;
            padding-top: 1.25rem;
        }
        /* Do not blanket-override Streamlit widget colors (breaks contrast & a11y) */

        .app-hero {
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 45%, #4f46e5 100%);
            color: #f8fafc;
            border-radius: 16px;
            padding: 1.35rem 1.5rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 12px 40px rgba(37, 99, 235, 0.22);
        }
        .app-hero h1 {
            font-size: 1.65rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin: 0 0 0.35rem 0;
            line-height: 1.2;
        }
        .app-hero p {
            margin: 0;
            opacity: 0.95;
            font-size: 0.98rem;
            line-height: 1.45;
        }
        .app-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 1rem 1.15rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
        }
        .app-muted {
            color: #475569;
            font-size: 0.9rem;
        }
        .app-kicker {
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #64748b;
        }
        /* Accessible focus for keyboard users (Streamlit buttons are <button>) */
        button:focus-visible {
            outline: 2px solid #2563eb !important;
            outline-offset: 2px !important;
        }
        a:focus-visible {
            outline: 2px solid #2563eb;
            outline-offset: 2px;
        }
        /* Sidebar breathing room */
        [data-testid="stSidebar"] {
            border-right: 1px solid #e2e8f0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_career_copilot_panel() -> None:
    st.markdown("### Career Copilot Workspace")
    st.caption("End-to-end support: job description analysis, resume tailoring, networking outreach, and follow-up planning.")
    tab_r, tab_n, tab_a = st.tabs(["Resume Tailor", "Networking", "Application Tracker"])

    with tab_r:
        jd = st.text_area(
            "Job description",
            value=st.session_state.session.active_job_description,
            height=130,
            key="career_jd",
            placeholder="Paste a target job description here...",
        )
        bullets_raw = st.text_area(
            "Resume bullets (one per line)",
            key="resume_bullets",
            height=130,
            placeholder="Built API for payments\nReduced latency by 35%\nLed migration to cloud",
        )
        c1, c2 = st.columns(2)
        if c1.button("Analyze JD keywords", use_container_width=True):
            st.session_state.session.active_job_description = jd
            kws = extract_jd_keywords(job_description=jd, top_k=12)
            st.write(", ".join(kws) if kws else "No keywords found yet.")
            save_session(SESSION_FILE, st.session_state.session)
        if c2.button("Tailor bullets", use_container_width=True):
            src = [x.strip() for x in bullets_raw.splitlines() if x.strip()]
            if not src or not jd.strip():
                st.warning("Add both a job description and resume bullets.")
            else:
                tailored = tailor_resume_bullets(resume_bullets=src, job_description=jd)
                st.markdown("**Tailored bullets**")
                for b in tailored:
                    st.markdown(f"- {b}")

    with tab_n:
        name = st.text_input("Your name", value=st.session_state.user_name or "Candidate", key="net_name")
        company = st.text_input("Target company", key="net_company")
        role = st.text_input("Target role", value=st.session_state.session.role, key="net_role")
        shared = st.text_input("Shared context (optional)", key="net_shared", placeholder="same alumni group, mutual contact, same meetup")
        if st.button("Generate outreach message", use_container_width=True):
            msg = generate_networking_message(
                candidate_name=name,
                target_role=role,
                company=company or "the company",
                shared_context=shared,
            )
            st.markdown("**Draft message**")
            st.write(msg)
            if company.strip() and company not in st.session_state.session.target_companies:
                st.session_state.session.target_companies.append(company.strip())
            st.session_state.session.outreach_history.append(msg)
            st.session_state.session.outreach_history = st.session_state.session.outreach_history[-20:]
            save_session(SESSION_FILE, st.session_state.session)

    with tab_a:
        a_company = st.text_input("Company", key="app_company")
        a_role = st.text_input("Role", value=st.session_state.session.role, key="app_role")
        days = st.number_input("Days since applied", min_value=0, max_value=90, value=7, step=1, key="app_days")
        if st.button("Generate follow-up reminder", use_container_width=True):
            reminder = generate_followup_reminder(company=a_company or "company", role=a_role, days_since_apply=int(days))
            st.info(reminder)
            st.session_state.session.application_log.append(reminder)
            st.session_state.session.application_log = st.session_state.session.application_log[-30:]
            save_session(SESSION_FILE, st.session_state.session)
        if st.session_state.session.application_log:
            st.markdown("**Recent follow-ups**")
            for item in reversed(st.session_state.session.application_log[-5:]):
                st.markdown(f"- {item}")


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
    if "user_answers" not in st.session_state:
        st.session_state.user_answers = []
    if "jury_mode" not in st.session_state:
        st.session_state.jury_mode = True
    if "tool_logs" not in st.session_state:
        st.session_state.tool_logs = []
    if "enable_tools" not in st.session_state:
        st.session_state.enable_tools = True
    if "enable_reflection" not in st.session_state:
        st.session_state.enable_reflection = True


def _generate_round() -> None:
    n = st.session_state.round_size
    items, raw = round_batch_agent(
        role=st.session_state.session.role,
        interview_type=st.session_state.interview_type,
        topic=st.session_state.topic,
        difficulty=st.session_state.difficulty,
        count=n,
        question_style=st.session_state.session.preferred_question_style,
    )
    st.session_state.round_items = [i.model_dump() for i in items]
    st.session_state.round_json_raw = raw
    st.session_state.user_answers = [""] * n
    _clear_answer_draft_keys()
    st.session_state.last_error = ""


def _evaluate_round() -> None:
    _sync_drafts_to_user_answers()
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
        if st.session_state.jury_mode:
            strict_ev, clarity_ev, ev, jury_summary = jury_evaluator_agent(question=q, answer=ua)
        else:
            ev = evaluator_agent(question=q, answer=ua)
            strict_ev = ev
            clarity_ev = ev
            jury_summary = "Single evaluator mode."
        plan = plan_next(ev, st.session_state.session, default_topic=st.session_state.topic)
        update_memory(ev, st.session_state.session, plan.focus_topic)
        intervention = execute_plan_action(plan, st.session_state.session)
        if st.session_state.enable_reflection:
            pattern, style, strategy = reflection_agent(
                topic=st.session_state.topic,
                question=q,
                answer=ua,
                feedback=ev.feedback_summary,
            )
            st.session_state.session.preferred_question_style = style
        else:
            pattern, style, strategy = "Reflection disabled", st.session_state.session.preferred_question_style, ""

        if st.session_state.enable_tools:
            tool_name, tool_reason = supervisor_tool_agent(
                topic=st.session_state.topic,
                missed_points=ev.missed_points,
                score=ev.overall_score,
            )
            tool_output = execute_supervisor_tool(
                tool_name=tool_name,
                session=st.session_state.session,
                topic=st.session_state.topic,
                missed_points=ev.missed_points,
                question=q,
                answer=ua,
                interview_type=st.session_state.interview_type,
            )
        else:
            tool_name, tool_reason, tool_output = "none", "Tools disabled", ""
        if st.session_state.session.reflections:
            st.session_state.session.reflections[-1].intervention_used = plan.action
            st.session_state.session.reflections[-1].mistake_pattern = pattern
            st.session_state.session.reflections[-1].recommended_style = style

        st.session_state.difficulty = plan.next_difficulty
        st.session_state.topic = plan.focus_topic
        st.session_state.last_hint = ev.feedback_summary[:400]
        if st.session_state.enable_tools:
            st.session_state.tool_logs.append(
                {
                    "tool": tool_name,
                    "reason": tool_reason,
                    "output": tool_output,
                }
            )
        st.session_state.history.append(
            {
                "question": q,
                "answer": ua,
                "correct_answer": ref,
                "evaluation": ev,
                "strict_evaluation": strict_ev,
                "clarity_evaluation": clarity_ev,
                "jury_summary": jury_summary,
                "plan": plan,
                "intervention": intervention,
                "tool_name": tool_name,
                "tool_reason": tool_reason,
                "tool_output": tool_output,
                "reflection_pattern": pattern,
                "reflection_style": style,
                "reflection_strategy": strategy,
            }
        )

    st.session_state.round_items = []
    st.session_state.round_json_raw = ""
    st.session_state.user_answers = []
    _clear_answer_draft_keys()
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
    st.session_state.user_answers = []
    _clear_answer_draft_keys()
    st.session_state.jury_mode = True
    st.session_state.tool_logs = []
    st.session_state.enable_tools = True
    st.session_state.enable_reflection = True
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def _render_behavioral_flashcards() -> None:
    """Offline STAR-style flashcards when interview focus is Behavioral."""
    if "bf_card_idx" not in st.session_state:
        st.session_state.bf_card_idx = 0
    n_cards = len(BEHAVIORAL_CARDS)
    i = int(st.session_state.bf_card_idx) % n_cards
    card = BEHAVIORAL_CARDS[i]

    with st.expander("Behavioral flashcards — quick practice (offline)", expanded=False):
        st.caption(f"Card {i + 1} of {n_cards} · tap Next to rotate prompts")
        st.markdown(f"**Prompt:** {card['prompt']}")
        if st.checkbox("Show framework & checklist", value=False, key="bf_show_back"):
            st.info(card["framework"])
            st.caption(card["checklist"])
        c_prev, c_next = st.columns(2)
        if c_prev.button("← Previous", key="bf_prev", use_container_width=True):
            st.session_state.bf_card_idx = (i - 1) % n_cards
        if c_next.button("Next →", key="bf_next", use_container_width=True):
            st.session_state.bf_card_idx = (i + 1) % n_cards


def _render_generation_panel() -> bool:
    """Full-width loading experience (not the tiny default spinner). Returns True on success."""
    role = st.session_state.session.role
    itype = st.session_state.interview_type
    topic = st.session_state.topic
    n = int(st.session_state.round_size)

    st.markdown("### Generating your round")
    st.caption(
        f"Planner context: **{role}** · **{itype}** · focus **{topic}** · **{n}** questions."
    )

    fact_pool = list(INTERVIEW_FACTS)
    random.shuffle(fact_pool)
    picks = fact_pool[: min(5, len(fact_pool))]

    ok = False
    col_left, col_right = st.columns([1.1, 1], gap="large")
    with col_left:
        with st.status("Batch generator running — this may take several minutes…", expanded=True) as status:
            status.write(
                "The **batch agent** is writing questions and concise reference answers in one structured JSON response."
            )
            status.write(
                f"**Supervisor context:** align with your interview type (**{itype}**) and calibrate difficulty to "
                f"**{st.session_state.difficulty}**."
            )
            prog = st.progress(0, text="Starting generation…")
            try:
                _generate_round()
                prog.progress(100, text="Round ready")
                status.update(label="Done — loading your workspace…", state="complete")
                ok = True
            except Exception as e:  # pragma: no cover
                st.session_state.last_error = f"Could not generate round: {e}"
                status.update(label="Generation failed", state="error")

    with col_right:
        st.markdown("##### While you wait")
        st.markdown("Quick, practical interview tips (rotated each run):")
        for line in picks:
            st.markdown(f"- {line}")
        st.info(
            "Tip: generation time depends on your local model and round size. "
            "Smaller rounds finish faster.",
            icon="⏱️",
        )
    return ok


def main() -> None:
    st.set_page_config(
        page_title="Career Preparation Copilot",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_app_styles()

    st.markdown(
        """
        <div class="app-hero" role="region" aria-label="App introduction">
            <h1>Agentic Career Preparation Copilot</h1>
            <p>End-to-end workflow: resume tailoring, networking outreach, interview coaching, and follow-up planning.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _ensure_state()

    if not st.session_state.profile_complete:
        st.markdown('<p class="app-kicker">Welcome</p>', unsafe_allow_html=True)
        st.markdown("### Start your session")
        st.caption("Tell us who you are and what you are preparing for. You can change this later in the sidebar.")

        _, mid, _ = st.columns([1, 2.2, 1])
        with mid:
            with st.container(border=True):
                with st.form("onboarding_form"):
                    user_name = st.text_input("Your name", placeholder="e.g. Alex")
                    role = st.text_input("Role you are interviewing for", value="Software Engineer")
                    interview_type = st.selectbox(
                        "Interview focus",
                        options=["Technical", "Behavioral", "System Design", "General"],
                        index=0,
                    )
                    topic = st.text_input(
                        "Starting topic (optional)",
                        value="data structures and algorithms",
                    )
                    submitted = st.form_submit_button("Continue", type="primary", use_container_width=True)
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

    if st.session_state.pop("_run_generate_round", False):
        if _render_generation_panel():
            st.toast("Round ready — answer the questions below.", icon="🎯")
            st.rerun()

    with st.sidebar:
        st.markdown('<p class="app-kicker">Session</p>', unsafe_allow_html=True)
        st.markdown("### Settings")
        role = st.text_input("Target role", value=st.session_state.session.role, key="sb_role")
        topic = st.text_input("Starting topic", value=st.session_state.topic, key="sb_topic")
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
            key="sb_type",
        )
        st.session_state.round_size = st.number_input(
            "Questions per round",
            min_value=1,
            max_value=10,
            value=int(st.session_state.round_size),
            step=1,
            help="How many questions to generate in one batch.",
        )

        st.divider()
        st.markdown('<p class="app-kicker">Agent behavior</p>', unsafe_allow_html=True)
        st.session_state.jury_mode = st.toggle(
            "Jury evaluation",
            value=st.session_state.jury_mode,
            help="Two evaluators (strict + clarity) combined into one final score.",
        )
        st.session_state.enable_tools = st.toggle(
            "Supervisor tools",
            value=st.session_state.enable_tools,
            help="LLM picks a tool each turn (explainer, drill, templates, etc.).",
        )
        st.session_state.enable_reflection = st.toggle(
            "Reflection loop",
            value=st.session_state.enable_reflection,
            help="Diagnose patterns and adjust question style for the next round.",
        )

        st.divider()
        c_apply = st.columns(1)[0]
        if c_apply.button("Save settings", use_container_width=True, type="secondary"):
            st.session_state.session.role = role.strip() or "Software Engineer"
            st.session_state.topic = topic.strip() or "data structures and algorithms"
            st.session_state.interview_type = interview_type
            save_session(SESSION_FILE, st.session_state.session)
            st.success("Saved.")

        col1, col2 = st.columns(2)
        if col1.button("Generate round", use_container_width=True, type="primary"):
            st.session_state._run_generate_round = True
            st.session_state.last_error = ""
        if col2.button("Reset", use_container_width=True):
            _reset_all()
            st.success("Session reset.")

        s: SessionSnapshot = st.session_state.session
        st.divider()
        st.markdown('<p class="app-kicker">Progress</p>', unsafe_allow_html=True)
        if st.session_state.user_name:
            st.write(f"**{st.session_state.user_name}** · {st.session_state.interview_type}")
        else:
            st.write(f"**Candidate** · {st.session_state.interview_type}")
        st.metric("Questions completed", s.questions_asked)
        st.metric("Difficulty", st.session_state.difficulty.capitalize())
        st.caption(f"Focus: **{st.session_state.topic}**")
        st.caption(f"Question style: **{s.preferred_question_style}**")
        st.caption(f"Target **{s.target_score}/10** · Goal {'reached' if s.completed else 'in progress'}")
        st.caption("Weak: " + (", ".join(s.weak_topics) or "—"))
        st.caption("Strong: " + (", ".join(s.strong_topics) or "—"))

        items_sb = st.session_state.round_items
        n_sb = st.session_state.round_size
        if items_sb and len(items_sb) == n_sb:
            filled_sb, _ = _filled_answer_count()
            st.progress(
                filled_sb / n_sb if n_sb else 0.0,
                text=f"Draft progress: {filled_sb} / {n_sb} answers",
            )

    items = st.session_state.round_items
    n = st.session_state.round_size

    if st.session_state.interview_type == "Behavioral":
        _render_behavioral_flashcards()

    _render_career_copilot_panel()

    if st.session_state.round_json_raw:
        with st.expander("Generated JSON (export)", expanded=False):
            st.code(st.session_state.round_json_raw, language="json")
            st.download_button(
                "Download JSON",
                data=st.session_state.round_json_raw.encode("utf-8"),
                file_name="interview_round.json",
                mime="application/json",
                use_container_width=True,
            )

    if not items or len(items) != n:
        st.info(
            "Select **Generate round** in the sidebar. One model call creates every question and a short reference answer."
        )
    else:
        # All questions on one page so every `text_area` stays mounted — drafts are not dropped when "Next" unmounts widgets.
        st.markdown('<p class="app-kicker">This round</p>', unsafe_allow_html=True)
        st.caption(
            f"**{n}** questions · difficulty **{st.session_state.difficulty}** · style **{st.session_state.session.preferred_question_style}**"
        )
        filled, _ = _filled_answer_count()
        st.caption(f"Non-empty answers: **{filled}** / {n}")

        for j in range(n):
            dk = _answer_draft_key(j)
            if dk not in st.session_state:
                ua0 = st.session_state.user_answers
                init = (ua0[j] if j < len(ua0) else "") or ""
                st.session_state[dk] = init

            with st.container(border=True):
                st.markdown(f"#### Question {j + 1} of {n}")
                st.markdown(items[j]["question"])
                st.text_area(
                    "Your answer",
                    key=dk,
                    height=180,
                    placeholder="Write your answer as you would in a real interview…",
                    label_visibility="visible",
                )
                with st.expander("Reference answer (from batch)", expanded=False):
                    st.write(items[j].get("reference_answer", ""))

        st.divider()
        eval_label = f"Evaluate {n} answers"
        if st.button(eval_label, type="primary", key="eval_bottom", use_container_width=True):
            try:
                _sync_drafts_to_user_answers()
                _evaluate_round()
                st.success("Evaluation complete — see history below.")
            except Exception as e:  # pragma: no cover
                st.session_state.last_error = f"Evaluation failed: {e}"

    if st.session_state.last_error:
        st.error(st.session_state.last_error)

    if st.session_state.history:
        recent_score = st.session_state.history[-1]["evaluation"].overall_score
        tgt = max(st.session_state.session.target_score, 1.0)
        progress = min(int((recent_score / tgt) * 100), 100)
        st.markdown('<p class="app-kicker">Snapshot</p>', unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Latest score", f"{recent_score:.1f} / 10")
        m2.metric("Questions graded", str(st.session_state.session.questions_asked))
        m3.metric("Toward goal", f"{progress}%")
        st.progress(progress / 100.0, text=f"Target: {st.session_state.session.target_score}/10")

    if st.session_state.history:
        st.divider()
        st.markdown("### History")
        st.caption("Each entry includes scores, jury breakdown, reflection, and planner + tool output.")

        for idx_h, item in enumerate(reversed(st.session_state.history), start=1):
            ev = item["evaluation"]
            plan = item["plan"]
            title = f"Q{len(st.session_state.history) - idx_h + 1}: {plan.focus_topic[:48]}{'…' if len(plan.focus_topic) > 48 else ''}"
            with st.expander(title, expanded=False):
                tab_a, tab_b, tab_c = st.tabs(["Overview", "Jury", "Planner & tools"])
                with tab_a:
                    st.markdown(f"**Question**  \n{item['question']}")
                    st.markdown(f"**Your answer**  \n{item['answer']}")
                    if item.get("correct_answer"):
                        st.markdown(f"**Reference**  \n{item['correct_answer']}")
                    st.markdown(
                        f"**Score {ev.overall_score}/10** — technical {ev.technical_accuracy}, "
                        f"completeness {ev.completeness}, clarity {ev.clarity}, "
                        f"depth {ev.depth}, communication {ev.communication}"
                    )
                    st.markdown(f"**Strengths:** {', '.join(ev.strengths) or '—'}")
                    st.markdown(f"**Gaps:** {', '.join(ev.missed_points) or '—'}")
                    st.markdown(f"**Feedback:** {ev.feedback_summary}")
                    st.markdown(
                        f"**Reflection:** {item.get('reflection_pattern', '—')} → next style **{item.get('reflection_style', 'balanced')}**. "
                        f"{item.get('reflection_strategy', '')}"
                    )
                with tab_b:
                    st.markdown(f"**Summary:** {item.get('jury_summary', '—')}")
                    if item.get("strict_evaluation") and item.get("clarity_evaluation"):
                        sev = item["strict_evaluation"]
                        cev = item["clarity_evaluation"]
                        j1, j2 = st.columns(2)
                        j1.metric("Strict (correctness)", f"{sev.overall_score}/10")
                        j2.metric("Clarity", f"{cev.overall_score}/10")
                with tab_c:
                    st.markdown(
                        f"**Planner:** `{plan.action}` → difficulty **{plan.next_difficulty}**, focus **{plan.focus_topic}**"
                    )
                    st.caption(plan.rationale)
                    st.markdown(f"**Intervention:** {item.get('intervention', '—')}")
                    st.markdown(f"**Tool:** `{item.get('tool_name', 'none')}` — {item.get('tool_reason', '—')}")
                    st.markdown(f"**Tool output:** {item.get('tool_output', '—')}")


if __name__ == "__main__":
    main()

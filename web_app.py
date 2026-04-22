from __future__ import annotations

from pathlib import Path

import streamlit as st

from interview_helper.behavioral_flashcards import CARDS as BEHAVIORAL_CARDS
from interview_helper.tools_runtime import (
    extract_jd_keywords,
    generate_followup_reminder,
    generate_networking_message,
    tailor_resume_bullets,
)

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
    """Typography + layout CSS. Theme colors come from .streamlit/config.toml."""
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400..700;1,9..40,400..700&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
        <style>
        .block-container {
            font-family: "DM Sans", "Instrument Sans", ui-sans-serif, system-ui, sans-serif;
            max-width: 1120px;
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
            box-sizing: border-box;
        }
        h1, h2, h3 { letter-spacing: -0.02em; }
        .stApp {
            background:
                radial-gradient(1200px 600px at 8% -10%, rgba(59, 130, 246, 0.10), transparent 42%),
                radial-gradient(900px 500px at 92% -12%, rgba(99, 102, 241, 0.10), transparent 40%),
                #f6f8fc;
        }

        .app-hero {
            background: linear-gradient(130deg, #0b132b 0%, #1d4ed8 48%, #4338ca 100%);
            color: #f1f5f9;
            border-radius: 20px;
            padding: 1.5rem 1.65rem;
            margin-bottom: 1.35rem;
            box-shadow: 0 18px 38px rgba(37, 99, 235, 0.26);
            border: 1px solid rgba(255, 255, 255, 0.14);
            width: 100%;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
            isolation: isolate;
            animation: heroFloat 9s ease-in-out infinite;
        }
        .app-hero::before {
            content: "";
            position: absolute;
            inset: -55% -30% auto auto;
            width: 260px;
            height: 260px;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.20) 0%, rgba(255, 255, 255, 0.0) 70%);
            pointer-events: none;
            z-index: -1;
        }
        @keyframes heroFloat {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-3px); }
        }
        .app-hero h1 {
            font-family: "Instrument Sans", "DM Sans", sans-serif;
            font-size: 1.75rem;
            font-weight: 700;
            margin: 0 0 0.4rem 0;
            line-height: 1.2;
        }
        .app-hero p {
            margin: 0;
            opacity: 0.92;
            font-size: 1rem;
            line-height: 1.5;
            max-width: 52rem;
        }
        .app-hero-badge {
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #c7d2fe;
            margin-bottom: 0.5rem;
        }
        .app-feature-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.65rem;
            margin: 0.65rem 0 0.1rem;
        }
        .app-feature-pill {
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 12px;
            padding: 0.52rem 0.62rem;
            font-size: 0.84rem;
            color: #e2e8f0;
            backdrop-filter: blur(6px);
            -webkit-backdrop-filter: blur(6px);
            line-height: 1.3;
        }
        .app-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 1.1rem 1.25rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
        }
        .app-muted { color: #64748b; font-size: 0.92rem; }
        .app-kicker {
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            color: #64748b;
        }
        button:focus-visible {
            outline: 2px solid #6366f1 !important;
            outline-offset: 2px !important;
        }
        a:focus-visible { outline: 2px solid #6366f1; outline-offset: 2px; }
        [data-testid="stSidebar"] {
            border-right: 1px solid #e2e8f0;
            background: linear-gradient(180deg, #fafafa 0%, #ffffff 100%);
        }
        div[data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 14px;
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            padding: 0.65rem;
        }
        div[data-testid="stForm"] .stTextInput > label {
            font-weight: 600;
            color: #334155;
        }
        .stButton > button[kind="primaryFormSubmit"],
        .stButton > button[kind="primary"] {
            border-radius: 12px !important;
            border: 1px solid #1d4ed8 !important;
            background: linear-gradient(140deg, #2563eb 0%, #4338ca 100%) !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.22);
            transition: transform 120ms ease, box-shadow 120ms ease;
        }
        .stButton > button[kind="primaryFormSubmit"]:hover,
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 14px 28px rgba(37, 99, 235, 0.28);
        }
        .app-onboard-shell {
            max-width: 920px;
            margin: 0 auto;
        }
        .app-onboard-lead {
            color: #475569;
            margin: -0.15rem 0 1rem 0;
        }
        .app-subtle-note {
            color: #64748b;
            font-size: 0.86rem;
            margin-top: 0.55rem;
        }
        .app-inner-hero {
            background: linear-gradient(140deg, rgba(29, 78, 216, 0.10), rgba(67, 56, 202, 0.10));
            border: 1px solid rgba(99, 102, 241, 0.18);
            border-radius: 14px;
            padding: 0.85rem 1rem;
            margin: 0.35rem 0 0.75rem 0;
        }
        .app-inner-hero p {
            margin: 0.2rem 0 0 0;
            color: #475569;
            font-size: 0.93rem;
        }
        .app-inner-hero strong {
            color: #1e293b;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 14px !important;
            border-color: rgba(148, 163, 184, 0.28) !important;
            background: rgba(255, 255, 255, 0.78);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
        }
        div[data-testid="stExpander"] {
            border: 1px solid rgba(148, 163, 184, 0.28) !important;
            border-radius: 12px !important;
            background: rgba(255, 255, 255, 0.84);
        }
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 12px;
            padding: 0.5rem 0.6rem;
        }
        [data-baseweb="button-group"] {
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 12px;
            padding: 0.2rem;
        }
        [data-baseweb="button-group"] button[aria-pressed="true"] {
            background: linear-gradient(140deg, #2563eb 0%, #4338ca 100%) !important;
            color: #ffffff !important;
            border-radius: 10px !important;
        }
        @media (max-width: 768px) {
            .block-container {
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }
            .app-hero {
                border-radius: 14px;
                padding: 1.1rem 1rem;
            }
            .app-hero h1 {
                font-size: 1.35rem;
            }
            .app-hero p {
                font-size: 0.95rem;
            }
            .app-feature-grid {
                grid-template-columns: 1fr;
                gap: 0.5rem;
            }
        }
        /* Tab strip polish */
        [data-baseweb="tab-list"] button {
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_career_copilot_panel() -> None:
    st.markdown(
        """
        <div class="app-inner-hero">
            <strong>Career workspace</strong>
            <p>Build application assets quickly: align bullets, draft outreach, and keep follow-ups ready to send.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Paste a job description and your bullets, or draft outreach — outputs stay below until you clear the session."
    )

    tab_r, tab_n, tab_a = st.tabs(["Resume alignment", "Recruiter outreach", "Application follow-up"])

    with tab_r:
        jd = st.text_area(
            "Job description",
            value=st.session_state.session.active_job_description,
            height=160,
            key="career_jd",
            placeholder="Paste the full job description (responsibilities, requirements, stack).",
        )
        bullets_raw = st.text_area(
            "Your bullets (one per line)",
            key="resume_bullets",
            height=160,
            placeholder="Shipped a payments API handling $2M/day\nCut p99 latency by 35% via caching and query tuning\nMentored 2 junior engineers on code review",
        )
        c1, c2 = st.columns(2)
        if c1.button("Extract keywords", use_container_width=True, type="secondary"):
            st.session_state.session.active_job_description = jd
            kws = extract_jd_keywords(job_description=jd, top_k=14)
            st.session_state.career_jd_keywords = kws
            save_session(SESSION_FILE, st.session_state.session)
            st.rerun()
        if c2.button("Tailor bullets to this JD", use_container_width=True, type="primary"):
            src = [x.strip() for x in bullets_raw.splitlines() if x.strip()]
            if not src or not jd.strip():
                st.warning("Add both a job description and at least one bullet.")
            else:
                with st.spinner("Aligning bullets with the job description…"):
                    tailored = tailor_resume_bullets(resume_bullets=src, job_description=jd)
                st.session_state.career_tailored_bullets = tailored
                st.session_state.session.active_job_description = jd
                save_session(SESSION_FILE, st.session_state.session)
                st.rerun()

        if st.session_state.career_jd_keywords:
            st.markdown("**Keywords from the posting**")
            st.caption(", ".join(st.session_state.career_jd_keywords))

        if st.session_state.career_tailored_bullets:
            st.markdown("**Tailored bullets**")
            tailored_text = "\n".join(f"• {b}" for b in st.session_state.career_tailored_bullets)
            for b in st.session_state.career_tailored_bullets:
                st.markdown(f"- {b}")
            st.download_button(
                "Download as .txt",
                data=tailored_text.encode("utf-8"),
                file_name="tailored_resume_bullets.txt",
                mime="text/plain",
                use_container_width=True,
            )

    with tab_n:
        ch = st.selectbox(
            "Format",
            options=["email", "linkedin"],
            format_func=lambda x: "Email (subject + body)" if x == "email" else "LinkedIn (short note)",
            key="outreach_channel",
        )
        name = st.text_input("Your name", value=st.session_state.user_name or "Candidate", key="net_name")
        company = st.text_input("Company", key="net_company", placeholder="e.g. Acme Corp")
        role = st.text_input("Role title", value=st.session_state.session.role, key="net_role")
        shared = st.text_input(
            "Connection detail (optional)",
            key="net_shared",
            placeholder="Referred by Jane Doe, or met at PyConf booth, or alum from UW",
        )
        if st.button("Draft message", use_container_width=True, type="primary"):
            with st.spinner("Drafting a clear subject line and body…"):
                msg = generate_networking_message(
                    candidate_name=name,
                    target_role=role,
                    company=company or "the company",
                    shared_context=shared,
                    channel=ch,
                )
            st.session_state.career_outreach = msg
            hist_line = (
                f"Subject: {msg.get('subject', '')}\n\n{msg.get('body', '')}"
                if msg.get("subject")
                else (msg.get("body") or "")
            )
            if company.strip() and company not in st.session_state.session.target_companies:
                st.session_state.session.target_companies.append(company.strip())
            st.session_state.session.outreach_history.append(hist_line.strip())
            st.session_state.session.outreach_history = st.session_state.session.outreach_history[-20:]
            save_session(SESSION_FILE, st.session_state.session)
            st.rerun()

        out = st.session_state.career_outreach
        if isinstance(out, dict) and out.get("body"):
            subj = (out.get("subject") or "").strip()
            body = (out.get("body") or "").strip()
            if ch == "email" and subj:
                st.markdown("**Subject**")
                st.code(subj, language=None)
            st.markdown("**Message** (copy below)")
            st.code(body, language=None)
            full_copy = f"Subject: {subj}\n\n{body}" if subj else body
            st.download_button(
                "Download message.txt",
                data=full_copy.encode("utf-8"),
                file_name="recruiter_message.txt",
                mime="text/plain",
                use_container_width=True,
            )

    with tab_a:
        a_company = st.text_input("Company", key="app_company")
        a_role = st.text_input("Role", value=st.session_state.session.role, key="app_role")
        days = st.number_input("Days since you applied", min_value=0, max_value=90, value=7, step=1, key="app_days")
        if st.button("Draft follow-up email", use_container_width=True, type="primary"):
            with st.spinner("Drafting follow-up…"):
                reminder = generate_followup_reminder(
                    company=a_company or "the company", role=a_role, days_since_apply=int(days)
                )
            st.session_state.career_followup_last = reminder
            st.session_state.session.application_log.append(reminder)
            st.session_state.session.application_log = st.session_state.session.application_log[-30:]
            save_session(SESSION_FILE, st.session_state.session)
            st.rerun()

        if st.session_state.career_followup_last:
            st.markdown("**Latest draft**")
            st.code(st.session_state.career_followup_last, language=None)
            st.download_button(
                "Download follow-up.txt",
                data=st.session_state.career_followup_last.encode("utf-8"),
                file_name="follow_up_email.txt",
                mime="text/plain",
                use_container_width=True,
            )
        if st.session_state.session.application_log:
            st.markdown("**Recent drafts (saved)**")
            for item in reversed(st.session_state.session.application_log[-5:]):
                preview = (item.replace("\n", " "))[:72] + ("…" if len(item) > 72 else "")
                with st.expander(preview or "Saved draft", expanded=False):
                    st.code(item, language=None)


def _ensure_state() -> None:
    if "session" not in st.session_state:
        persisted = load_session(SESSION_FILE)
        st.session_state.session = persisted or SessionSnapshot(role="Software Engineer")
    if "difficulty" not in st.session_state:
        st.session_state.difficulty = "medium"
    if "topic" not in st.session_state:
        st.session_state.topic = "core interview fundamentals"
    if "last_hint" not in st.session_state:
        st.session_state.last_hint = ""
    if "history" not in st.session_state:
        st.session_state.history = []
    if "last_error" not in st.session_state:
        st.session_state.last_error = ""
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "interview_type" not in st.session_state:
        st.session_state.interview_type = "General"
    if "profile_complete" not in st.session_state:
        st.session_state.profile_complete = False
    if "round_size" not in st.session_state:
        st.session_state.round_size = 3
    if "round_items" not in st.session_state:
        st.session_state.round_items = []
    if "round_json_raw" not in st.session_state:
        st.session_state.round_json_raw = ""
    if "user_answers" not in st.session_state:
        st.session_state.user_answers = []
    if "jury_mode" not in st.session_state:
        st.session_state.jury_mode = False
    if "tool_logs" not in st.session_state:
        st.session_state.tool_logs = []
    if "enable_tools" not in st.session_state:
        st.session_state.enable_tools = True
    if "enable_reflection" not in st.session_state:
        st.session_state.enable_reflection = True
    if "career_jd_keywords" not in st.session_state:
        st.session_state.career_jd_keywords = []
    if "career_tailored_bullets" not in st.session_state:
        st.session_state.career_tailored_bullets = []
    if "career_outreach" not in st.session_state:
        st.session_state.career_outreach = None
    if "career_followup_last" not in st.session_state:
        st.session_state.career_followup_last = ""


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
    st.session_state.topic = "core interview fundamentals"
    st.session_state.last_hint = ""
    st.session_state.history = []
    st.session_state.last_error = ""
    st.session_state.profile_complete = False
    st.session_state.round_items = []
    st.session_state.round_json_raw = ""
    st.session_state.user_answers = []
    _clear_answer_draft_keys()
    st.session_state.jury_mode = False
    st.session_state.tool_logs = []
    st.session_state.enable_tools = True
    st.session_state.enable_reflection = True
    st.session_state.career_jd_keywords = []
    st.session_state.career_tailored_bullets = []
    st.session_state.career_outreach = None
    st.session_state.career_followup_last = ""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def _bf_shift(delta: int) -> None:
    n_cards = len(BEHAVIORAL_CARDS)
    cur = int(st.session_state.get("bf_card_idx", 0))
    st.session_state.bf_card_idx = (cur + delta) % n_cards


def _render_behavioral_flashcards() -> None:
    """Offline STAR-style flashcards when interview focus is Behavioral."""
    if "bf_card_idx" not in st.session_state:
        st.session_state.bf_card_idx = 0
    n_cards = len(BEHAVIORAL_CARDS)
    i = int(st.session_state.bf_card_idx) % n_cards
    card = BEHAVIORAL_CARDS[i]

    with st.expander("Behavioral flashcards — offline STAR practice", expanded=False):
        st.caption(f"Card {i + 1} of {n_cards} · use Previous / Next")
        st.markdown(f"**Prompt:** {card['prompt']}")
        if st.checkbox("Show framework & checklist", value=False, key="bf_show_back"):
            st.info(card["framework"])
            st.caption(card["checklist"])
        c_prev, c_next = st.columns(2)
        c_prev.button("← Previous", key="bf_prev", use_container_width=True, on_click=_bf_shift, args=(-1,))
        c_next.button("Next →", key="bf_next", use_container_width=True, on_click=_bf_shift, args=(1,))


def _render_generation_panel() -> bool:
    """One focused column: local LLM calls are the bottleneck, not layout."""
    role = st.session_state.session.role
    itype = st.session_state.interview_type
    topic = st.session_state.topic
    n = int(st.session_state.round_size)

    st.markdown("### Generating interview round")
    st.caption(
        f"**{role}** · **{itype}** · **{topic}** · **{n}** questions · difficulty **{st.session_state.difficulty}**"
    )
    st.caption(
        "Tip: smaller question counts and a faster local model (or API) reduce wait time. "
        "Evaluation is faster with **Jury** off in the sidebar."
    )

    ok = False
    with st.status("Calling the batch model — usually the slowest step…", expanded=True) as status:
        status.write("One request asks for every question plus short reference answers (JSON).")
        prog = st.progress(0, text="Starting…")
        try:
            _generate_round()
            prog.progress(100, text="Done")
            status.update(label="Round ready", state="complete")
            ok = True
        except Exception as e:  # pragma: no cover
            st.session_state.last_error = f"Could not generate round: {e}"
            status.update(label="Generation failed", state="error")
    return ok


def main() -> None:
    st.set_page_config(
        page_title="Career Preparation Copilot",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_app_styles()

    _ensure_state()
    # Product decision: keep interview mode auto-managed for a cleaner UX.
    st.session_state.interview_type = "General"

    if not st.session_state.profile_complete:
        st.markdown('<div class="app-onboard-shell">', unsafe_allow_html=True)
        st.markdown("## Agentic Career Preparation Copilot")
        st.markdown(
            """
            <div class="app-hero" role="region" aria-label="Welcome">
                <div class="app-hero-badge">Practice • Tailor • Outreach</div>
                <h1>Build interview confidence faster</h1>
                <p>Generate realistic interview rounds, get structured feedback, tailor your resume to a target job, and draft recruiter-ready messages from one workspace.</p>
                <div class="app-feature-grid">
                    <div class="app-feature-pill">Adaptive interview rounds</div>
                    <div class="app-feature-pill">Resume bullet tailoring</div>
                    <div class="app-feature-pill">Recruiter-ready outreach drafts</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<p class="app-onboard-lead">Quick start: add your name + role, then choose your workspace.</p>', unsafe_allow_html=True)
        _, mid, _ = st.columns([1, 2.2, 1])
        with mid:
            with st.container(border=True):
                with st.form("onboarding_form"):
                    user_name = st.text_input("Your name", placeholder="e.g. Alex")
                    role = st.text_input("Role you are interviewing for", value="Software Engineer")
                    submitted = st.form_submit_button("Continue", type="primary", use_container_width=True)
                if submitted:
                    st.session_state.user_name = user_name.strip()
                    st.session_state.session.role = role.strip() or "Software Engineer"
                    st.session_state.interview_type = "General"
                    st.session_state.topic = "core interview fundamentals"
                    st.session_state.profile_complete = True
                    st.session_state.last_error = ""
                    save_session(SESSION_FILE, st.session_state.session)
                    st.rerun()
        st.markdown(
            '<p class="app-subtle-note">Tip: start with 2-3 questions per round for the fastest feedback loop.</p>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    with st.sidebar:
        st.markdown('<p class="app-kicker">Session</p>', unsafe_allow_html=True)
        st.caption("Interview actions (generate, answer) live in the main panel →")
        st.markdown("### Profile")
        role = st.text_input("Target role", value=st.session_state.session.role, key="sb_role")
        st.caption("Interview focus and topics adapt automatically from your performance.")

        st.divider()
        st.markdown('<p class="app-kicker">Speed vs depth</p>', unsafe_allow_html=True)
        st.caption("Each question in **Evaluate** calls the model several times if jury/tools/reflection are on.")
        st.session_state.jury_mode = st.toggle(
            "Jury evaluation (2 evaluators)",
            value=st.session_state.jury_mode,
            help="Roughly doubles evaluator work per answer. Turn off for faster feedback.",
        )
        st.session_state.enable_tools = st.toggle(
            "Supervisor tools",
            value=st.session_state.enable_tools,
            help="Extra LLM tool pick each answer.",
        )
        st.session_state.enable_reflection = st.toggle(
            "Reflection loop",
            value=st.session_state.enable_reflection,
            help="Extra LLM call to adjust question style.",
        )

        st.divider()
        c_apply = st.columns(1)[0]
        if c_apply.button("Save settings", use_container_width=True, type="secondary"):
            st.session_state.session.role = role.strip() or "Software Engineer"
            save_session(SESSION_FILE, st.session_state.session)
            st.success("Saved.")

        if st.button("Reset session", use_container_width=True):
            _reset_all()
            st.success("Session reset.")

        s: SessionSnapshot = st.session_state.session
        st.divider()
        st.markdown('<p class="app-kicker">Progress</p>', unsafe_allow_html=True)
        if st.session_state.user_name:
            st.write(f"**{st.session_state.user_name}** · Adaptive interview mode")
        else:
            st.write("**Candidate** · Adaptive interview mode")
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

    if st.session_state.pop("_run_generate_round", False):
        if _render_generation_panel():
            st.toast("Round ready — answer in the Interview workspace below.", icon="🎯")
            st.rerun()

    items = st.session_state.round_items
    n = st.session_state.round_size

    with st.container(border=True):
        st.markdown("## Agentic Career Preparation Copilot")
        st.markdown(
            """
            <div class="app-inner-hero">
                <strong>Your main workspace</strong>
                <p>Switch between interview practice and career tools. Everything uses the same style and workflow for a smoother experience.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        workspace = st.segmented_control(
            "Workspace",
            options=["Interview practice", "Career workspace"],
            key="main_workspace_segment",
        )

        if workspace == "Interview practice":
            st.divider()
            sum_l, mid_m, mid_r, btn_c = st.columns([2.0, 1.0, 1.0, 1.2], gap="small")
            with sum_l:
                st.markdown(
                    f"**{st.session_state.session.role}** · _adaptive mixed interview_ · "
                    f"**Topic:** {st.session_state.topic}"
                )
            with mid_m:
                st.session_state.round_size = st.number_input(
                    "Questions",
                    min_value=1,
                    max_value=10,
                    value=int(st.session_state.round_size),
                    step=1,
                    help="Fewer questions = faster generation and evaluation.",
                    key="practice_round_size",
                )
            with mid_r:
                st.session_state.difficulty = st.selectbox(
                    "Difficulty",
                    options=["easy", "medium", "hard"],
                    index=["easy", "medium", "hard"].index(st.session_state.difficulty),
                    key="practice_difficulty",
                )
            with btn_c:
                st.write("")  # align button with inputs
                st.write("")
                if st.button("Generate round", type="primary", use_container_width=True, key="main_generate_round"):
                    st.session_state._run_generate_round = True
                    st.session_state.last_error = ""
                    st.rerun()

            if st.session_state.interview_type == "Behavioral":
                _render_behavioral_flashcards()

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
                    "Set **Questions**, then click **Generate round** above. One model call builds the full set of prompts."
                )
            else:
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

        else:
            st.divider()
            _render_career_copilot_panel()

    if st.session_state.last_error:
        st.error(st.session_state.last_error)


if __name__ == "__main__":
    main()

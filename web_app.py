from __future__ import annotations

from pathlib import Path

import streamlit as st

from interview_helper.behavioral_flashcards import CARDS as BEHAVIORAL_CARDS
from interview_helper.tools_runtime import (
    extract_resume_achievements,
    extract_jd_keywords,
    generate_followup_reminder,
    generate_networking_message,
    tailor_resume_bullets,
)

from interview_helper.agents import (
    round_batch_agent,
)
from interview_helper.memory import load_session, save_session
from interview_helper.models import SessionSnapshot
from interview_helper.orchestrator import run_agentic_turn

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
        <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400..800&family=Manrope:wght@500;600;700;800&display=swap" rel="stylesheet" />
        <style>
        .block-container {
            font-family: "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
            max-width: 1120px;
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
            box-sizing: border-box;
            color: #0f172a;
            line-height: 1.5;
        }
        h1, h2, h3 {
            letter-spacing: -0.02em;
            font-family: "Manrope", "Inter", ui-sans-serif, system-ui, sans-serif;
            color: #0b1220;
        }
        p, li, label, .stMarkdown, .stCaption {
            font-size: 0.97rem;
        }
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
            font-family: "Manrope", "Inter", sans-serif;
            font-size: 1.75rem;
            font-weight: 800;
            margin: 0 0 0.4rem 0;
            line-height: 1.2;
        }
        .app-hero p {
            margin: 0;
            opacity: 0.98;
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
        .app-muted { color: #334155; font-size: 0.92rem; }
        .app-kicker {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            color: #334155;
        }
        button:focus-visible {
            outline: 3px solid #1d4ed8 !important;
            outline-offset: 2px !important;
            box-shadow: 0 0 0 4px rgba(29, 78, 216, 0.25);
        }
        a:focus-visible {
            outline: 3px solid #1d4ed8;
            outline-offset: 2px;
            border-radius: 4px;
        }
        a {
            color: #1d4ed8 !important;
        }
        a:hover {
            color: #1e40af !important;
        }
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
            font-weight: 700 !important;
            min-height: 2.6rem !important;
        }
        .stButton > button[kind="primaryFormSubmit"]:hover,
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 14px 28px rgba(37, 99, 235, 0.28);
        }
        .stButton > button[kind="secondary"] {
            border-radius: 12px !important;
            border: 1px solid #94a3b8 !important;
            background: #ffffff !important;
            color: #0f172a !important;
            font-weight: 600 !important;
            min-height: 2.5rem !important;
        }
        .app-onboard-shell {
            max-width: 920px;
            margin: 0 auto;
        }
        .app-onboard-lead {
            color: #334155;
            margin: -0.15rem 0 1rem 0;
        }
        .app-subtle-note {
            color: #334155;
            font-size: 0.86rem;
            margin-top: 0.55rem;
        }
        .app-gen-shell {
            border: 1px solid rgba(148, 163, 184, 0.32);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.86);
            padding: 0.9rem 1rem 0.65rem;
            margin: 0.45rem 0 0.8rem 0;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
        }
        .app-gen-kv {
            color: #334155;
            font-size: 0.92rem;
            margin-bottom: 0.5rem;
        }
        .app-gen-note {
            color: #334155;
            font-size: 0.86rem;
            margin: 0;
        }
        .resume-studio {
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 14px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(248, 250, 252, 0.92));
            padding: 0.9rem 1rem 0.7rem;
            margin: 0.3rem 0 0.7rem;
        }
        .resume-studio h4 {
            margin: 0 0 0.25rem 0;
            font-size: 1rem;
            color: #0f172a;
        }
        .resume-studio p {
            margin: 0;
            color: #334155;
            font-size: 0.9rem;
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
            color: #334155;
            font-size: 0.93rem;
        }
        .app-inner-hero strong {
            color: #1e293b;
        }
        .app-shell {
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.72);
            box-shadow: 0 16px 36px rgba(15, 23, 42, 0.08);
            padding: 1rem 1rem 1.15rem;
        }
        .app-topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.7rem;
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 12px;
            padding: 0.65rem 0.8rem;
            background: linear-gradient(140deg, rgba(37, 99, 235, 0.10), rgba(67, 56, 202, 0.08));
            margin-bottom: 0.7rem;
        }
        .app-topbar-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: #0f172a;
        }
        .app-topbar-sub {
            font-size: 0.84rem;
            color: #334155;
        }
        .app-chip {
            border: 1px solid rgba(99, 102, 241, 0.25);
            border-radius: 999px;
            padding: 0.28rem 0.6rem;
            font-size: 0.78rem;
            color: #3730a3;
            background: rgba(238, 242, 255, 0.8);
            white-space: nowrap;
        }
        .app-section-card {
            border: 1px solid rgba(148, 163, 184, 0.26);
            border-radius: 13px;
            background: rgba(255, 255, 255, 0.88);
            padding: 0.75rem 0.85rem 0.5rem;
            margin-bottom: 0.75rem;
        }
        .app-section-title {
            margin: 0 0 0.2rem 0;
            font-size: 0.95rem;
            color: #0f172a;
            font-weight: 700;
        }
        .app-section-sub {
            margin: 0 0 0.45rem 0;
            color: #334155;
            font-size: 0.84rem;
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
        .stTextInput input,
        .stTextArea textarea {
            border-radius: 10px !important;
            border: 1px solid #94a3b8 !important;
            color: #0f172a !important;
            background: #ffffff !important;
        }
        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {
            color: #64748b !important;
            opacity: 1 !important;
        }
        [data-testid="stForm"] label,
        .stTextInput label,
        .stTextArea label,
        .stSelectbox label,
        .stNumberInput label {
            color: #1e293b !important;
            font-weight: 600 !important;
        }
        @media (prefers-reduced-motion: reduce) {
            .app-hero {
                animation: none !important;
            }
            * {
                scroll-behavior: auto !important;
                transition: none !important;
            }
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
            .app-topbar {
                flex-direction: column;
                align-items: flex-start;
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
        st.markdown(
            """
            <div class="resume-studio">
                <h4>Resume Alignment Studio</h4>
                <p>Paste your full resume text (or bullets) plus a target JD. The app extracts key achievements first, then tailors them for the role.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        strength = st.select_slider(
            "Rewrite strength",
            options=["light", "balanced", "aggressive"],
            value="balanced",
            help="Light keeps your wording close. Aggressive reframes more strongly for role fit.",
            key="resume_rewrite_strength",
        )
        jd = st.text_area(
            "Job description",
            height=160,
            value=st.session_state.career_jd_draft,
            key="career_jd_widget",
            placeholder="Paste the full job description (responsibilities, requirements, stack).",
        )
        st.session_state.career_jd_draft = jd
        resume_raw = st.text_area(
            "Your resume content (paste full text or bullets)",
            value=st.session_state.resume_content_draft,
            key="resume_content_widget",
            height=220,
            placeholder="Paste your experience section or full resume text here...",
        )
        st.session_state.resume_content_draft = resume_raw
        c1, c2 = st.columns(2)
        if c1.button("Extract keywords", use_container_width=True, type="secondary"):
            st.session_state.session.active_job_description = jd
            kws = extract_jd_keywords(job_description=jd, top_k=14)
            st.session_state.career_jd_keywords = kws
            save_session(SESSION_FILE, st.session_state.session)
            st.rerun()
        if c2.button("Tailor resume highlights to this JD", use_container_width=True, type="primary"):
            if not resume_raw.strip() or not jd.strip():
                st.warning("Add both a job description and resume content.")
            else:
                with st.spinner("Aligning bullets with the job description…"):
                    src = extract_resume_achievements(resume_text=resume_raw, max_points=8)
                    tailored = tailor_resume_bullets(
                        resume_bullets=src,
                        job_description=jd,
                        rewrite_strength=strength,
                    )
                pairs = []
                for i, t in enumerate(tailored):
                    original = src[i] if i < len(src) else ""
                    pairs.append({"original": original, "tailored": t})
                st.session_state.career_tailored_bullets = tailored
                st.session_state.career_tailor_pairs = pairs
                st.session_state.session.active_job_description = jd
                save_session(SESSION_FILE, st.session_state.session)
                st.rerun()

        if st.session_state.career_jd_keywords:
            st.markdown("**Keywords from the posting**")
            st.caption(", ".join(st.session_state.career_jd_keywords))

        if st.session_state.career_tailored_bullets:
            st.success("Tailoring complete. Review extracted source points and final tailored versions below.")
            st.markdown("**Tailored bullets**")
            for idx, pair in enumerate(st.session_state.career_tailor_pairs or [], start=1):
                with st.expander(f"Bullet {idx}: before → after", expanded=False):
                    st.markdown(f"**Before:** {pair.get('original', '')}")
                    st.markdown(f"**After:** {pair.get('tailored', '')}")
            if not st.session_state.career_tailor_pairs:
                for b in st.session_state.career_tailored_bullets:
                    st.markdown(f"- {b}")
            tailored_text = "\n".join(f"• {b}" for b in st.session_state.career_tailored_bullets)
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
    if "career_tailor_pairs" not in st.session_state:
        st.session_state.career_tailor_pairs = []
    if "career_jd_draft" not in st.session_state:
        st.session_state.career_jd_draft = ""
    if "resume_content_draft" not in st.session_state:
        st.session_state.resume_content_draft = ""
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
        turn = run_agentic_turn(
            session=st.session_state.session,
            question=q,
            answer=ua,
            topic=st.session_state.topic,
            interview_type=st.session_state.interview_type,
            jury_mode=st.session_state.jury_mode,
            enable_reflection=st.session_state.enable_reflection,
            enable_tools=st.session_state.enable_tools,
            max_steps=3,
        )
        ev = turn["evaluation"]
        strict_ev = turn["strict_evaluation"]
        clarity_ev = turn["clarity_evaluation"]
        jury_summary = turn["jury_summary"]
        plan = turn["plan"]
        intervention = turn["intervention"]
        tool_name = turn["tool_name"]
        tool_reason = turn["tool_reason"]
        tool_output = turn["tool_output"]
        pattern = turn["reflection_pattern"]
        style = turn["reflection_style"]
        strategy = turn["reflection_strategy"]
        critic_notes = turn["critic_notes"]

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
                "critic_notes": critic_notes,
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
    st.session_state.career_tailor_pairs = []
    st.session_state.career_jd_draft = ""
    st.session_state.resume_content_draft = ""
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
    st.markdown(
        f"""
        <div class="app-gen-shell">
            <p class="app-gen-kv"><strong>{role}</strong> · {itype} · {topic} · {n} questions · difficulty <strong>{st.session_state.difficulty}</strong></p>
            <p class="app-gen-note">Live pipeline shown below. This mirrors the app workflow (prompt build → model call → parse/validate → ready).</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("What the app is doing right now", expanded=True):
        st.markdown("- Stage 1: Build structured prompt from role, topic, difficulty, and count.")
        st.markdown("- Stage 2: Request one JSON batch from the model (all questions + reference answers).")
        st.markdown("- Stage 3: Parse JSON and validate exact item count.")
        st.markdown("- Stage 4: If invalid, run one repair pass and re-parse.")
        st.markdown("- Stage 5: Save round into session and render your answer fields.")

    ok = False
    with st.status("Calling the batch model — usually the slowest step…", expanded=True) as status:
        status.write("Stage 1/5: Preparing prompt payload")
        status.write("Stage 2/5: Sending batch request to your model")
        prog = st.progress(0, text="Starting…")
        try:
            prog.progress(30, text="Model request in progress…")
            _generate_round()
            status.write("Stage 3/5: Parsing JSON output")
            status.write("Stage 4/5: Validating output length/shape")
            prog.progress(85, text="Validating and saving…")
            status.write("Stage 5/5: Round saved to session")
            prog.progress(100, text="Done")
            status.update(label="Round ready", state="complete")
            ok = True
        except Exception as e:  # pragma: no cover
            st.session_state.last_error = f"Could not generate round: {e}"
            status.update(label="Generation failed", state="error")
    return ok


def main() -> None:
    st.set_page_config(
        page_title="Agentic Career Readiness Assistant",
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
        st.markdown("## Agentic Career Readiness Assistant")
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
                    role = st.text_input("Role you are interviewing for", placeholder="e.g. Software Engineer")
                    submitted = st.form_submit_button("Continue", type="primary", use_container_width=True)
                if submitted:
                    st.session_state.user_name = user_name.strip()
                    st.session_state.session.role = role.strip() or "Candidate"
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
    display_name = (st.session_state.user_name or "").strip() or "there"

    with st.container(border=True):
        st.markdown('<div class="app-shell">', unsafe_allow_html=True)
        st.markdown(f"## Hi {display_name}, let's begin your prep")
        st.markdown(
            f"""
            <div class="app-topbar">
                <div>
                    <div class="app-topbar-title">Agentic Career Readiness Assistant</div>
                    <div class="app-topbar-sub">Interview practice + JD alignment + outreach in one workspace</div>
                </div>
                <div class="app-chip">{st.session_state.session.role}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
            st.markdown(
                """
                <div class="app-section-card">
                    <p class="app-section-title">Interview controls</p>
                    <p class="app-section-sub">Tune question count and difficulty, then generate a fresh round.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
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
                st.markdown(
                    """
                    <div class="app-section-card">
                        <p class="app-section-title">Answer workspace</p>
                        <p class="app-section-sub">Write concise interview responses and evaluate them together at the end.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
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
                st.markdown(
                    """
                    <div class="app-section-card">
                        <p class="app-section-title">Performance history</p>
                        <p class="app-section-sub">Review scores, jury verdicts, and planner/tool interventions over time.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
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
                            critic_notes = item.get("critic_notes") or []
                            if critic_notes:
                                last_note = critic_notes[-1]
                                st.markdown(
                                    f"**Critic:** approved={last_note.get('approved')} · confidence={last_note.get('confidence')} · "
                                    f"reason: {last_note.get('reason', '—')}"
                                )

        else:
            st.divider()
            _render_career_copilot_panel()
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.last_error:
        st.error(st.session_state.last_error)


if __name__ == "__main__":
    main()

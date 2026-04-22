from __future__ import annotations

from typing import Any

from interview_helper.agents import answer_key_agent, coaching_agent
from interview_helper.llm_client import chat_completion, model_for
from interview_helper.models import SessionSnapshot
from interview_helper.parse_json import extract_json_array, extract_json_object
from interview_helper.prompts import recruiter_outreach_system, recruiter_outreach_user, resume_tailor_system, resume_tailor_user


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


def extract_jd_keywords(*, job_description: str, top_k: int = 12) -> list[str]:
    stop = {
        "the",
        "and",
        "with",
        "for",
        "that",
        "this",
        "you",
        "your",
        "from",
        "have",
        "will",
        "are",
        "our",
        "role",
        "team",
        "years",
        "experience",
    }
    words = []
    for raw in job_description.replace("/", " ").replace(",", " ").split():
        w = raw.strip(" .:;()[]{}!?\"'").lower()
        if len(w) < 3 or w in stop:
            continue
        words.append(w)
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    ordered = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in ordered[:top_k]]


def _coerce_string_list(raw: Any, *, expected: int) -> list[str]:
    """Normalize model JSON (array of strings or objects) into a flat list of strings."""
    if isinstance(raw, list):
        out: list[str] = []
        for x in raw:
            if isinstance(x, str):
                s = x.strip()
            elif isinstance(x, dict):
                s = (
                    str(x.get("bullet") or x.get("text") or x.get("tailored") or x.get("content") or "")
                    .strip()
                )
            else:
                s = str(x).strip() if x is not None else ""
            out.append(s)
        if len(out) == expected and all(out):
            return out
    return []


def tailor_resume_bullets(*, resume_bullets: list[str], job_description: str) -> list[str]:
    """
    Rewrite bullets to align with the job description using the interview LLM.
    Falls back to a light keyword weave only if the model call or JSON parse fails.
    """
    jd = job_description.strip()
    src = [b.strip() for b in resume_bullets if b.strip()]
    if not src or not jd:
        return src

    model = model_for("interview")
    system = resume_tailor_system()
    user = resume_tailor_user(job_description=jd, bullets=src)

    def _fallback() -> list[str]:
        kws = extract_jd_keywords(job_description=jd, top_k=8)
        out: list[str] = []
        for i, b in enumerate(src):
            hint = kws[i % len(kws)] if kws else "relevant impact"
            out.append(
                f"{b.rstrip('.')}, emphasizing alignment with {hint} and measurable results where supported by the original."
            )
        return out

    try:
        raw = chat_completion(model=model, system=system, user=user, temperature=0.35)
        arr = extract_json_array(raw)
        coerced = _coerce_string_list(arr, expected=len(src))
        if coerced:
            return coerced
        data = extract_json_object(raw)
        inner = data.get("bullets") or data.get("tailored_bullets") or data.get("items")
        coerced2 = _coerce_string_list(inner, expected=len(src))
        if coerced2:
            return coerced2
    except Exception:
        pass

    try:
        repair = chat_completion(
            model=model,
            system=system,
            user=(
                "Your previous reply was not a valid JSON array of strings of the correct length. "
                f"Output ONLY a JSON array of exactly {len(src)} strings, same order as the originals.\n\n"
                + user
            ),
            temperature=0.0,
        )
        arr2 = extract_json_array(repair)
        coerced3 = _coerce_string_list(arr2, expected=len(src))
        if coerced3:
            return coerced3
    except Exception:
        pass

    return _fallback()


def generate_networking_message(
    *,
    candidate_name: str,
    target_role: str,
    company: str,
    shared_context: str = "",
    channel: str = "email",
) -> dict[str, str]:
    """
    Draft a recruiter- or hiring-manager-ready message.
    Returns {"subject": str, "body": str} suitable for email or LinkedIn (subject may be empty).
    """
    name = (candidate_name or "Candidate").strip() or "Candidate"
    role = (target_role or "this role").strip() or "this role"
    co = (company or "your company").strip() or "your company"
    ch = (channel or "email").strip().lower()
    if ch not in ("email", "linkedin"):
        ch = "email"

    model = model_for("interview")
    system = recruiter_outreach_system()
    user = recruiter_outreach_user(
        candidate_name=name,
        target_role=role,
        company=co,
        shared_context=shared_context,
        channel="Professional email" if ch == "email" else "LinkedIn connection request or InMail (short paragraphs)",
    )

    def _template_fallback() -> dict[str, str]:
        first = name.split()[0] if name else "Candidate"
        subj = "" if ch == "linkedin" else f"Question about the {role} role — {first}"
        body_lines = [
            f"Hi,",
            "",
            f"My name is {name}. I recently applied for the {role} opening at {co} and wanted to reach out respectfully.",
        ]
        if shared_context.strip():
            body_lines.extend(["", f"We have a bit of shared context: {shared_context.strip()}. I hoped that might make a brief note appropriate."])
        body_lines.extend(
            [
                "",
                "I would really value ten minutes of your advice on what the team prioritizes in strong candidates for this role, "
                "or any suggestions on how I can best prepare for the next steps.",
                "",
                "Thank you for your time and consideration.",
                "",
                f"Best regards,",
                name,
            ]
        )
        return {"subject": subj, "body": "\n".join(body_lines)}

    try:
        raw = chat_completion(model=model, system=system, user=user, temperature=0.45)
        data = extract_json_object(raw)
        subj = str(data.get("subject", "")).strip()
        body = str(data.get("body", "")).strip()
        if body:
            if ch == "linkedin" and not subj:
                subj = ""
            return {"subject": subj, "body": body}
    except Exception:
        pass

    try:
        repair = chat_completion(
            model=model,
            system=system,
            user="Output ONLY valid JSON: {\"subject\": \"...\", \"body\": \"...\"}.\n\n" + user,
            temperature=0.0,
        )
        data2 = extract_json_object(repair)
        subj2 = str(data2.get("subject", "")).strip()
        body2 = str(data2.get("body", "")).strip()
        if body2:
            return {"subject": subj2, "body": body2}
    except Exception:
        pass

    return _template_fallback()


def generate_followup_reminder(*, company: str, role: str, days_since_apply: int) -> str:
    model = model_for("interview")
    system = (
        "You write brief, ready-to-send follow-up email drafts for job applicants. "
        "Output ONLY a JSON object: {\"subject\": string, \"body\": string}. Plain text body, 3–5 short paragraphs max."
    )
    user = (
        f"It has been {days_since_apply} days since applying to {company} for the {role} role. "
        "Draft a polite follow-up that restates interest, references the application, and mentions one concrete strength."
    )
    try:
        raw = chat_completion(model=model, system=system, user=user, temperature=0.35)
        data = extract_json_object(raw)
        subj = str(data.get("subject", "")).strip()
        body = str(data.get("body", "")).strip()
        if subj and body:
            return f"Subject: {subj}\n\n{body}"
        if body:
            return body
    except Exception:
        pass
    return (
        f"Subject: Following up — {role} application at {company}\n\n"
        f"Hi,\n\n"
        f"I hope you are doing well. I wanted to follow up on my application for the {role} position "
        f"at {company} ({days_since_apply} days ago). I remain very interested and would welcome any update "
        f"when convenient.\n\n"
        f"Thank you for your time.\n\n"
        f"Best regards"
    )

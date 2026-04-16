from __future__ import annotations

from interview_helper.agents import answer_key_agent, coaching_agent
from interview_helper.models import SessionSnapshot


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


def tailor_resume_bullets(*, resume_bullets: list[str], job_description: str) -> list[str]:
    kws = extract_jd_keywords(job_description=job_description, top_k=8)
    out: list[str] = []
    for i, b in enumerate(resume_bullets):
        hint = kws[i % len(kws)] if kws else "impact"
        out.append(f"{b.rstrip('.')} using {hint}, with measurable outcome where possible.")
    return out


def generate_networking_message(
    *,
    candidate_name: str,
    target_role: str,
    company: str,
    shared_context: str = "",
) -> str:
    context = f" We share {shared_context}." if shared_context.strip() else ""
    return (
        f"Hi, I am {candidate_name} and I am preparing for {target_role} roles at {company}.{context} "
        "I admire the work your team is doing and would value 10 minutes for advice on how to prepare "
        "for the role effectively. Thank you for considering."
    )


def generate_followup_reminder(*, company: str, role: str, days_since_apply: int) -> str:
    return (
        f"Follow-up reminder: It has been {days_since_apply} days since applying to {company} for {role}. "
        "Send a concise, polite follow-up highlighting continued interest and one relevant achievement."
    )

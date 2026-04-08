from __future__ import annotations

from interview_helper.models import Difficulty, EvaluationResult, NextPlan, SessionSnapshot


def infer_topic_from_evaluation(ev: EvaluationResult, fallback: str) -> str:
    """Light heuristic: use first missed point as a topic hint, else fallback."""
    if ev.missed_points:
        return ev.missed_points[0][:80]
    return fallback


def plan_next(
    ev: EvaluationResult,
    session: SessionSnapshot,
    default_topic: str,
) -> NextPlan:
    """
    Decide next difficulty and focus without a second LLM call.
    This is explicit policy logic (easy to explain in a report / demo).
    """
    s = ev.overall_score
    if s < 5.0:
        nxt: Difficulty = "easy"
        rationale = "Score under 5: ease difficulty and reinforce fundamentals."
    elif s < 7.5:
        nxt = "medium"
        rationale = "Score in mid range: hold or slightly adjust difficulty."
    else:
        nxt = "hard"
        rationale = "Strong answer: increase challenge."

    focus = infer_topic_from_evaluation(ev, default_topic)
    if ev.missed_points:
        rationale += " Focus on gaps listed in evaluation."

    return NextPlan(next_difficulty=nxt, focus_topic=focus, rationale=rationale)


def update_memory(ev: EvaluationResult, session: SessionSnapshot, topic: str) -> None:
    session.questions_asked += 1
    session.recent_scores.append(ev.overall_score)
    session.recent_scores = session.recent_scores[-10:]

    avg = sum(session.recent_scores) / len(session.recent_scores)
    if ev.overall_score < avg - 0.5 and topic:
        if topic not in session.weak_topics:
            session.weak_topics.append(topic)
        session.weak_topics = session.weak_topics[-8:]
    elif ev.overall_score >= 7.5 and topic:
        if topic not in session.strong_topics:
            session.strong_topics.append(topic)
        session.strong_topics = session.strong_topics[-8:]

    session.current_topic = topic

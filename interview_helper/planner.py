from __future__ import annotations

from interview_helper.models import (
    Difficulty,
    EvaluationResult,
    NextPlan,
    SessionSnapshot,
    TurnReflection,
)


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
    action = "ask_question"
    payload = ""

    topic_key = session.current_topic or default_topic
    topic_streak = session.topic_fail_streak.get(topic_key, 0)
    if topic_streak >= 2 and s < 5.5:
        action = "give_lesson"
        payload = f"Autonomous remediation on {topic_key}"
        focus = topic_key
        nxt = "easy"
        rationale += " Low-score streak detected: switch to remediation mode."
    elif ev.missed_points and s < 6.0:
        action = "give_lesson"
        payload = ev.missed_points[0]
        rationale += " Trigger mini-lesson before next question."
    elif ev.missed_points and 6.0 <= s < 7.5:
        action = "give_drill"
        payload = ev.missed_points[0]
        rationale += " Trigger targeted drill on the weakest concept."
    elif not ev.missed_points and s >= session.target_score and len(session.recent_scores) >= 2:
        action = "end_session"
        payload = "Goal achieved with consistent performance."
        rationale += " Session goal reached consistently."
    elif session.missed_points_log:
        action = "review_mistakes"
        payload = session.missed_points_log[-1]
        rationale += " Review recurring mistake pattern."

    if ev.missed_points:
        rationale += " Focus on gaps listed in evaluation."

    return NextPlan(
        next_difficulty=nxt,
        focus_topic=focus,
        rationale=rationale,
        action=action,
        action_payload=payload,
    )


def update_memory(ev: EvaluationResult, session: SessionSnapshot, topic: str) -> None:
    prev_topic = session.current_topic or "general"
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

    for missed in ev.missed_points:
        if missed and missed not in session.missed_points_log:
            session.missed_points_log.append(missed)
    session.missed_points_log = session.missed_points_log[-20:]

    pattern = ev.missed_points[0] if ev.missed_points else "No dominant gap"
    session.reflections.append(
        TurnReflection(
            topic=topic,
            score=ev.overall_score,
            mistake_pattern=pattern,
            intervention_used="none",
        )
    )
    session.reflections = session.reflections[-20:]

    if len(session.recent_scores) >= 3:
        trailing = session.recent_scores[-3:]
        trailing_avg = sum(trailing) / 3
        session.completed = trailing_avg >= session.target_score

    streak_key = topic or prev_topic
    if streak_key:
        if ev.overall_score < 5.5:
            session.topic_fail_streak[streak_key] = session.topic_fail_streak.get(streak_key, 0) + 1
        else:
            session.topic_fail_streak[streak_key] = 0

    session.current_topic = topic

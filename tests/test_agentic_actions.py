from interview_helper.models import EvaluationResult, SessionSnapshot
from interview_helper.planner import plan_next, update_memory


def _ev(score: float, missed: list[str] | None = None) -> EvaluationResult:
    return EvaluationResult(
        technical_accuracy=7,
        completeness=7,
        clarity=7,
        depth=7,
        communication=7,
        overall_score=score,
        missed_points=missed or [],
        strengths=["ok"],
        feedback_summary="fine",
    )


def test_plan_triggers_lesson_for_low_score_with_gaps() -> None:
    s = SessionSnapshot(role="Software Engineer")
    plan = plan_next(_ev(4.5, missed=["hash collisions"]), s, default_topic="hash maps")
    assert plan.action == "give_lesson"
    assert plan.action_payload == "hash collisions"


def test_session_completion_after_three_strong_scores() -> None:
    s = SessionSnapshot(role="Software Engineer", target_score=8.0)
    for score in [8.0, 8.5, 8.2]:
        update_memory(_ev(score), s, "system design")
    assert s.completed is True


def test_autonomous_remediation_after_topic_streak() -> None:
    s = SessionSnapshot(role="Software Engineer", current_topic="dynamic programming")
    s.topic_fail_streak["dynamic programming"] = 2
    plan = plan_next(_ev(4.8, missed=["states"]), s, default_topic="dynamic programming")
    assert plan.action == "give_lesson"
    assert "remediation" in plan.action_payload.lower()

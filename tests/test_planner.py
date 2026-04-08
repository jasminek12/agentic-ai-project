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


def test_plan_next_difficulty_bands() -> None:
    s = SessionSnapshot(role="Software Engineer")
    assert plan_next(_ev(4.9), s, default_topic="x").next_difficulty == "easy"
    assert plan_next(_ev(5.0), s, default_topic="x").next_difficulty == "medium"
    assert plan_next(_ev(7.4), s, default_topic="x").next_difficulty == "medium"
    assert plan_next(_ev(7.5), s, default_topic="x").next_difficulty == "hard"


def test_update_memory_tracks_topics() -> None:
    s = SessionSnapshot(role="Software Engineer")
    update_memory(_ev(8.0), s, "arrays")
    assert "arrays" in s.strong_topics


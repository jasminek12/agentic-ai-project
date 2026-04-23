from interview_helper.models import EvaluationResult, NextPlan, SessionSnapshot
from interview_helper.orchestrator import run_agentic_turn


def _ev(score: float = 4.6) -> EvaluationResult:
    return EvaluationResult(
        technical_accuracy=5,
        completeness=5,
        clarity=5,
        depth=5,
        communication=5,
        overall_score=score,
        missed_points=["hash collisions"],
        strengths=["clear structure"],
        feedback_summary="Missed collision handling details.",
    )


def test_orchestrator_replans_when_critic_rejects(monkeypatch) -> None:
    monkeypatch.setattr("interview_helper.orchestrator.evaluator_agent", lambda **_: _ev())
    monkeypatch.setattr(
        "interview_helper.orchestrator.plan_next",
        lambda *_args, **_kwargs: NextPlan(
            next_difficulty="easy",
            focus_topic="hash tables",
            rationale="low score",
            action="ask_question",
            action_payload="",
        ),
    )
    monkeypatch.setattr(
        "interview_helper.orchestrator.execute_plan_action",
        lambda plan, _session: f"action::{plan.action}",
    )
    monkeypatch.setattr(
        "interview_helper.orchestrator.supervisor_tool_agent",
        lambda **_: ("none", "no tool"),
    )
    monkeypatch.setattr(
        "interview_helper.orchestrator.execute_supervisor_tool",
        lambda **_: "",
    )
    monkeypatch.setattr(
        "interview_helper.orchestrator.reflection_agent",
        lambda **_: ("gap pattern", "balanced", "practice gaps"),
    )
    calls = {"n": 0}

    def _critic(**_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return False, 0.4, "Too weak", "give_lesson", "collision strategy"
        return True, 0.8, "Looks good", "give_lesson", "collision strategy"

    monkeypatch.setattr("interview_helper.orchestrator.critic_agent", _critic)

    s = SessionSnapshot(role="Software Engineer")
    out = run_agentic_turn(
        session=s,
        question="How does a hash map handle collisions?",
        answer="It hashes keys into buckets.",
        topic="hash maps",
        interview_type="General",
        jury_mode=False,
        enable_reflection=True,
        enable_tools=False,
        max_steps=3,
    )
    assert out["plan"].action == "give_lesson"
    assert len(out["critic_notes"]) == 2
    assert s.questions_asked == 1


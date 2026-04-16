import json

from interview_helper import agents


def _wrapped_payload(score: float = 7.5) -> str:
    return json.dumps(
        {
            "evaluation": {
                "technical_accuracy": 7,
                "completeness": 7,
                "clarity": 7,
                "depth": 7,
                "communication": 7,
                "overall_score": score,
                "missed_points": ["edge cases"],
                "strengths": ["structure"],
                "feedback_summary": "Solid baseline answer.",
            }
        }
    )


def test_evaluator_accepts_wrapped_schema(monkeypatch) -> None:
    monkeypatch.setattr(agents, "model_for", lambda *_: "fake-model")
    monkeypatch.setattr(agents, "chat_completion", lambda **_: _wrapped_payload(8.0))

    ev = agents.evaluator_agent(question="Q", answer="A")
    assert ev.overall_score == 8.0
    assert ev.technical_accuracy == 7


def test_evaluator_repair_path_handles_wrapped_schema(monkeypatch) -> None:
    calls = iter(
        [
            '{"evaluation": {"technical_accuracy": 7 "completeness": 7}}',  # invalid JSON
            _wrapped_payload(6.5),
        ]
    )
    monkeypatch.setattr(agents, "model_for", lambda *_: "fake-model")
    monkeypatch.setattr(agents, "chat_completion", lambda **_: next(calls))

    ev = agents.evaluator_agent(question="Q", answer="A")
    assert ev.overall_score == 6.5
    assert ev.clarity == 7


def test_jury_evaluator_accepts_wrapped_schema(monkeypatch) -> None:
    calls = iter([_wrapped_payload(8.0), _wrapped_payload(6.0)])
    monkeypatch.setattr(agents, "model_for", lambda *_: "fake-model")
    monkeypatch.setattr(agents, "chat_completion", lambda **_: next(calls))

    strict, clarity, final, summary = agents.jury_evaluator_agent(question="Q", answer="A")
    assert strict.overall_score == 8.0
    assert clarity.overall_score == 6.0
    assert 1.0 <= final.overall_score <= 10.0
    assert "Final" in summary


def test_evaluator_coerces_partial_and_fractional_scores(monkeypatch) -> None:
    payload = json.dumps(
        {
            "technical_accuracy": 0.5,
            "feedback_summary": "Some relevant information.",
        }
    )
    monkeypatch.setattr(agents, "model_for", lambda *_: "fake-model")
    monkeypatch.setattr(agents, "chat_completion", lambda **_: payload)

    ev = agents.evaluator_agent(question="Q", answer="A")
    # 0.5 should be interpreted as 5/10 scale, not invalid int.
    assert ev.technical_accuracy == 5
    assert ev.completeness == 5
    assert ev.clarity == 5
    assert ev.depth == 5
    assert ev.communication == 5
    assert ev.overall_score == 5.0

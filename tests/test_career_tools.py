from __future__ import annotations

import pytest

from interview_helper import tools_runtime as tr


def test_tailor_resume_bullets_uses_llm_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_chat(*, model, system, user, temperature=0.4, max_retries=2):
        return '["First bullet tuned", "Second bullet tuned"]'

    monkeypatch.setattr(tr, "chat_completion", fake_chat)
    out = tr.tailor_resume_bullets(
        resume_bullets=["a", "b"],
        job_description="We need Python and AWS experience for backend work.",
    )
    assert out == ["First bullet tuned", "Second bullet tuned"]


def test_generate_networking_message_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_chat(*, model, system, user, temperature=0.4, max_retries=2):
        return '{"subject": "Hello from Alex", "body": "Hi there,\\n\\nBody text."}'

    monkeypatch.setattr(tr, "chat_completion", fake_chat)
    d = tr.generate_networking_message(
        candidate_name="Alex",
        target_role="Engineer",
        company="Acme",
        shared_context="",
        channel="email",
    )
    assert d["subject"] == "Hello from Alex"
    assert "Body text" in d["body"]


def test_generate_networking_message_template_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*, model, system, user, temperature=0.4, max_retries=2):
        raise RuntimeError("no API")

    monkeypatch.setattr(tr, "chat_completion", boom)
    d = tr.generate_networking_message(
        candidate_name="Alex",
        target_role="Engineer",
        company="Acme",
        shared_context="met at meetup",
        channel="linkedin",
    )
    assert d["subject"] == ""
    assert "Acme" in d["body"] and "Alex" in d["body"]


def test_extract_resume_achievements_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_chat(*, model, system, user, temperature=0.4, max_retries=2):
        return '["Reduced API latency by 35% for checkout service", "Led migration from monolith to services"]'

    monkeypatch.setattr(tr, "chat_completion", fake_chat)
    out = tr.extract_resume_achievements(
        resume_text="long pasted resume text",
        max_points=2,
    )
    assert len(out) == 2
    assert "latency" in out[0].lower()

"""Offline behavioral interview flashcards (no LLM required)."""

from typing import TypedDict


class Flashcard(TypedDict):
    prompt: str
    framework: str
    checklist: str


CARDS: list[Flashcard] = [
    {
        "prompt": "Tell me about a time you disagreed with your manager.",
        "framework": "STAR in ~90s: Situation → Task → Action → Result. End with what you learned.",
        "checklist": "Name the disagreement without blame · show how you raised it · describe the outcome · reflect on trust.",
    },
    {
        "prompt": "Describe a project that failed or missed a deadline.",
        "framework": "Own the miss early · explain constraints · what you changed next time · metrics if possible.",
        "checklist": "No excuses-only framing · show accountability · concrete follow-up · emotional steadiness.",
    },
    {
        "prompt": "Give an example of working with a difficult teammate.",
        "framework": "Focus on collaboration mechanics: communication, expectations, boundaries, escalation path.",
        "checklist": "Assume good intent · specific behavior (not personality) · how you de-escalated · team impact.",
    },
    {
        "prompt": "Tell me about a time you influenced without authority.",
        "framework": "Stakeholders + data + pilot · build allies · show persistence without steamrolling.",
        "checklist": "Clear ask · evidence · small experiment · how you handled pushback · adoption signal.",
    },
    {
        "prompt": "Describe a high-pressure situation and how you prioritized.",
        "framework": "Triage criteria (customer risk, deadlines) · communicate trade-offs · delegate if relevant.",
        "checklist": "Show judgment under uncertainty · explicit trade-offs · communication cadence · result.",
    },
    {
        "prompt": "Tell me about giving someone hard feedback.",
        "framework": "Private, timely, specific behavior → impact → ask + plan · follow-up.",
        "checklist": "No surprise feedback in a review · examples · empathy · measurable improvement plan.",
    },
    {
        "prompt": "Describe a time you learned something quickly on the job.",
        "framework": "Motivation → resources used → practice loop → outcome · humility + agency.",
        "checklist": "Name sources (docs, mentors, experiments) · timeboxed learning · proof of skill.",
    },
    {
        "prompt": "Why do you want this role / company?",
        "framework": "Bridge your past strengths to their mission/product · 2–3 specifics · curiosity question at end.",
        "checklist": "Avoid generic praise · tie to real work you'd do · show you researched thoughtfully.",
    },
]

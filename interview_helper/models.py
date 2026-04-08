from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Difficulty = Literal["easy", "medium", "hard"]


class EvaluationResult(BaseModel):
    """Structured output from the evaluator agent."""

    technical_accuracy: int = Field(ge=1, le=10)
    completeness: int = Field(ge=1, le=10)
    clarity: int = Field(ge=1, le=10)
    depth: int = Field(ge=1, le=10)
    communication: int = Field(ge=1, le=10)
    overall_score: float = Field(ge=1.0, le=10.0)
    missed_points: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    feedback_summary: str = ""


class NextPlan(BaseModel):
    """What the planner chooses for the next question."""

    next_difficulty: Difficulty
    focus_topic: str
    rationale: str


class SessionSnapshot(BaseModel):
    """Persisted memory between turns."""

    role: str
    weak_topics: list[str] = Field(default_factory=list)
    strong_topics: list[str] = Field(default_factory=list)
    recent_scores: list[float] = Field(default_factory=list)
    current_topic: str = "general"
    questions_asked: int = 0

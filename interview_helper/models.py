from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Difficulty = Literal["easy", "medium", "hard"]
PlannerAction = Literal[
    "ask_question",
    "give_lesson",
    "give_drill",
    "review_mistakes",
    "end_session",
]


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
    """What the planner chooses for the next turn."""

    next_difficulty: Difficulty
    focus_topic: str
    rationale: str
    action: PlannerAction = "ask_question"
    action_payload: str = ""


class TurnReflection(BaseModel):
    """Per-turn diagnostic memory used for planning interventions."""

    topic: str
    score: float
    mistake_pattern: str = ""
    intervention_used: str = ""
    recommended_style: str = "balanced"


class JuryEvaluation(BaseModel):
    """Outputs from multi-evaluator jury mode."""

    strict: EvaluationResult
    clarity: EvaluationResult
    final: EvaluationResult
    judge_summary: str = ""


class RoundQaItem(BaseModel):
    """One question + reference answer from a batch JSON round."""

    question: str
    reference_answer: str


class SessionSnapshot(BaseModel):
    """Persisted memory between turns."""

    role: str
    weak_topics: list[str] = Field(default_factory=list)
    strong_topics: list[str] = Field(default_factory=list)
    recent_scores: list[float] = Field(default_factory=list)
    missed_points_log: list[str] = Field(default_factory=list)
    reflections: list[TurnReflection] = Field(default_factory=list)
    current_topic: str = "general"
    questions_asked: int = 0
    target_score: float = 8.0
    completed: bool = False
    topic_fail_streak: dict[str, int] = Field(default_factory=dict)
    preferred_question_style: str = "balanced"
    target_companies: list[str] = Field(default_factory=list)
    active_job_description: str = ""
    outreach_history: list[str] = Field(default_factory=list)
    application_log: list[str] = Field(default_factory=list)
    login_days: list[str] = Field(default_factory=list)

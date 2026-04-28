from typing import Dict, List, Optional

from pydantic import BaseModel, Field, constr


class ErrorResponse(BaseModel):
    error: str = Field(..., example="Job description cannot be empty")


class TailorResumeRequest(BaseModel):
    resume_text: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        description="Raw resume text provided by the user.",
        example="Software Engineer at X...",
    )
    job_description: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        description="Target job description used for tailoring.",
        example="We are seeking a backend engineer with Python and FastAPI experience.",
    )


class TailorResumeResponse(BaseModel):
    pdf_path: str = Field(..., example="storage/outputs/resume_20260421_224500.pdf")


class ResumeResponse(BaseModel):
    message: str = Field(..., example="PDF file response generated successfully.")


class StartInterviewRequest(BaseModel):
    mode: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        description='Interview mode selected by user: "behavioral" or "technical".',
        example="behavioral",
    )
    job_description: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        description="Target job description for interview context.",
        example="Looking for a Python backend developer with Redis and Docker experience.",
    )
    resume: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        description="Candidate resume text.",
        example="Backend Engineer with 3 years of experience...",
    )
    session_id: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        description="Unique interview session identifier for multi-user memory isolation.",
        example="user_123_session_1",
    )
    panel_mode: bool = Field(
        default=False,
        description="Enable multi-persona panel simulation.",
        example=True,
    )
    pressure_round: bool = Field(
        default=False,
        description="Enable tougher follow-up style that challenges assumptions.",
        example=False,
    )
    company_context: str = Field(
        default="",
        description="Optional company context to tailor interview themes.",
        example="Series B fintech focused on compliance-heavy payment rails.",
    )
    role_context: str = Field(
        default="",
        description="Optional role context such as level/team expectations.",
        example="Backend Engineer II for platform reliability.",
    )
    interview_date: Optional[str] = Field(
        default=None,
        description="Optional interview date in YYYY-MM-DD format for curriculum planning.",
        example="2026-05-02",
    )
    target_question_count: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Optional custom question count override. If omitted, the agent estimates it from the role context.",
        example=6,
    )


class StartInterviewResponse(BaseModel):
    question: str = Field(..., example="Tell me about a time you resolved conflict in your team.")
    interview_started: bool = Field(default=True, example=True)
    target_question_count: int = Field(default=6, ge=1, example=6)


class InterviewStartResponse(StartInterviewResponse):
    pass


class SubmitAnswerRequest(BaseModel):
    answer: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        description="Candidate answer to the latest question.",
        example="In my previous role, we had conflicting priorities...",
    )
    session_id: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        description="Session identifier used to fetch the correct interview state.",
        example="user_123_session_1",
    )


class SubmitAnswerResponse(BaseModel):
    score: int = Field(..., ge=0, le=10, example=7)
    feedback: str = Field(..., example="Good structure, but add measurable impact.")
    next_question: str = Field(default="", example="How did you prioritize tasks under tight deadlines?")
    follow_up_question: str = Field(
        default="",
        description="Targeted follow-up generated from the latest answer.",
        example="What metric did you track to validate the improvement?",
    )
    waiting_for_next_step: bool = Field(
        default=False,
        description="Whether the client must choose follow-up or next question before continuing.",
    )
    interview_complete: bool = Field(
        default=False,
        description="True only when interview has reached target question count.",
    )
    critique: str = Field(
        default="",
        description="Short rubric-based critique of the latest answer.",
        example="Clear structure and context, but impact and trade-offs were underdeveloped.",
    )
    rewrite: str = Field(
        default="",
        description="Suggested improved answer draft in the candidate's style.",
        example="In this project, I inherited an API with 1.8s latency...",
    )
    debrief_actions: List[str] = Field(default_factory=list, description="End-of-interview action items.")
    next_round_target: str = Field(
        default="",
        description="Measurable target for the next round.",
        example="Score at least 8/10 while using one metric and one trade-off statement.",
    )
    curriculum_plan: List[str] = Field(
        default_factory=list,
        description="Short day-by-day plan derived from persistent weak areas.",
    )
    weak_topic_memory: List[str] = Field(
        default_factory=list,
        description="Top weak topics remembered across this session.",
    )
    final_evaluation: str = Field(
        default="",
        description="Overall interview performance summary. Present only when interview is complete.",
    )
    relevance_score: float = Field(default=0.0, ge=0, le=100)
    correctness_score: float = Field(default=0.0, ge=0, le=100)
    clarity_score: float = Field(default=0.0, ge=0, le=100)
    depth_score: float = Field(default=0.0, ge=0, le=100)
    confidence_score: float = Field(default=0.0, ge=0, le=1)
    technical_accuracy_pct: float = Field(default=0.0, ge=0, le=100)
    star_format_usage_pct: float = Field(default=0.0, ge=0, le=100)
    answer_length_words: int = Field(default=0, ge=0)
    response_time_seconds: float = Field(default=0.0, ge=0)
    evaluation_latency_ms: float = Field(default=0.0, ge=0)
    skill_overlap_pct: float = Field(default=0.0, ge=0, le=100)
    keyword_match_score: float = Field(default=0.0, ge=0, le=100)
    experience_alignment_score: float = Field(default=0.0, ge=0, le=100)
    ats_style_score: float = Field(default=0.0, ge=0, le=100)
    consistency_score: float = Field(default=0.0, ge=0, le=100)
    drift_score: float = Field(default=0.0, ge=0, le=100)


class InterviewAnswerResponse(SubmitAnswerResponse):
    pass


class AdvanceInterviewRequest(BaseModel):
    session_id: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        description="Session identifier used to fetch the correct interview state.",
        example="user_123_session_1",
    )
    choice: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        description="Either 'follow_up' or 'next_question'.",
        example="follow_up",
    )


class AdvanceInterviewResponse(BaseModel):
    question: str = Field(..., description="Chosen next question to present to the candidate.")


class FrameMessageRequest(BaseModel):
    message_type: str = Field(
        ...,
        description="One of: follow_up, thank_you, cold, connection, schedule.",
        example="follow_up",
    )
    channel: str = Field(..., description="'email' or 'linkedin'.", example="email")
    tone: str = Field(..., description="'professional', 'warm', or 'concise'.", example="professional")
    sender_name: str = Field(default="", description="Sign-off name.", example="Alex Rivera")
    recipient_name: str = Field(default="", description="Optional recipient first or full name.", example="Jordan")
    company: str = Field(default="", example="Acme Corp")
    role: str = Field(default="", example="Software Engineer Intern")
    notes: str = Field(default="", description="Optional bullet lines or context.", example="Referred by Sam.")


class FrameMessageResponse(BaseModel):
    message: str = Field(..., description="Draft the user can paste into email or LinkedIn.")
    confidence: str = Field(default="medium", example="high")
    rationale: str = Field(default="", example="Aligns tone and role with provided company context.")


class ResumeExperienceItem(BaseModel):
    title: str = ""
    company: str
    points: List[str]


class TailoredResumeData(BaseModel):
    summary: str
    experience: List[ResumeExperienceItem]
    skills: List[str]


class InterviewHistoryItem(BaseModel):
    question: str
    answer: Optional[str] = ""
    score: Optional[int] = None
    relevance_score: Optional[float] = 0.0
    correctness_score: Optional[float] = 0.0
    clarity_score: Optional[float] = 0.0
    depth_score: Optional[float] = 0.0
    confidence_score: Optional[float] = 0.0
    technical_accuracy_pct: Optional[float] = 0.0
    star_format_usage_pct: Optional[float] = 0.0
    answer_length_words: Optional[int] = 0
    response_time_seconds: Optional[float] = 0.0
    evaluation_latency_ms: Optional[float] = 0.0
    asked_at: Optional[str] = ""


class InterviewMemory(BaseModel):
    mode: str = ""
    job_description: str = ""
    resume: str = ""
    panel_mode: bool = False
    pressure_round: bool = False
    company_context: str = ""
    role_context: str = ""
    interview_date: str = ""
    panel_personas: List[str] = Field(default_factory=list)
    panel_turn_index: int = 0
    weak_topic_memory: List[str] = Field(default_factory=list)
    target_question_count: int = 6
    answered_count: int = 0
    pending_next_step: Dict[str, str] = Field(default_factory=dict)
    interview_complete: bool = False
    final_evaluation: str = ""
    debrief_actions: List[str] = Field(default_factory=list)
    next_round_target: str = ""
    curriculum_plan: List[str] = Field(default_factory=list)
    completed_at: str = ""
    system_metrics: Dict[str, float] = Field(default_factory=dict)
    resume_job_match: Dict[str, float] = Field(default_factory=dict)
    history: List[InterviewHistoryItem] = Field(default_factory=list)


class InterviewSessionListItem(BaseModel):
    session_id: str = Field(..., example="session-12")
    mode: str = Field(default="", example="behavioral")
    answered_count: int = Field(default=0, ge=0, example=3)
    target_question_count: int = Field(default=6, ge=1, example=6)
    interview_complete: bool = Field(default=False, example=False)
    updated_at: str = Field(default="", example="2026-04-26T20:30:00Z")


class InterviewSessionListResponse(BaseModel):
    sessions: List[InterviewSessionListItem] = Field(default_factory=list)


class InterviewSessionDetailResponse(BaseModel):
    session_id: str = Field(..., example="session-12")
    memory: InterviewMemory


class DeleteInterviewSessionResponse(BaseModel):
    deleted: bool = Field(default=True, example=True)
    session_id: str = Field(..., example="session-12")

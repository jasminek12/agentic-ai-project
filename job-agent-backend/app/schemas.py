from typing import List, Optional

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


class StartInterviewResponse(BaseModel):
    question: str = Field(..., example="Tell me about a time you resolved conflict in your team.")


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
    next_question: str = Field(..., example="How did you prioritize tasks under tight deadlines?")


class InterviewAnswerResponse(SubmitAnswerResponse):
    pass


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


class InterviewMemory(BaseModel):
    mode: str = ""
    job_description: str = ""
    resume: str = ""
    history: List[InterviewHistoryItem] = Field(default_factory=list)

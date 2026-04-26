from fastapi import APIRouter, HTTPException, status

from app.agents.resume_agent import tailor_resume
from app.schemas import ErrorResponse, TailorResumeRequest, TailoredResumeData


router = APIRouter(prefix="", tags=["resume"])


@router.post(
    "/tailor-resume",
    response_model=TailoredResumeData,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid client input."},
        500: {"model": ErrorResponse, "description": "Server-side processing error."},
    },
)
def tailor_resume_endpoint(payload: TailorResumeRequest):
    """
    Tailor a resume against a target job and return structured JSON.

    Example Request:
    {
      "resume_text": "Software Engineer with backend experience...",
      "job_description": "Looking for FastAPI and Python developer..."
    }

    Example Response:
    {
      "summary": "Backend-focused engineer...",
      "experience": [
        {
          "title": "Software Engineer",
          "company": "Acme",
          "points": ["Built ...", "Designed ...", "Improved ..."]
        }
      ],
      "skills": ["Python", "FastAPI", "PostgreSQL"]
    }
    """
    # Endpoint flow:
    # 1) Validate user input
    # 2) Generate tailored resume JSON via LLM
    # 3) Return structured JSON for frontend rendering/copy
    if not payload.resume_text.strip():
        raise HTTPException(status_code=400, detail={"error": "Resume text cannot be empty"})
    if not payload.job_description.strip():
        raise HTTPException(status_code=400, detail={"error": "Job description cannot be empty"})

    try:
        tailored_json = tailor_resume(payload.resume_text, payload.job_description)
        return tailored_json
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[DEBUG] /tailor-resume failed: {exc}")
        raise HTTPException(status_code=500, detail={"error": "Failed to tailor resume."}) from exc

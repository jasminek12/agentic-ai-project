from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.agents.resume_agent import tailor_resume
from app.config import BASE_DIR
from app.schemas import ErrorResponse, ResumeResponse, TailorResumeRequest
from app.utils.latex import compile_pdf, json_to_latex


router = APIRouter(prefix="", tags=["resume"])


@router.post(
    "/tailor-resume",
    response_model=ResumeResponse,
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid client input."},
        500: {"model": ErrorResponse, "description": "Server-side processing error."},
    },
)
def tailor_resume_endpoint(payload: TailorResumeRequest):
    """
    Tailor a resume against a target job and generate a downloadable PDF.

    Example Request:
    {
      "resume_text": "Software Engineer with backend experience...",
      "job_description": "Looking for FastAPI and Python developer..."
    }

    Example Response:
    {
      "message": "Returns a downloadable PDF stream."
    }
    """
    # Endpoint flow:
    # 1) Validate user input
    # 2) Generate tailored resume JSON via LLM
    # 3) Convert JSON to LaTeX and compile PDF
    # 4) Return PDF file directly for frontend download
    if not payload.resume_text.strip():
        raise HTTPException(status_code=400, detail={"error": "Resume text cannot be empty"})
    if not payload.job_description.strip():
        raise HTTPException(status_code=400, detail={"error": "Job description cannot be empty"})

    try:
        tailored_json = tailor_resume(payload.resume_text, payload.job_description)
        latex_content = json_to_latex(tailored_json)
        pdf_path = compile_pdf(latex_content)
        absolute_pdf_path = BASE_DIR / Path(pdf_path)
        return FileResponse(
            path=str(absolute_pdf_path),
            media_type="application/pdf",
            filename="tailored_resume.pdf",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[DEBUG] /tailor-resume failed: {exc}")
        raise HTTPException(status_code=500, detail={"error": "Failed to tailor resume."}) from exc

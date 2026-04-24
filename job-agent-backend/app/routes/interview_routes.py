from fastapi import APIRouter, HTTPException, status

from app.agents.interview_agent import evaluate_answer, generate_question
from app.schemas import (
    ErrorResponse,
    InterviewAnswerResponse,
    InterviewStartResponse,
    StartInterviewRequest,
    SubmitAnswerRequest,
)
from app.utils.memory import load_memory, reset_memory, save_memory


router = APIRouter(prefix="", tags=["interview"])


@router.post(
    "/start-interview",
    response_model=InterviewStartResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid client input."},
        500: {"model": ErrorResponse, "description": "Server-side processing error."},
    },
)
def start_interview(payload: StartInterviewRequest):
    """
    Start a new interview session and return the first generated question.

    Example Request:
    {
      "mode": "behavioral",
      "job_description": "Hiring backend engineer with FastAPI, Docker.",
      "resume": "Backend developer with 3 years of API experience...",
      "session_id": "user_123_session_1"
    }

    Example Response:
    {
      "question": "Tell me about a time you led a team through a deadline risk."
    }
    """
    # Endpoint flow:
    # 1) Validate mode and required text fields
    # 2) Reset and initialize interview memory
    # 3) Generate first question based on chosen mode
    if payload.mode not in {"behavioral", "technical"}:
        raise HTTPException(status_code=400, detail={"error": "Mode must be 'behavioral' or 'technical'"})
    if not payload.job_description.strip():
        raise HTTPException(status_code=400, detail={"error": "Job description cannot be empty"})
    if not payload.resume.strip():
        raise HTTPException(status_code=400, detail={"error": "Resume cannot be empty"})
    if not payload.session_id.strip():
        raise HTTPException(status_code=400, detail={"error": "Session ID is required"})

    try:
        memory = reset_memory(payload.session_id)
        memory["mode"] = payload.mode
        memory["job_description"] = payload.job_description
        memory["resume"] = payload.resume

        first_question = generate_question(payload.mode, payload.job_description, payload.resume, memory["history"])
        memory["history"].append({"question": first_question["question"], "answer": "", "score": None})
        save_memory(payload.session_id, memory)
        return first_question
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
    except Exception as exc:
        print(f"[DEBUG] /start-interview failed: {exc}")
        raise HTTPException(status_code=500, detail={"error": "Failed to start interview."}) from exc


@router.post(
    "/submit-answer",
    response_model=InterviewAnswerResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid client input."},
        500: {"model": ErrorResponse, "description": "Server-side processing error."},
    },
)
def submit_answer(payload: SubmitAnswerRequest):
    """
    Submit candidate answer, evaluate it, and return score + next adaptive question.

    Example Request:
    {
      "answer": "I handled a production outage by coordinating with SRE and backend teams...",
      "session_id": "user_123_session_1"
    }

    Example Response:
    {
      "score": 7,
      "feedback": "Good communication and structure; include measurable impact.",
      "next_question": "How would you design retry logic for a flaky downstream API?"
    }
    """
    # Endpoint flow:
    # 1) Load memory and locate last unanswered question
    # 2) Evaluate current answer with LLM
    # 3) Update memory history with score/answer
    # 4) Generate next question using adaptive score logic
    if not payload.answer.strip():
        raise HTTPException(status_code=400, detail={"error": "Answer cannot be empty"})
    if not payload.session_id.strip():
        raise HTTPException(status_code=400, detail={"error": "Session ID is required"})

    try:
        memory = load_memory(payload.session_id)
        if not memory.get("mode"):
            raise HTTPException(status_code=400, detail={"error": "Interview session not started"})

        history = memory.get("history", [])
        if not history:
            raise HTTPException(status_code=400, detail={"error": "No question found. Start interview first."})

        current_item = next((item for item in reversed(history) if not item.get("answer")), None)
        if not current_item:
            raise HTTPException(status_code=400, detail={"error": "No pending question found."})

        evaluation = evaluate_answer(current_item["question"], payload.answer)
        current_item["answer"] = payload.answer
        current_item["score"] = evaluation["score"]

        next_question = generate_question(
            memory["mode"],
            memory["job_description"],
            memory["resume"],
            history,
        )
        history.append({"question": next_question["question"], "answer": "", "score": None})
        memory["history"] = history
        save_memory(payload.session_id, memory)

        return {
            "score": evaluation["score"],
            "feedback": evaluation["feedback"],
            "next_question": next_question["question"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[DEBUG] /submit-answer failed: {exc}")
        raise HTTPException(status_code=500, detail={"error": "Failed to submit answer."}) from exc

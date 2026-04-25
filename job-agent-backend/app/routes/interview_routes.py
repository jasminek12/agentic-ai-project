from fastapi import APIRouter, HTTPException, status

from app.agents.interview_agent import (
    build_curriculum_plan,
    build_debrief_actions,
    evaluate_answer,
    generate_follow_up,
    generate_question,
)
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
        memory["panel_mode"] = payload.panel_mode
        memory["pressure_round"] = payload.pressure_round
        memory["company_context"] = payload.company_context
        memory["role_context"] = payload.role_context
        memory["interview_date"] = payload.interview_date or ""
        memory["panel_personas"] = (
            ["recruiter", "hiring_manager", "domain_expert"] if payload.panel_mode else []
        )
        memory["panel_turn_index"] = 0

        first_question = generate_question(
            payload.mode,
            payload.job_description,
            payload.resume,
            memory["history"],
            panel_mode=payload.panel_mode,
            pressure_round=payload.pressure_round,
            company_context=payload.company_context,
            role_context=payload.role_context,
            panel_personas=memory.get("panel_personas", []),
            panel_turn_index=memory.get("panel_turn_index", 0),
        )
        memory["history"].append(
            {
                "question": first_question["question"],
                "answer": "",
                "score": None,
                "persona": first_question.get("persona", ""),
                "focus_area": first_question.get("focus_area", ""),
            }
        )
        memory["panel_turn_index"] = int(memory.get("panel_turn_index", 0)) + 1
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

        evaluation = evaluate_answer(current_item["question"], payload.answer, memory.get("mode", "behavioral"))
        current_item["answer"] = payload.answer
        current_item["score"] = evaluation["score"]
        current_item["feedback"] = evaluation["feedback"]
        current_item["weak_topics"] = evaluation["weak_topics"]
        current_item["critique"] = evaluation["critique"]
        current_item["rewrite"] = evaluation["rewrite"]

        weak_topic_memory = list(memory.get("weak_topic_memory", []))
        weak_topic_memory.extend([str(t).strip() for t in evaluation["weak_topics"] if str(t).strip()])
        weak_topic_memory = weak_topic_memory[-60:]
        memory["weak_topic_memory"] = weak_topic_memory

        follow_up_question = generate_follow_up(
            current_item["question"],
            payload.answer,
            evaluation["weak_topics"],
            pressure_round=bool(memory.get("pressure_round", False)),
        )

        next_question = generate_question(
            memory["mode"],
            memory["job_description"],
            memory["resume"],
            history,
            panel_mode=bool(memory.get("panel_mode", False)),
            pressure_round=bool(memory.get("pressure_round", False)),
            company_context=memory.get("company_context", ""),
            role_context=memory.get("role_context", ""),
            panel_personas=memory.get("panel_personas", []),
            panel_turn_index=int(memory.get("panel_turn_index", 0)),
        )
        history.append(
            {
                "question": next_question["question"],
                "answer": "",
                "score": None,
                "persona": next_question.get("persona", ""),
                "focus_area": next_question.get("focus_area", ""),
            }
        )
        memory["panel_turn_index"] = int(memory.get("panel_turn_index", 0)) + 1
        memory["history"] = history
        save_memory(payload.session_id, memory)
        debrief = build_debrief_actions(evaluation["score"], weak_topic_memory)
        curriculum_plan = build_curriculum_plan(weak_topic_memory, memory.get("interview_date", ""))

        return {
            "score": evaluation["score"],
            "feedback": evaluation["feedback"],
            "next_question": next_question["question"],
            "follow_up_question": follow_up_question,
            "critique": evaluation["critique"],
            "rewrite": evaluation["rewrite"],
            "debrief_actions": debrief["actions"],
            "next_round_target": debrief["target"],
            "curriculum_plan": curriculum_plan,
            "weak_topic_memory": weak_topic_memory[-8:],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[DEBUG] /submit-answer failed: {exc}")
        raise HTTPException(status_code=500, detail={"error": "Failed to submit answer."}) from exc

from fastapi import APIRouter, HTTPException, status

from app.agents.interview_agent import (
    build_curriculum_plan,
    build_debrief_actions,
    estimate_question_count,
    evaluate_answer,
    generate_follow_up,
    generate_question,
    summarize_final_evaluation,
)
from app.schemas import (
    AdvanceInterviewRequest,
    AdvanceInterviewResponse,
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
        memory["target_question_count"] = estimate_question_count(payload.job_description, payload.mode)
        memory["answered_count"] = 0
        memory["pending_next_step"] = {}
        memory["interview_complete"] = False

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
        return {
            "question": first_question["question"],
            "interview_started": True,
            "target_question_count": int(memory.get("target_question_count", 6)),
        }
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
    Submit candidate answer, evaluate it, and return follow-up choice options.

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
    # 4) Prepare follow-up/next options; completion evaluation only at interview end
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
        if memory.get("pending_next_step"):
            raise HTTPException(
                status_code=400,
                detail={"error": "Choose follow-up or next question before submitting another answer."},
            )

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
        memory["answered_count"] = int(memory.get("answered_count", 0)) + 1
        answered_count = int(memory["answered_count"])
        target_question_count = int(memory.get("target_question_count", 6))
        interview_complete = answered_count >= target_question_count

        response_payload = {
            "score": evaluation["score"],
            "feedback": evaluation["feedback"],
            "next_question": "",
            "follow_up_question": "",
            "waiting_for_next_step": False,
            "interview_complete": interview_complete,
            "critique": evaluation["critique"],
            "rewrite": evaluation["rewrite"],
            "debrief_actions": [],
            "next_round_target": "",
            "curriculum_plan": [],
            "weak_topic_memory": weak_topic_memory[-8:],
            "final_evaluation": "",
        }

        if interview_complete:
            memory["interview_complete"] = True
            debrief = build_debrief_actions(evaluation["score"], weak_topic_memory)
            curriculum_plan = build_curriculum_plan(weak_topic_memory, memory.get("interview_date", ""))
            response_payload["debrief_actions"] = debrief["actions"]
            response_payload["next_round_target"] = debrief["target"]
            response_payload["curriculum_plan"] = curriculum_plan
            response_payload["final_evaluation"] = summarize_final_evaluation(
                history, memory.get("mode", "behavioral")
            )
        else:
            follow_up_question = generate_follow_up(
                current_item["question"],
                payload.answer,
                evaluation["weak_topics"],
                pressure_round=bool(memory.get("pressure_round", False)),
                score=evaluation["score"],
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
            memory["pending_next_step"] = {
                "follow_up_question": follow_up_question,
                "next_question": next_question["question"],
                "next_persona": next_question.get("persona", ""),
                "next_focus_area": next_question.get("focus_area", ""),
            }
            response_payload["follow_up_question"] = follow_up_question
            response_payload["next_question"] = next_question["question"]
            response_payload["waiting_for_next_step"] = True

        memory["history"] = history
        save_memory(payload.session_id, memory)
        return response_payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[DEBUG] /submit-answer failed: {exc}")
        raise HTTPException(status_code=500, detail={"error": "Failed to submit answer."}) from exc


@router.post(
    "/advance-interview",
    response_model=AdvanceInterviewResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid client input."},
        500: {"model": ErrorResponse, "description": "Server-side processing error."},
    },
)
def advance_interview(payload: AdvanceInterviewRequest):
    if payload.choice not in {"follow_up", "next_question"}:
        raise HTTPException(status_code=400, detail={"error": "Choice must be 'follow_up' or 'next_question'."})

    try:
        memory = load_memory(payload.session_id)
        if memory.get("interview_complete"):
            raise HTTPException(status_code=400, detail={"error": "Interview already completed."})

        pending = memory.get("pending_next_step", {})
        if not pending:
            raise HTTPException(status_code=400, detail={"error": "No pending follow-up decision found."})

        selected_question = pending.get("follow_up_question") if payload.choice == "follow_up" else pending.get(
            "next_question"
        )
        if not selected_question:
            raise HTTPException(status_code=400, detail={"error": "Selected question is unavailable."})

        history = memory.get("history", [])
        history.append(
            {
                "question": selected_question,
                "answer": "",
                "score": None,
                "persona": pending.get("next_persona", ""),
                "focus_area": pending.get("next_focus_area", ""),
            }
        )
        memory["history"] = history
        memory["pending_next_step"] = {}
        memory["panel_turn_index"] = int(memory.get("panel_turn_index", 0)) + 1
        save_memory(payload.session_id, memory)
        return {"question": selected_question}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[DEBUG] /advance-interview failed: {exc}")
        raise HTTPException(status_code=500, detail={"error": "Failed to advance interview."}) from exc

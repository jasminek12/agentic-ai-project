from fastapi import APIRouter, HTTPException, status

from app.agents.outreach_agent import frame_professional_message
from app.schemas import ErrorResponse, FrameMessageRequest, FrameMessageResponse


router = APIRouter(prefix="", tags=["outreach"])


ALLOWED_TYPES = frozenset({"follow_up", "thank_you", "cold", "connection", "schedule"})
ALLOWED_CHANNELS = frozenset({"email", "linkedin"})
ALLOWED_TONES = frozenset({"professional", "warm", "concise"})


@router.post(
    "/frame-message",
    response_model=FrameMessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid client input."},
        500: {"model": ErrorResponse, "description": "Server-side processing error."},
    },
)
def frame_message(payload: FrameMessageRequest):
    """
    Generate a professional outreach draft (email or LinkedIn style) using the LLM.
    """
    if payload.message_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail={"error": f"message_type must be one of: {', '.join(sorted(ALLOWED_TYPES))}"},
        )
    if payload.channel not in ALLOWED_CHANNELS:
        raise HTTPException(
            status_code=400,
            detail={"error": "channel must be 'email' or 'linkedin'."},
        )
    if payload.tone not in ALLOWED_TONES:
        raise HTTPException(
            status_code=400,
            detail={"error": "tone must be 'professional', 'warm', or 'concise'."},
        )

    if not (
        (payload.role or "").strip()
        or (payload.company or "").strip()
        or (payload.recipient_name or "").strip()
        or (payload.notes or "").strip()
    ):
        raise HTTPException(
            status_code=400,
            detail={"error": "Provide at least one of: role, company, recipient_name, or notes."},
        )

    try:
        result = frame_professional_message(
            message_type=payload.message_type,
            channel=payload.channel,
            tone=payload.tone,
            sender_name=(payload.sender_name or "").strip(),
            recipient_name=(payload.recipient_name or "").strip(),
            company=(payload.company or "").strip(),
            role=(payload.role or "").strip(),
            notes=(payload.notes or "").strip(),
        )
        return FrameMessageResponse(
            message=result["message"],
            confidence=result["confidence"],
            rationale=result["rationale"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail={"error": str(exc)}) from exc
    except Exception as exc:
        print(f"[DEBUG] /frame-message failed: {exc}")
        raise HTTPException(status_code=500, detail={"error": "Failed to frame message."}) from exc

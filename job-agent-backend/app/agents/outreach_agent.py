import json
import re
from typing import Any, Dict

from app.utils.llm import call_llm_with_system


def _extract_json_object(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in LLM output.")
        return json.loads(match.group(0))


SYSTEM = """You are an expert career coach who writes concise, professional outreach for job seekers.
Rules:
- Sound human and specific; avoid generic filler.
- Match the requested channel length: LinkedIn stays short (roughly under 900 characters); email can use short paragraphs.
- Use appropriate greeting when a recipient name is given (e.g. Hello Firstname,).
- Sign off with the sender name provided.
- Never invent employers, job offers, or conversations that did not happen.
- Return ONLY valid JSON with keys: message (string), confidence (string: high, medium, or low), rationale (one short sentence string)."""


def frame_professional_message(
    *,
    message_type: str,
    channel: str,
    tone: str,
    sender_name: str,
    recipient_name: str,
    company: str,
    role: str,
    notes: str,
) -> Dict[str, str]:
    purpose_map = {
        "follow_up": "Follow up on a submitted job application.",
        "thank_you": "Thank-you note after an interview or conversation.",
        "cold": "Cold outreach expressing interest in a role or team.",
        "connection": "Short connection or intro request (especially for LinkedIn).",
        "schedule": "Politely request a brief call or meeting.",
    }
    purpose = purpose_map.get(message_type, purpose_map["cold"])

    user = f"""
Purpose type: {message_type}
Purpose: {purpose}

Channel: {channel}  (email = multi-paragraph OK; linkedin = brief, scannable)

Tone: {tone}  (professional = formal; warm = friendly but still professional; concise = fewer words)

Sender name (sign as this person): {sender_name or "Candidate"}

Recipient first name if known (optional): {recipient_name or "(none)"}

Company (optional): {company or "(none)"}

Role or opportunity: {role or "(none)"}

Bullet notes to weave in if relevant (optional):
{notes or "(none)"}

Return STRICT JSON only:
{{
  "message": "full draft text the user can paste",
  "confidence": "high|medium|low",
  "rationale": "one sentence"
}}
""".strip()

    raw = call_llm_with_system(system=SYSTEM, user=user, temperature=0.45)
    parsed = _extract_json_object(raw)
    message = (parsed.get("message") or "").strip()
    if not message:
        raise ValueError("LLM returned an empty message.")
    confidence = str(parsed.get("confidence") or "medium").strip().lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"
    rationale = str(parsed.get("rationale") or "").strip()
    if not rationale:
        rationale = "Draft generated from your inputs."
    return {"message": message, "confidence": confidence, "rationale": rationale}

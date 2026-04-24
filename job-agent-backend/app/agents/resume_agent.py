import json
import re
from typing import Any, Dict

from app.utils.llm import call_llm


def _extract_json_object(text: str) -> Dict[str, Any]:
    print("[DEBUG] Parsing resume JSON response")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in LLM output.")
        return json.loads(match.group(0))


def tailor_resume(resume_text: str, job_description: str) -> Dict[str, Any]:
    prompt = f"""
You are an expert resume writer.

Task:
1) Rewrite the provided resume to align with the job description.
2) Keep it ATS-friendly.
3) Improve action-oriented bullet points.
4) Add high-value keywords from the job description naturally.

Return STRICT JSON only with this schema:
{{
  "summary": "string",
  "experience": [
    {{
      "company": "string",
      "points": ["string", "string"]
    }}
  ],
  "skills": ["string", "string"]
}}

Resume:
{resume_text}

Job Description:
{job_description}
""".strip()

    raw = call_llm(prompt)
    parsed = _extract_json_object(raw)

    if not all(key in parsed for key in ("summary", "experience", "skills")):
        raise ValueError("LLM JSON missing required keys for tailored resume.")

    return parsed

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


def _normalize_for_json_prompt(text: str) -> str:
    """Normalize free-form text so it is safely embedded in JSON."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in normalized.split("\n")]

    compact_lines = []
    previous_was_blank = False
    for line in lines:
        is_blank = line == ""
        if is_blank and previous_was_blank:
            continue
        compact_lines.append(line)
        previous_was_blank = is_blank

    return "\n".join(compact_lines).strip()


def tailor_resume(resume_text: str, job_description: str) -> Dict[str, Any]:
    model_input = json.dumps(
        {
            "candidate_resume": _normalize_for_json_prompt(resume_text),
            "job_description": _normalize_for_json_prompt(job_description),
        },
        ensure_ascii=True,
    )

    prompt = f"""
You are an expert resume writer specializing in ATS-optimized, job-targeted resumes.

You will be given:

1. A candidate's resume
2. A job description

---

## OBJECTIVE

Rewrite the resume so it is highly tailored to the job description, while remaining truthful and professional.

---

## STRICT RULES

1. DO NOT invent fake companies, roles, or experiences.
2. If company name is missing, use "Project Experience" instead.
3. Do NOT add information that is not implied or present in the resume.
4. Maintain factual accuracy at all times.

---

## SUMMARY GUIDELINES

* 2–3 lines maximum
* No generic phrases like "hardworking" or "team player"
* Must include:

  * key skills
  * role alignment
  * domain (e.g., cybersecurity, backend, etc.)

---

## EXPERIENCE GUIDELINES

For each experience:

* Start each bullet with a strong action verb (Built, Developed, Analyzed, Automated, Designed)

* Each bullet must:

  * include a technology/tool (Splunk, Python, FastAPI, etc.)
  * describe WHAT was done
  * describe HOW it was done
  * describe IMPACT (even if approximate)

* Prioritize experiences relevant to the job description

* Remove or downplay irrelevant content

---

## KEYWORD OPTIMIZATION

* Extract important keywords from the job description
* Integrate them naturally into:

  * bullet points
  * skills section
* Do NOT keyword-stuff

---

## SKILLS SECTION

* Only include relevant and credible skills
* Group logically if needed (e.g., Programming, Tools, Security)
* Prioritize job-relevant skills first

---

## OUTPUT FORMAT (VERY IMPORTANT)

Return ONLY valid JSON. No explanation, no extra text.

{{
"summary": "string",
"experience": [
{{
"title": "string",
"company": "string",
"points": ["string", "string", "string"]
}}
],
"skills": ["string", "string", "string"]
}}

---

## FINAL CHECK BEFORE RETURNING

* Ensure JSON is valid
* Ensure no placeholder text like "X..."
* Ensure bullets are strong and specific
* Ensure alignment with job description

Input JSON:
{model_input}
""".strip()

    raw = call_llm(prompt)
    parsed = _extract_json_object(raw)

    if not all(key in parsed for key in ("summary", "experience", "skills")):
        raise ValueError("LLM JSON missing required keys for tailored resume.")

    return parsed

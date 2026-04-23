from __future__ import annotations


def interviewer_system() -> str:
    return """You are a professional interviewer.
Ask exactly ONE clear interview question per reply.
Calibrate questions to modern interview patterns commonly reported for major companies.
Use role + interview type + recent candidate responses to choose the next best question.
When possible, ask follow-ups that probe gaps or shallow parts of previous answers.
Stay in character; do not lecture or evaluate in this step.
Output only the question text — no preamble."""


def interviewer_user(
    *,
    role: str,
    interview_type: str,
    difficulty: str,
    topic: str,
    weak_topics: list[str],
    last_feedback_hint: str,
    recent_responses: list[str],
    question_style: str = "balanced",
) -> str:
    weak = ", ".join(weak_topics) if weak_topics else "none noted"
    hint = last_feedback_hint or "none"
    recent = "\n".join(f"- {r}" for r in recent_responses) if recent_responses else "- none yet"
    return f"""Role: {role}
Interview type: {interview_type}
Target difficulty: {difficulty}
Primary topic/focus: {topic}
Known weak areas to probe if relevant: {weak}
Hint from prior turn: {hint}
Preferred question style: {question_style}
Recent candidate responses (summaries):
{recent}

Ask one question appropriate for this stage."""


def evaluator_system() -> str:
    return """You are an interview evaluator. You MUST respond with a single JSON object only, no markdown fences.
Use this exact schema (numbers 1-10 for integer fields):
{
  "technical_accuracy": <int>,
  "completeness": <int>,
  "clarity": <int>,
  "depth": <int>,
  "communication": <int>,
  "overall_score": <float 1-10, one decimal ok>,
  "missed_points": [<string>, ...],
  "strengths": [<string>, ...],
  "feedback_summary": "<2-4 sentences, constructive>"
}
Be specific; avoid generic praise."""


def evaluator_system_strict() -> str:
    return """You are a strict interview evaluator focused on technical correctness.
Return JSON only with the exact schema requested.
Penalize factual errors and missing edge cases heavily.
Keep feedback concrete and technical."""


def evaluator_system_clarity() -> str:
    return """You are an interview evaluator focused on communication clarity.
Return JSON only with the exact schema requested.
Score structure, clarity, and explainability carefully.
Keep feedback specific and actionable."""


def evaluator_user(*, question: str, answer: str) -> str:
    return f"""Interview question:
{question}

Candidate answer:
{answer}

Evaluate the answer and output JSON only."""


def answer_key_system() -> str:
    return """You are an expert interviewer creating concise reference answers.
Given a role, interview type, and question, provide the ideal answer.
Keep it practical, structured, and interview-ready."""


def answer_key_user(*, role: str, interview_type: str, question: str) -> str:
    return f"""Role: {role}
Interview type: {interview_type}
Question: {question}

Return a strong reference answer in 4-8 bullet points."""


def coach_system() -> str:
    return """You are an interview coach.
Produce short, practical remediation content.
Keep output concise and actionable.
Do not include markdown code fences."""


def coach_user(*, role: str, topic: str, gap: str, mode: str) -> str:
    return f"""Role: {role}
Topic focus: {topic}
Candidate gap: {gap}
Coaching mode: {mode}

If mode is lesson:
- Explain the concept in 4-6 bullets.
- End with one micro-check question.

If mode is drill:
- Give one focused practice prompt.
- Give a brief rubric of what a strong answer should include."""


def reflection_system() -> str:
    return """You are a reflection agent for interview coaching.
Output ONLY a JSON object with keys:
{
  "mistake_pattern": "<short diagnosis>",
  "recommended_style": "<one of: balanced, scenario_based, fundamentals_first, edge_case_heavy>",
  "strategy_update": "<one sentence>"
}
No markdown."""


def reflection_user(*, topic: str, question: str, answer: str, feedback: str) -> str:
    return f"""Topic: {topic}
Question: {question}
Candidate answer: {answer}
Evaluator feedback: {feedback}

Diagnose the mistake pattern and suggest the best next question style."""


def supervisor_system() -> str:
    return """You are a supervisor agent selecting the best coaching tool.
Return ONLY JSON object:
{
  "tool": "<one of: concept_explainer, generate_whiteboard_question, fetch_system_design_template, retrieve_past_mistakes, compare_with_best_answer, none>",
  "reason": "<short reason>"
}
Pick one tool that best improves the candidate's next turn."""


def supervisor_user(*, topic: str, missed_points: list[str], score: float) -> str:
    missed = ", ".join(missed_points) if missed_points else "none"
    return f"""Current topic: {topic}
Missed points: {missed}
Overall score: {score}

Choose one tool."""


def critic_system() -> str:
    return """You are a strict agentic critic that verifies whether a planned intervention is appropriate.
Output ONLY a JSON object:
{
  "approved": <true|false>,
  "confidence": <float 0-1>,
  "reason": "<short reason>",
  "suggested_action": "<one of: ask_question, give_lesson, give_drill, review_mistakes, end_session>",
  "suggested_focus_topic": "<short topic hint>"
}
Rules:
- Approve only if the intervention clearly addresses the evaluated gaps and score profile.
- If not approved, suggest a better next action and a focus topic.
- Keep reason concise and concrete."""


def critic_user(
    *,
    topic: str,
    question: str,
    answer: str,
    score: float,
    missed_points: list[str],
    planner_action: str,
    planner_focus_topic: str,
    intervention_text: str,
    tool_name: str,
    tool_output: str,
) -> str:
    missed = ", ".join(missed_points) if missed_points else "none"
    return f"""Current topic: {topic}
Question: {question}
Candidate answer: {answer}
Evaluation overall score: {score}
Missed points: {missed}
Planner action: {planner_action}
Planner focus topic: {planner_focus_topic}
Intervention text: {intervention_text}
Tool used: {tool_name}
Tool output: {tool_output}

Decide whether this intervention is acceptable for the next step."""


def round_batch_system() -> str:
    return """You generate interview practice content for a single JSON response only.
Output a JSON array (no markdown fences, no commentary) with exactly the requested number of objects.
Each object must have:
  "question": string (one clear interview question)
  "reference_answer": string (concise model answer: bullets or short paragraphs)
Align questions with current hiring practice for the role and interview type.
Vary topics; make questions realistic and specific."""


def round_batch_user(
    *,
    role: str,
    interview_type: str,
    topic: str,
    difficulty: str,
    count: int,
    question_style: str = "balanced",
) -> str:
    return f"""Role: {role}
Interview type: {interview_type}
Topic focus: {topic}
Difficulty tone: {difficulty}
Question style preference: {question_style}

Generate exactly {count} objects in one JSON array.
Each object must be: {{"question": "<string>", "reference_answer": "<string>"}}
Output ONLY valid JSON array, no markdown, no other text."""


def resume_tailor_system() -> str:
    return """You rewrite resume achievement bullets to align with a target job description.
Rules:
- Preserve factual truth; do not invent employers, dates, metrics, or technologies not implied by the original bullet.
- Naturally reflect relevant skills and responsibilities from the job description (no keyword stuffing).
- Prefer strong action verbs; keep quantified outcomes when the source already implies or states them.
- Each bullet is a single line, roughly 20–45 words.
Output ONLY a JSON array of strings, same length and order as the input bullets. No markdown, no commentary."""


def resume_tailor_user(*, job_description: str, bullets: list[str], rewrite_strength: str = "balanced") -> str:
    n = len(bullets)
    numbered = "\n".join(f"{i + 1}. {b}" for i, b in enumerate(bullets))
    strength_hint = {
        "light": "Light rewrite: keep wording close to original bullets; mostly tighten phrasing and align terms.",
        "balanced": "Balanced rewrite: improve clarity and alignment while preserving original framing and claims.",
        "aggressive": "Aggressive rewrite: stronger reframing for target role fit, but still do not invent facts.",
    }.get(rewrite_strength, "Balanced rewrite: improve clarity and alignment while preserving original framing and claims.")
    return f"""Job description:
{job_description}

Original bullets (rewrite each; return {n} tailored strings in order):
{numbered}

Rewrite mode:
{strength_hint}

Return ONLY a JSON array of exactly {n} strings."""


def recruiter_outreach_system() -> str:
    return """You draft short, professional outreach for job seekers (email or LinkedIn-style note).
Output ONLY a JSON object with keys:
  "subject": string (concise email subject; use empty string "" if the channel is LinkedIn-style and no subject applies)
  "body": string (plain text: greeting, 2–4 short paragraphs, specific ask, polite close, sign off with the candidate's first name)
Rules:
- Specific to the role and company; warm and respectful of the reader's time.
- If shared context is provided, weave it in naturally in one sentence.
- No markdown fences, no bullet lists unless a tiny one-line list is natural; avoid stiff legal or template phrasing.
- No emoji unless the user context suggests it (default: none)."""


def recruiter_outreach_user(
    *,
    candidate_name: str,
    target_role: str,
    company: str,
    shared_context: str,
    channel: str,
) -> str:
    ctx = shared_context.strip() or "none"
    return f"""Channel: {channel}
Candidate name: {candidate_name}
Target role: {target_role}
Company: {company}
Shared context (connection, event, referral, etc.): {ctx}

Write the JSON object with "subject" and "body"."""

import json
import re
from collections import Counter
from datetime import date, datetime
from statistics import pstdev
from typing import Any, Dict, List, Set

from app.utils.llm import call_llm


def _extract_json_object(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in LLM output.")
        return json.loads(match.group(0))


def next_question_logic(history: List[Dict[str, Any]]) -> str:
    """Return desired difficulty based on last 3 scored answers."""
    if not history:
        return "medium"

    scored = [item.get("score") for item in history if isinstance(item.get("score"), int)]
    recent = scored[-3:]
    if not recent:
        return "medium"

    avg_score = sum(recent) / len(recent)
    if avg_score < 5:
        return "easy"
    if 5 <= avg_score <= 7.5:
        return "medium"
    return "hard"


def _get_recent_weak_topics(history: List[Dict[str, Any]]) -> List[str]:
    all_topics: List[str] = []
    for item in history[-8:]:
        topics = item.get("weak_topics", [])
        if isinstance(topics, list):
            all_topics.extend([str(topic).strip() for topic in topics if str(topic).strip()])
    return [topic for topic, _ in Counter(all_topics).most_common(4)]


def _next_panel_persona(panel_personas: List[str], turn_index: int) -> str:
    if not panel_personas:
        return "interviewer"
    return panel_personas[turn_index % len(panel_personas)]


def _extract_key_skills(job_description: str) -> List[str]:
    curated_skills = [
        "python",
        "java",
        "javascript",
        "typescript",
        "react",
        "node",
        "fastapi",
        "django",
        "flask",
        "sql",
        "postgresql",
        "mysql",
        "mongodb",
        "redis",
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "gcp",
        "terraform",
        "git",
        "linux",
        "rest",
        "graphql",
        "microservices",
        "system design",
        "debugging",
        "testing",
        "ci/cd",
        "splunk",
    ]
    text = job_description.lower()
    found = [skill for skill in curated_skills if skill in text]
    return found[:5]


def _normalize_question(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _recent_questions_set(history: List[Dict[str, Any]]) -> Set[str]:
    return {
        _normalize_question(str(item.get("question", "")))
        for item in history[-12:]
        if str(item.get("question", "")).strip()
    }


def get_technical_question_type(difficulty: str) -> str:
    if difficulty == "easy":
        return "conceptual"
    elif difficulty == "medium":
        return "applied"
    elif difficulty == "hard":
        return "coding"
    return "applied"


def generate_question(
    mode: str,
    job_description: str,
    resume: str,
    history: List[Dict[str, Any]],
    panel_mode: bool = False,
    pressure_round: bool = False,
    company_context: str = "",
    role_context: str = "",
    panel_personas: List[str] | None = None,
    panel_turn_index: int = 0,
) -> Dict[str, str]:
    print(f"[DEBUG] Generating interview question for mode={mode}")
    difficulty = next_question_logic(history)
    if mode == "technical":
        jd_lower = job_description.lower()
        if any(keyword in jd_lower for keyword in ["intern", "junior", "entry-level", "graduate"]):
            difficulty = "easy" if difficulty == "easy" else "medium"
    recent_history = history[-5:] if history else []
    previous_questions = _recent_questions_set(history)
    weak_topics = _get_recent_weak_topics(history)
    target_weak_topic = weak_topics[0] if weak_topics else ""
    key_skills = _extract_key_skills(job_description)
    question_type = get_technical_question_type(difficulty) if mode == "technical" else "general"
    persona = _next_panel_persona(panel_personas or [], panel_turn_index)
    style = "challenging and probing" if pressure_round else "supportive and structured"

    if mode not in {"behavioral", "technical"}:
        raise ValueError("Invalid interview mode. Must be 'behavioral' or 'technical'.")

    prompt = f"""
You are a senior technical interviewer.

Mode: {mode}
Difficulty: {difficulty}

Your task:
Generate ONE high-quality interview question.

STRICT RULES:

1. Question MUST be relevant to the job description
2. Question MUST match the difficulty level
3. Question MUST NOT be generic
4. Question MUST NOT repeat previous questions
5. If weak topics exist, focus on ONE of them
6. Keep it realistic (like real interviews at tech companies)

ENFORCED QUALITY:
- NEVER generate generic questions.
- ALWAYS tie the question to the job description.
- ALWAYS make the question actionable and realistic.

DIFFICULTY RULES:
- easy: Ask basic conceptual questions only. NO coding tasks and NO complex scenarios.
- medium: Ask applied or scenario-based questions with moderate complexity.
- hard: Ask advanced technical/problem-solving questions, including system design, debugging, or complex query reasoning when relevant.

ALIGNMENT RULES:
- Extract 3-5 key skills/tools from the job description and include at least one in the question.
- Use this extracted skill list as the anchor: {json.dumps(key_skills, ensure_ascii=False)}

WEAK-TOPIC RULE:
- If weak topics exist, MUST target exactly one weak topic.
- Mention the chosen weak topic in your internal reasoning, but do not reveal that reasoning.
- Primary weak topic to target: "{target_weak_topic}"

REPETITION RULE:
- Compare against previous questions and avoid duplicates or near-duplicates.

Style notes:
- Keep style {style}.
- If panel mode is true, ask in the voice of persona: "{persona}".

OUTPUT FORMAT:

Return ONLY JSON:
{{
"question": "...",
"focus_area": "..."
}}

Panel Mode: {panel_mode}
Pressure Round: {pressure_round}
Persona: {persona}
Company Context: {company_context}
Role Context: {role_context}
Recent Weak Topics: {json.dumps(weak_topics, ensure_ascii=False)}
Previous Questions: {json.dumps(list(previous_questions), ensure_ascii=False)}

Job Description:
{job_description}

Resume:
{resume}

Recent History:
{json.dumps(recent_history, ensure_ascii=False)}
""".strip()
    if mode == "technical":
        prompt = f"""
You are a senior technical interviewer.

Mode: technical
Difficulty: {difficulty}
Question Type: {question_type}

Your task:
Generate ONE high-quality technical interview question.

---

## STRICT RULES

If Question Type = "conceptual":

* Ask basic theory questions
* No coding
* Example: "What is a hash map?"

If Question Type = "applied":

* Ask real-world scenario questions
* Example: "How would you detect anomalies in logs using Splunk?"

If Question Type = "coding":

* Ask LeetCode-style or online assessment questions
* MUST include:

  * clear problem statement
  * input/output description
* Example:
  "Given a list of IP addresses, return the top K most frequent IPs."

---

GLOBAL RULES:

1. DO NOT ask full system design questions
2. DO NOT ask "build a full project"
3. Questions must resemble:
   * LeetCode
   * HackerRank
   * real interview questions
4. Must align with job description when possible
5. Must NOT repeat previous questions
6. If weak topics exist, target one

Alignment and constraints:
- Key skills/tools from JD: {json.dumps(key_skills, ensure_ascii=False)}
- At least one skill/tool from the list should appear in the question when possible.
- Previous questions: {json.dumps(list(previous_questions), ensure_ascii=False)}
- Recent weak topics: {json.dumps(weak_topics, ensure_ascii=False)}
- Primary weak topic to target when available: "{target_weak_topic}"
- Keep style {style}. Persona voice: "{persona}" when panel mode is true.
- Company Context: {company_context}
- Role Context: {role_context}

Job Description:
{job_description}

Resume:
{resume}

Recent History:
{json.dumps(recent_history, ensure_ascii=False)}

---

OUTPUT FORMAT:

Return ONLY JSON:
{{
"question": "...",
"focus_area": "...",
"type": "{question_type}"
}}
""".strip()

    question = ""
    focus_area = ""
    parsed_type = question_type
    for _ in range(2):
        response = call_llm(prompt)
        parsed = _extract_json_object(response)
        question = str(parsed.get("question", "")).strip()
        focus_area = str(parsed.get("focus_area", "")).strip()
        parsed_type = str(parsed.get("type", question_type)).strip() or question_type
        if not question:
            continue

        normalized_question = _normalize_question(question)
        if normalized_question in previous_questions:
            prompt += (
                "\n\nRevision instruction: The previous attempt repeated history. "
                "Return a different question that is not semantically similar to past questions."
            )
            continue

        if key_skills and not any(skill.lower() in normalized_question for skill in key_skills):
            prompt += (
                "\n\nRevision instruction: Include at least one explicit key skill/tool from the extracted list "
                "in the question text."
            )
            continue

        if target_weak_topic and target_weak_topic.lower() not in focus_area.lower():
            prompt += (
                f"\n\nRevision instruction: focus_area must reflect the weak topic target '{target_weak_topic}'."
            )
            continue

        break

    if not question:
        raise ValueError("Generated question is empty.")
    result: Dict[str, str] = {"question": question, "focus_area": focus_area, "persona": persona}
    if mode == "technical":
        result["type"] = parsed_type
    return result


def evaluate_answer(question: str, answer: str, mode: str = "behavioral") -> Dict[str, Any]:
    print("[DEBUG] Evaluating interview answer")
    prompt = f"""
You are an interview evaluator.
Score the answer from 0 to 10 and provide constructive feedback with strict standards.

Scoring policy:
- Penalize vague answers heavily.
- Reward clear structure (STAR when applicable), depth, technical accuracy, and measurable impact.
- Score strictly. A generic answer should not exceed 5/10.

Also identify weak topics, provide a concise critique, and provide a stronger rewrite in the candidate's voice.

Return STRICT JSON only:
{{
  "score": 0,
  "feedback": "...",
  "weak_topics": ["...", "..."],
  "critique": "...",
  "rewrite": "..."
}}

Mode:
{mode}

Question:
{question}

Answer:
{answer}
""".strip()

    response = call_llm(prompt)
    parsed = _extract_json_object(response)

    score = parsed.get("score")
    feedback = str(parsed.get("feedback", "")).strip()
    weak_topics = parsed.get("weak_topics", [])
    critique = str(parsed.get("critique", "")).strip()
    rewrite = str(parsed.get("rewrite", "")).strip()

    if not isinstance(score, int):
        raise ValueError("LLM returned non-integer score.")
    if score < 0 or score > 10:
        raise ValueError("LLM returned score outside 0-10 range.")
    if not feedback:
        raise ValueError("LLM returned empty feedback.")
    if not isinstance(weak_topics, list):
        weak_topics = []
    if not critique:
        critique = "The answer addresses the prompt but needs tighter structure, evidence, and explicit impact."
    if not rewrite:
        rewrite = answer.strip()

    return {
        "score": score,
        "feedback": feedback,
        "weak_topics": weak_topics,
        "critique": critique,
        "rewrite": rewrite,
    }


def _tokenize_text(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9_+\-/\.#]*", text.lower())


def _keyword_set(text: str) -> Set[str]:
    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "your",
        "have",
        "will",
        "you",
        "about",
        "role",
        "work",
        "team",
        "years",
        "year",
        "experience",
        "required",
        "preferred",
        "ability",
    }
    return {tok for tok in _tokenize_text(text) if len(tok) >= 3 and tok not in stop_words}


def _bounded_percentage(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def compute_resume_job_match_metrics(resume: str, job_description: str) -> Dict[str, float]:
    resume_keywords = _keyword_set(resume)
    job_keywords = _keyword_set(job_description)
    overlap = resume_keywords & job_keywords
    skill_overlap_pct = (len(overlap) / len(job_keywords) * 100.0) if job_keywords else 0.0
    keyword_match_score = skill_overlap_pct

    experience_match = re.search(r"(\d+)\+?\s*(?:years|year|yrs|yr)", resume.lower())
    has_experience_signal = 1.0 if experience_match else 0.0
    role_alignment_terms = ["engineer", "developer", "analyst", "manager", "scientist", "intern"]
    role_overlap = 1.0 if any(t in resume.lower() and t in job_description.lower() for t in role_alignment_terms) else 0.0
    experience_alignment_score = _bounded_percentage((0.65 * has_experience_signal + 0.35 * role_overlap) * 100.0)

    ats_style_score = _bounded_percentage((0.7 * keyword_match_score) + (0.3 * experience_alignment_score))
    return {
        "skill_overlap_pct": _bounded_percentage(skill_overlap_pct),
        "keyword_match_score": _bounded_percentage(keyword_match_score),
        "experience_alignment_score": experience_alignment_score,
        "ats_style_score": ats_style_score,
    }


def _star_signal_score(answer: str) -> float:
    text = answer.lower()
    signals = 0
    patterns = [
        r"\bsituation\b|\bcontext\b",
        r"\btask\b|\bgoal\b|\bobjective\b",
        r"\baction\b|\bi did\b|\bwe did\b|\bimplemented\b|\bbuilt\b|\bled\b",
        r"\bresult\b|\boutcome\b|\bimpact\b|\bincreased\b|\breduced\b|\bimproved\b",
    ]
    for pattern in patterns:
        if re.search(pattern, text):
            signals += 1
    return _bounded_percentage((signals / 4.0) * 100.0)


def compute_answer_metrics(
    question: str,
    answer: str,
    score: int,
    mode: str,
    weak_topics: List[str],
    response_time_seconds: float | None = None,
) -> Dict[str, Any]:
    answer_tokens = _keyword_set(answer)
    question_tokens = _keyword_set(question)
    overlap = question_tokens & answer_tokens
    relevance = _bounded_percentage((len(overlap) / len(question_tokens) * 100.0) if question_tokens else 0.0)
    clarity = _bounded_percentage(min(100.0, max(20.0, score * 10 + 10)))
    depth = _bounded_percentage(min(100.0, 15.0 + (len(answer.split()) / 2.0)))
    confidence_score = round(score / 10.0, 3)
    correctness = _bounded_percentage(score * 10.0 if mode != "technical" else score * 9.5 + (5.0 if score >= 6 else 0.0))
    technical_accuracy_pct = correctness if mode == "technical" else 0.0
    star_format_usage = _star_signal_score(answer) if mode == "behavioral" else 0.0
    answer_length = len(answer.split())
    simulated_response_time_seconds = (
        round(float(response_time_seconds), 2) if isinstance(response_time_seconds, (int, float)) else round(max(5, answer_length // 3), 2)
    )
    drift_risk = _bounded_percentage((len(weak_topics) * 8.0) + (100.0 - clarity) * 0.25)

    return {
        "relevance_score": relevance,
        "correctness_score": correctness,
        "clarity_score": clarity,
        "depth_score": depth,
        "confidence_score": confidence_score,
        "technical_accuracy_pct": technical_accuracy_pct,
        "star_format_usage_pct": star_format_usage,
        "answer_length_words": answer_length,
        "response_time_seconds": simulated_response_time_seconds,
        "drift_risk_score": drift_risk,
    }


def compute_session_system_metrics(history: List[Dict[str, Any]]) -> Dict[str, float]:
    scored = [item for item in history if isinstance(item, dict) and isinstance(item.get("score"), int)]
    if not scored:
        return {"latency_ms_avg": 0.0, "consistency_score": 0.0, "drift_score": 0.0}

    latencies = [
        float(item.get("evaluation_latency_ms", 0.0))
        for item in scored
        if isinstance(item.get("evaluation_latency_ms"), (int, float))
    ]
    scores = [float(item["score"]) for item in scored]
    drift_risks = [
        float(item.get("drift_risk_score", 0.0))
        for item in scored
        if isinstance(item.get("drift_risk_score"), (int, float))
    ]

    score_std = pstdev(scores) if len(scores) > 1 else 0.0
    consistency_score = _bounded_percentage(max(0.0, 100.0 - (score_std * 12.0)))
    drift_score = _bounded_percentage(sum(drift_risks) / len(drift_risks)) if drift_risks else 0.0
    latency_ms_avg = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    return {
        "latency_ms_avg": latency_ms_avg,
        "consistency_score": consistency_score,
        "drift_score": drift_score,
    }


def generate_follow_up(
    question: str,
    answer: str,
    weak_topics: List[str],
    pressure_round: bool = False,
    score: int | None = None,
) -> str:
    low_score_rule = (
        "Score is below 5: generate a clarification follow-up on the same topic only; do not switch to a new topic."
        if isinstance(score, int) and score < 5
        else "Generate a natural follow-up; if possible, deepen the same topic before changing scope."
    )
    prompt = f"""
Generate one natural interviewer follow-up question based on the latest answer.
If pressure round is enabled, make it more challenging.
Target measurable impact, trade-offs, or clarity gaps.
{low_score_rule}

Return STRICT JSON only:
{{
  "follow_up_question": "..."
}}

Score: {score}
Pressure Round: {pressure_round}
Original Question: {question}
Candidate Answer: {answer}
Weak Topics: {json.dumps(weak_topics, ensure_ascii=False)}
""".strip()
    response = call_llm(prompt)
    parsed = _extract_json_object(response)
    return str(parsed.get("follow_up_question", "")).strip()


def build_debrief_actions(score: int, weak_topics: List[str]) -> Dict[str, Any]:
    prioritized = [topic for topic, _ in Counter(weak_topics).most_common(3)]
    while len(prioritized) < 3:
        fallback = ["quantification", "depth", "clarity"][len(prioritized)]
        if fallback not in prioritized:
            prioritized.append(fallback)

    actions = [
        f"Practice one answer focused on {prioritized[0]} and include a concrete metric.",
        f"Record and revise one answer focused on {prioritized[1]} using a clear STAR flow.",
        f"Run a timed drill targeting {prioritized[2]} in under 90 seconds with explicit outcomes.",
    ]
    next_target = (
        "Reach 8/10+ on the next answer with one metric, one trade-off, and a concise closing result."
        if score < 8
        else "Sustain 8/10+ while improving precision and adding clearer leadership signals."
    )
    return {"actions": actions, "target": next_target}


def build_curriculum_plan(weak_topic_memory: List[str], interview_date: str = "") -> List[str]:
    top_topics = [topic for topic, _ in Counter(weak_topic_memory).most_common(3)]
    if not top_topics:
        top_topics = ["quantification", "clarity", "trade-offs"]

    days = 7
    if interview_date:
        try:
            target = datetime.strptime(interview_date, "%Y-%m-%d").date()
            days_until = max(1, (target - date.today()).days)
            days = min(7, days_until)
        except ValueError:
            days = 7

    plan: List[str] = []
    for day_idx in range(days):
        topic = top_topics[day_idx % len(top_topics)]
        plan.append(f"Day {day_idx + 1}: 30-45 min focused drill on {topic} plus one timed mock answer.")
    return plan


def estimate_question_count(job_description: str, mode: str) -> int:
    text = job_description.lower()
    base = 6 if mode == "behavioral" else 7
    if any(keyword in text for keyword in ["senior", "staff", "lead", "principal", "architect"]):
        base += 2
    if any(keyword in text for keyword in ["intern", "junior", "entry-level", "graduate"]):
        base -= 1
    if len(job_description.split()) > 220:
        base += 1
    return max(4, min(10, base))


def summarize_final_evaluation(history: List[Dict[str, Any]], mode: str) -> str:
    scored_items = [item for item in history if isinstance(item.get("score"), int)]
    if not scored_items:
        return "No scored answers were completed."

    avg_score = sum(int(item["score"]) for item in scored_items) / len(scored_items)
    all_weak_topics: List[str] = []
    for item in scored_items:
        topics = item.get("weak_topics", [])
        if isinstance(topics, list):
            all_weak_topics.extend([str(topic).strip() for topic in topics if str(topic).strip()])
    top_topics = [topic for topic, _ in Counter(all_weak_topics).most_common(3)]
    strengths = "communication and structure" if avg_score >= 7 else "consistency and clarity growth potential"
    weak_summary = ", ".join(top_topics) if top_topics else "depth and quantification"

    return (
        f"Completed {len(scored_items)} {mode} questions with an average score of {avg_score:.1f}/10. "
        f"Current strengths include {strengths}. Primary improvement themes are {weak_summary}."
    )

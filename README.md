# Agentic Career Preparation Copilot

A local **agentic** career-prep app (Ollama-compatible) for end-to-end job preparation.

It works like a multi-stage workflow:

- **Career workspace tools**: JD keyword extraction, resume bullet tailoring, networking outreach drafts, follow-up reminders
- **Interviewer agent**: asks role-aware questions (technical/behavioral/system design/general)
- **Evaluator agent**: scores interview answers with structured metrics + feedback
- **Planner (policy + actions)**: chooses next difficulty/topic *and* intervention action
- **Action router**: executes plan actions (ask, lesson, drill, review, or end)
- **Memory + reflection**: persists weak/strong topics, missed-point logs, and turn reflections
- **Autonomous topic switching**: streak-based remediation when scores stay low on the same focus
- **Supervisor tool agent**: selects a tool call each turn (explainer, whiteboard drill, templates, mistake retrieval, best-answer compare)
- **Reflection loop**: diagnoses mistake patterns and updates preferred question style for the next batch
- **Jury evaluation**: strict vs clarity evaluators with a combined final score

## Quickstart (Windows + Ollama)

### 1) Install and start Ollama

- Install Ollama from [ollama.com](https://ollama.com)
- Pull a model (one-time):

```bash
ollama pull llama3
```

### 2) Setup Python env

From the project folder:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

### 3) Configure `.env`

Copy the example:

```bash
copy .env.example .env
```

Default settings are already Ollama-first:

- `OPENAI_BASE_URL=http://localhost:11434/v1`
- `OPENAI_API_KEY=ollama`
- `INTERVIEW_MODEL=llama3`
- `EVALUATOR_MODEL=llama3`

If you pulled a different model name, set `INTERVIEW_MODEL` / `EVALUATOR_MODEL` to match.

### 4) Run the Web Frontend (recommended)

```bash
streamlit run web_app.py
```

Then open the local URL shown in terminal (usually `http://localhost:8501`).
This repo includes `.streamlit/config.toml`, so no onboarding email prompt appears.

### 5) Run the CLI demo (optional)

```bash
python -m interview_helper.cli
```

Optional arguments:

```bash
python -m interview_helper.cli --role "Software Engineer" --topic "networking"
```

Commands during the session:

- `/quit` saves and exits
- `/reset` clears saved memory

## Running tests

```bash
pytest -q
```

## What makes it “agentic”

- **Multiple roles** (interviewer + evaluator + reflection + supervisor tool selector)
- **Explicit action policy** that selects from an action space (question/lesson/drill/review/end)
- **Planner decisions** for difficulty + next focus + intervention payload
- **Persistent memory + reflection** across turns to support adaptive behavior
- **Tool execution** across the hiring funnel (resume/networking/interview/follow-up)

## Repo layout

- `web_app.py`: Streamlit frontend for end-to-end career prep sessions
- `interview_helper/cli.py`: CLI loop for adaptive interview practice
- `interview_helper/agents.py`: interviewer/evaluator model calls
- `interview_helper/tools_runtime.py`: runtime tools for resume/networking/interview/follow-up
- `interview_helper/prompts.py`: system + user prompts for each agent
- `interview_helper/planner.py`: deterministic planning policy + memory updates
- `interview_helper/memory.py`: save/load session file
- `interview_helper/models.py`: Pydantic schemas (evaluation + session + plan)

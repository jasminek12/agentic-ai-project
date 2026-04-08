# Agentic Interview Helper (AI Interview Agent)

A small **agentic** interview-prep app that runs locally with **Ollama**.

It works like a loop:

- **Interviewer agent**: asks exactly one question (role + difficulty + topic)
- **Evaluator agent**: scores your answer with structured metrics + feedback
- **Planner (policy)**: updates next difficulty/topic based on the evaluation
- **Memory**: persists weak/strong topics across turns in a session file

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

- **Multiple roles** (interviewer + evaluator) instead of one blob prompt
- **Planner policy** that makes explicit decisions (difficulty + next focus)
- **Memory** that persists weak/strong topics across turns

## Repo layout

- `web_app.py`: Streamlit frontend for end-to-end interview sessions
- `interview_helper/cli.py`: CLI loop (ask → answer → evaluate → plan → persist)
- `interview_helper/agents.py`: interviewer/evaluator model calls
- `interview_helper/prompts.py`: system + user prompts for each agent
- `interview_helper/planner.py`: deterministic planning policy + memory updates
- `interview_helper/memory.py`: save/load session file
- `interview_helper/models.py`: Pydantic schemas (evaluation + session + plan)

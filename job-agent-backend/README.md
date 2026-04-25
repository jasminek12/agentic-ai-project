# Agentic Interview Helper — Backend (FastAPI + Groq)

> **Project overview:** see the repo root [README.md](../README.md).

**Agentic AI backend:** multiple **LLM agents** (resume, interview, outreach), **session memory** for adaptive interviews, and a **PDF toolchain**—see root README section *What makes this agentic AI?*

Backend MVP for:

- Resume tailoring and **PDF download** (`POST /tailor-resume`)
- Adaptive interview simulation (`behavioral` / `technical`) with **per-session memory** and explicit follow-up branching (`POST /start-interview`, `POST /submit-answer`, `POST /advance-interview`)
- **Professional outreach** drafts via Groq (`POST /frame-message`)

The React frontend in `job-agent-frontend/` calls these endpoints. The UI **falls back** to a local template if `/frame-message` fails (e.g. network or 502).

## Project Structure

```text
job-agent-backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── routes/
│   │   ├── resume_routes.py
│   │   ├── interview_routes.py
│   │   └── outreach_routes.py
│   ├── agents/
│   │   ├── resume_agent.py
│   │   ├── interview_agent.py
│   │   └── outreach_agent.py
│   └── utils/
│       ├── llm.py
│       ├── latex.py
│       └── memory.py
├── storage/
│   ├── memory.json
│   └── outputs/
├── requirements.txt
└── README.md
```

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set the Groq API key:

   ```bash
   set GROQ_API_KEY=your_groq_api_key
   ```

   PowerShell:

   ```powershell
   $env:GROQ_API_KEY="your_groq_api_key"
   ```

4. Ensure `pdflatex` is installed and on your `PATH` (required for resume PDF generation).

## Run Server

From the **`job-agent-backend`** directory (so `app` imports resolve):

```bash
cd job-agent-backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health checks:

- `GET /` — simple JSON status
- `GET /health` — JSON `{ "status": "ok" }`

API docs (when the server is running):

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## API Endpoints

### 1) `POST /tailor-resume`

Tailors the resume to the job description and returns a **PDF file** for download (not a JSON path).

**Request** (`application/json`):

```json
{
  "resume_text": "Software Engineer with backend API experience...",
  "job_description": "Need Python, FastAPI, Docker, and AWS skills..."
}
```

**Response**

- Status `200`
- Body: **binary PDF** (`Content-Disposition` / filename `tailored_resume.pdf` from the server)
- Errors: JSON `{ "error": "..." }` with `4xx` / `5xx` as applicable

The frontend typically uses `fetch` + `response.blob()` and triggers a browser download.

---

### 2) `POST /start-interview`

Starts (or resets) an interview for a given **`session_id`** and returns the first question plus run metadata.

**Request** (`application/json`):

```json
{
  "mode": "behavioral",
  "session_id": "user_123_session_1",
  "job_description": "Hiring backend engineer with FastAPI and PostgreSQL.",
  "resume": "Backend engineer with 3 years experience building APIs...",
  "panel_mode": true,
  "pressure_round": false,
  "company_context": "B2B fintech platform with strict SLA goals.",
  "role_context": "Backend Engineer II on platform reliability.",
  "interview_date": "2026-05-02"
}
```

- `mode` must be `"behavioral"` or `"technical"`.
- `session_id` is required: interview state is stored per session under `storage/` (see Notes).

**Response** (`application/json`):

```json
{
  "question": "Tell me about a time you handled a difficult stakeholder.",
  "interview_started": true,
  "target_question_count": 7
}
```

---

### 3) `POST /submit-answer`

Submits an answer for the **current open question** for the given `session_id`.
For in-progress sessions it returns score/feedback plus a **pending decision** between follow-up and next main question.
For completed sessions it returns final evaluation artifacts.

**Request** (`application/json`):

```json
{
  "session_id": "user_123_session_1",
  "answer": "I used a structured communication plan and weekly demos..."
}
```

**Response** (`application/json`):

```json
{
  "score": 7,
  "feedback": "Strong communication details; include measurable outcomes.",
  "next_question": "How would you optimize a slow API endpoint?",
  "follow_up_question": "Can you quantify the business impact of your communication changes?",
  "waiting_for_next_step": true,
  "interview_complete": false,
  "critique": "Clear structure, but impact details are light.",
  "rewrite": "In this project, I aligned weekly updates to stakeholder goals...",
  "debrief_actions": [],
  "next_round_target": "",
  "curriculum_plan": [],
  "weak_topic_memory": ["quantification", "depth"],
  "final_evaluation": ""
}
```

On completion, `interview_complete` becomes `true` and final fields are populated (`final_evaluation`, `debrief_actions`, `next_round_target`, `curriculum_plan`).

You must call `/start-interview` for that `session_id` before `/submit-answer`.

---

### 4) `POST /advance-interview`

Commits the candidate's branch choice after `/submit-answer` returns `waiting_for_next_step=true`.

**Request** (`application/json`):

```json
{
  "session_id": "user_123_session_1",
  "choice": "follow_up"
}
```

`choice` must be `"follow_up"` or `"next_question"`.

**Response** (`application/json`):

```json
{
  "question": "Can you quantify the business impact of your communication changes?"
}
```

---

### 5) `POST /frame-message`

Generates a recruiter- or hiring-manager-ready message (email or LinkedIn style) using the **Groq** LLM.

**Request** (`application/json`):

```json
{
  "message_type": "follow_up",
  "channel": "email",
  "tone": "professional",
  "sender_name": "Alex Rivera",
  "recipient_name": "Jordan",
  "company": "Acme Corp",
  "role": "Backend engineer",
  "notes": "Mutual connection with Sam."
}
```

- `message_type`: `follow_up` | `thank_you` | `cold` | `connection` | `schedule`
- `channel`: `email` | `linkedin`
- `tone`: `professional` | `warm` | `concise`
- At least one of `role`, `company`, `recipient_name`, or `notes` must be non-empty.

**Response** (`application/json`):

```json
{
  "message": "Hello Jordan,\n\n...",
  "confidence": "high",
  "rationale": "Matches stated role and company context."
}
```

---

## CORS

`app/main.py` enables permissive CORS (`allow_origins=["*"]`) for local development. **Tighten `allow_origins` in production** to your deployed frontend origin(s).

## Notes

- Mode is chosen by the client (`behavioral` or `technical`), not inferred by the LLM alone.
- Interview history is persisted per `session_id` (see `app/utils/memory.py` and files under `storage/`).
- Generated PDFs are written under `storage/outputs/` during tailoring.
- `/frame-message` does not persist state; each call is independent.

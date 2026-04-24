# Job Agent Backend (FastAPI + Groq)

Backend MVP for:
- Resume tailoring and PDF generation
- Adaptive interview simulation (`behavioral` / `technical`)

## Project Structure

```text
job-agent-backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── routes/
│   │   ├── resume_routes.py
│   │   └── interview_routes.py
│   ├── agents/
│   │   ├── resume_agent.py
│   │   └── interview_agent.py
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

1. Create and activate Python virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variable:
   ```bash
   set GROQ_API_KEY=your_groq_api_key
   ```
   On PowerShell:
   ```powershell
   $env:GROQ_API_KEY="your_groq_api_key"
   ```
4. Ensure `pdflatex` is installed and available in PATH.

## Run Server

```bash
uvicorn app.main:app --reload
```

API docs:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## API Endpoints

### 1) POST `/tailor-resume`

Request:
```json
{
  "resume_text": "Software Engineer with backend API experience...",
  "job_description": "Need Python, FastAPI, Docker, and AWS skills..."
}
```

Response:
```json
{
  "pdf_path": "storage/outputs/resume_20260421_224500.pdf"
}
```

### 2) POST `/start-interview`

Request:
```json
{
  "mode": "behavioral",
  "job_description": "Hiring backend engineer with FastAPI and PostgreSQL.",
  "resume": "Backend engineer with 3 years experience building APIs..."
}
```

Response:
```json
{
  "question": "Tell me about a time you handled a difficult stakeholder."
}
```

### 3) POST `/submit-answer`

Request:
```json
{
  "answer": "I used a structured communication plan and weekly demos..."
}
```

Response:
```json
{
  "score": 7,
  "feedback": "Strong communication details; include measurable outcomes.",
  "next_question": "How would you optimize a slow API endpoint?"
}
```

## Notes

- Mode selection is controlled by user input (`behavioral` or `technical`), not by the LLM.
- Interview history is persisted in `storage/memory.json`.
- Generated PDFs are stored under `storage/outputs/`.

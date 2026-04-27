# Agentic Interview Helper — Frontend

> **Project overview:** see the repo root [README.md](../README.md).

**Agentic AI UI:** React + Vite SPA for the FastAPI backend — tabs for resume tailoring, adaptive interview simulation, and professional outreach, plus workflow/status UX that surfaces what the agent is doing.

## Features

- Welcome/account flow (local account + workspace draft persistence)
- Resume tailoring UI: `POST /tailor-resume` returns structured output (summary/experience/skills) for copy-paste
- Interview simulator:
  - adaptive branch mode (`/start-interview`, `/submit-answer`, `/advance-interview`)
  - panel simulation mode with auto progression and persona-driven active speaker
  - pause/resume session UX + session transcript sidebar
- Interview session lifecycle integration (`GET/DELETE /interview-sessions...`)
- Professional outreach:
  - `POST /frame-message` with fallback template generation in browser
  - purpose/channel/tone dropdowns with placeholder defaults
  - custom purpose via "Other..."
- Rewrite audio controls (play, pause, restart, seek bar)

## Prerequisites

- Node.js 18+
- Running backend server at `http://127.0.0.1:8000` (or configure a custom URL)

## Setup

```bash
npm install
```

Create a `.env` file in this folder (optional, defaults already point to localhost backend):

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Run

```bash
npm run dev
```

Open the URL printed by Vite (usually `http://localhost:5173`).

## Build

```bash
npm run build
npm run preview
```

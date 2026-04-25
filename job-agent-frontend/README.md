# Agentic Interview Helper — Frontend

> **Project overview:** see the repo root [README.md](../README.md).

**Agentic AI UI:** React + Vite SPA for the FastAPI backend—tabs for resume, adaptive interview, and outreach, plus a **goal/workflow-style dashboard** that surfaces agent progress alongside API results (`job-agent-backend`). Product name: **Agentic Interview Helper**.

## Features

- Welcome screen (collects name; stored in `localStorage`)
- Resume tailoring UI: `POST /tailor-resume` — expects a **PDF** response and starts a download
- Interview simulator: `POST /start-interview` and `POST /submit-answer` (both require **`session_id`**)
- Professional outreach tab: calls **`POST /frame-message`**; falls back to a **local template** if the API errors
- Agent-style dashboard (progress, insights, goals, etc.) — mostly UI logic; core data still comes from the backend routes above

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

Open the URL printed by Vite (usually `http://127.0.0.1:5173`).

## Build

```bash
npm run build
npm run preview
```

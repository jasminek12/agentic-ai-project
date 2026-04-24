# Job Agent Frontend

React + Vite frontend for the FastAPI backend in `job-agent-backend`.

## Features

- Resume tailoring UI (posts to `/tailor-resume` and downloads generated PDF)
- Interview simulator UI:
  - Start session (`/start-interview`)
  - Submit answer and receive score/feedback/next question (`/submit-answer`)

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

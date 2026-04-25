from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes.interview_routes import router as interview_router
from app.routes.outreach_routes import router as outreach_router
from app.routes.resume_routes import router as resume_router


app = FastAPI(
    title="Agentic Interview Helper — API",
    description="Agentic Interview Helper API: resume PDF tailoring, adaptive interview (session memory), and LLM outreach. Setup: repository root README.md.",
    version="1.0.0",
)

# CORS middleware for frontend integration.
# Update allow_origins in production to a strict list of trusted frontend domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume_router)
app.include_router(interview_router)
app.include_router(outreach_router)


@app.exception_handler(HTTPException)
def http_exception_handler(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail["error"]})
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


@app.exception_handler(Exception)
def unhandled_exception_handler(_: Request, exc: Exception):
    print(f"[DEBUG] Unhandled server error: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.get("/")
def healthcheck():
    return {"status": "ok", "message": "Agentic Interview Helper backend is running."}


@app.get("/health")
def health():
    return {"status": "ok"}

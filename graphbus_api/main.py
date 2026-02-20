"""
GraphBus API Server

Wraps the GraphBus build + runtime pipeline as a REST API,
powered by the Anthropic agent SDK backend.

Usage:
    python3 -m graphbus_api.main
    # or
    uvicorn graphbus_api.main:app --host 0.0.0.0 --port 8080 --reload
"""

import os
import sys

# Ensure graphbus_core is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graphbus_api.auth import init_api_key
from graphbus_api.routes.build import router as build_router
from graphbus_api.routes.run import router as run_router
from graphbus_api.routes.negotiations import router as negotiations_router

app = FastAPI(
    title="GraphBus API",
    description=(
        "REST API for the GraphBus multi-agent orchestration framework.\n\n"
        "**Build mode** — scan agent modules, run LLM negotiation (via Anthropic SDK), emit artifacts.\n\n"
        "**Runtime mode** — load artifacts, call methods, publish events on the message bus."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth init ────────────────────────────────────────────────────────────────

init_api_key()

# ── Routers ──────────────────────────────────────────────────────────────────

app.include_router(build_router, prefix="/api")
app.include_router(run_router, prefix="/api")
app.include_router(negotiations_router, prefix="/api")


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
def health():
    """Liveness check."""
    return {"status": "ok", "service": "graphbus-api"}


@app.get("/", tags=["meta"])
def root():
    """API info."""
    return {
        "service": "GraphBus API",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "build": {
                "start":  "POST /api/build",
                "status": "GET  /api/build/{job_id}",
                "list":   "GET  /api/build",
            },
            "run": {
                "start":   "POST   /api/run",
                "call":    "POST   /api/run/{session_id}/call",
                "publish": "POST   /api/run/{session_id}/publish",
                "stats":   "GET    /api/run/{session_id}/stats",
                "info":    "GET    /api/run/{session_id}",
                "stop":    "DELETE /api/run/{session_id}",
            },
            "negotiations": {
                "create":    "POST   /api/negotiations",
                "list":      "GET    /api/negotiations",
                "get":       "GET    /api/negotiations/{session_id}",
                "update":    "PATCH  /api/negotiations/{session_id}",
                "proposals": "POST   /api/negotiations/{session_id}/proposals",
                "commits":   "POST   /api/negotiations/{session_id}/commits",
                "feedback":  "POST   /api/negotiations/{session_id}/feedback",
            },
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "graphbus_api.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info",
    )

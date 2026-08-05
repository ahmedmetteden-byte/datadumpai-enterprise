"""
DataDumpAI product API (workspaces, knowledge, indexing).

Run:
    uvicorn api.app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import home, intelligence, knowledge, me, reports, workspaces

app = FastAPI(title="DataDumpAI Product API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(home.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
app.include_router(workspaces.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(intelligence.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health")
def api_health() -> dict[str, str]:
    return {"status": "ok"}

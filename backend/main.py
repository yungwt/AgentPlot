"""FastAPI entry point for the AgentPlot backend.

Run:
    uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.settings import OUTPUT_DIR
from backend.core.config import CORS_ORIGINS
from backend.api import sessions as sessions_api
from backend.api import steps as steps_api

app = FastAPI(title="AgentPlot API", version="0.1.0")

# Ensure the output directory exists so StaticFiles can mount it on first run.
os.makedirs(OUTPUT_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated images / artifacts under /static/output/<session_id>/...
app.mount("/static/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

app.include_router(sessions_api.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(steps_api.router, prefix="/api/sessions", tags=["steps"])


@app.get("/")
def root():
    return {"name": "AgentPlot API", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}

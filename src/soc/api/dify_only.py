"""Minimal, retrieval-only FastAPI app for a temporary Dify integration demo.

Unlike soc.api.main, this application deliberately does not expose alerts,
approvals, reports, triage, stats, or administrative APIs.
"""
from fastapi import FastAPI

from .dify import router

app = FastAPI(
    title="SOC External Knowledge API",
    version="1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}

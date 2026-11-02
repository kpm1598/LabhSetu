"""LabhSetu - FastAPI application entry point.

Run from the backend folder:
    uvicorn app.main:app --reload
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup / shutdown.

    On startup the database is initialized (tables and indexes are
    created only if missing; existing records are never touched).
    If initialization fails, the error is logged and the API still
    starts, so / and /health keep working and the failure stays visible
    through GET /api/database/status instead of a silent crash loop.
    """
    try:
        database.initialize_database()
    except database.DatabaseError as exc:
        logger.error("Database initialization failed: %s", exc)
    yield


app = FastAPI(title="LabhSetu", version="0.1.0", lifespan=lifespan)


@app.get("/")
def root():
    """Root endpoint - confirms the API is running."""
    return {"message": "Welcome to LabhSetu", "status": "running"}


@app.get("/health")
def health_check():
    """Health-check endpoint - used to verify the backend is alive."""
    return {"status": "ok"}


@app.get("/api/database/status")
def database_status():
    """Report whether the database is initialized and its tables exist."""
    return database.get_database_status()


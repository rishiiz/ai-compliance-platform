"""FastAPI application entry point."""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from pymongo.errors import PyMongoError
from mongoengine.connection import get_connection

try:
    from openai import APIError as OpenAIAPIError
except ImportError:
    OpenAIAPIError = None  # openai package may use different export path

from app.config import settings
from app.database import init_db
from app.scheduler import get_scheduler
from app.services.external_db import get_external_engine
from app.utils.logging_config import setup_logging
from app.routes import (
    audit as audit_routes,
    auth_routes,
    dashboard as dashboard_routes,
    database as database_routes,
    files as files_routes,
    metrics_routes,
    notifications as notifications_routes,
    policy as policy_routes,
    profile_routes,
    reports_routes,
    rules as rules_routes,
    scan as scan_routes,
    settings_routes,
    violations as violations_routes,
    users_routes,
)
from app.scheduler import start_scheduler, stop_scheduler
from app.services.rule_extractor import RuleExtractionError

logger = logging.getLogger(__name__)


def _error_response(
    status_code: int,
    error_type: str,
    message: str,
    detail: str | None = None,
) -> dict:
    """Build a structured JSON error payload."""
    body = {
        "error": {
            "type": error_type,
            "message": message,
        },
        "status_code": status_code,
    }
    if detail is not None:
        body["error"]["detail"] = detail
    return body


async def database_exception_handler(request: Request, exc: PyMongoError) -> JSONResponse:
    """Handle database errors. Log and return structured JSON."""
    logger.exception("Database error: %s", exc)
    return JSONResponse(
        status_code=503,
        content=_error_response(
            status_code=503,
            error_type="database_error",
            message="A database error occurred.",
            detail=str(exc) if settings.DEBUG else None,
        ),
    )


async def openai_exception_handler(request: Request, exc: OpenAIAPIError) -> JSONResponse:
    """Handle OpenAI API errors. Log and return structured JSON."""
    logger.exception("OpenAI API error: %s", exc)
    status_code = getattr(exc, "status_code", None) or 502
    if status_code >= 500:
        status_code = 502
    elif status_code >= 400:
        status_code = min(status_code, 422)
    return JSONResponse(
        status_code=status_code,
        content=_error_response(
            status_code=status_code,
            error_type="openai_api_error",
            message="An error occurred while calling the OpenAI API.",
            detail=str(exc),
        ),
    )


async def rule_extraction_exception_handler(
    request: Request, exc: RuleExtractionError
) -> JSONResponse:
    """Handle rule extraction (OpenAI/parsing) errors. Log and return structured JSON."""
    logger.warning("Rule extraction error: %s", exc)
    return JSONResponse(
        status_code=422,
        content=_error_response(
            status_code=422,
            error_type="rule_extraction_error",
            message="Rule extraction failed.",
            detail=str(exc),
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exception. Log and return structured JSON."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=_error_response(
            status_code=500,
            error_type="internal_server_error",
            message="An unexpected error occurred.",
            detail=str(exc) if settings.DEBUG else None,
        ),
    )


def _warmup_rag_background() -> None:
    """Pre-warm RAG embedding model in background so first upload/reindex is fast."""
    try:
        from app.services.rag_service import warmup_rag
        warmup_rag()
    except Exception as e:
        logger.warning("RAG warmup failed (non-fatal): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start scheduler on startup, stop on shutdown. Pre-warm RAG in background."""
    setup_logging(level=logging.DEBUG if settings.DEBUG else logging.INFO)
    init_db()
    start_scheduler()
    # Pre-warm RAG so first upload/index is fast (runs in background, does not block startup)
    threading.Thread(target=_warmup_rag_background, daemon=True).start()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI compliance monitoring platform API",
    lifespan=lifespan,
)

# Allow frontend (Next.js dev on port 3000) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handlers: structured JSON + logging
app.add_exception_handler(PyMongoError, database_exception_handler)
if OpenAIAPIError is not None:
    app.add_exception_handler(OpenAIAPIError, openai_exception_handler)
app.add_exception_handler(RuleExtractionError, rule_extraction_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(audit_routes.router)
app.include_router(auth_routes.router)
app.include_router(policy_routes.router)
app.include_router(rules_routes.router)
app.include_router(database_routes.router)
app.include_router(files_routes.router)
app.include_router(scan_routes.router)
app.include_router(violations_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(notifications_routes.router)
app.include_router(settings_routes.router)
app.include_router(reports_routes.router)
app.include_router(profile_routes.router)
app.include_router(users_routes.router)
app.include_router(metrics_routes.router)


def _check_main_database() -> dict:
    """Check main MongoDB connection. Returns {status, message}."""
    try:
        conn = get_connection()
        conn.admin.command('ping')
        return {"status": "ok", "message": "Connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _check_external_database() -> dict:
    """Check external DB connection if configured. Returns {status, message}."""
    engine = get_external_engine()
    if engine is None:
        return {"status": "unconfigured", "message": "No external database configured"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _check_openai_api_key() -> dict:
    """Check OpenAI API key presence (optional when using Groq-only). Returns {status, message}."""
    key = getattr(settings, "OPENAI_API_KEY", None)
    if key and str(key).strip() and "your_openai_key_here" not in str(key).lower():
        return {"status": "ok", "message": "API key present"}
    return {"status": "missing", "message": "OpenAI key not set (use Groq + local embeddings for no OpenAI)"}


def _check_groq_api_key() -> dict:
    """Check Groq API key presence (used for LLM: Ask policy, rule extraction). Returns {status, message}."""
    key = getattr(settings, "GROQ_API_KEY", None)
    if key and str(key).strip() and "your_groq_key_here" not in str(key).lower():
        return {"status": "ok", "message": "API key present"}
    return {"status": "missing", "message": "GROQ_API_KEY not set (required for Groq + Llama)"}


def _check_scheduler() -> dict:
    """Check scheduler is running. Returns {status, message}."""
    scheduler = get_scheduler()
    if scheduler is None:
        return {"status": "not_running", "message": "Scheduler not started"}
    if getattr(scheduler, "running", False):
        return {"status": "ok", "message": "Scheduler running"}
    return {"status": "not_running", "message": "Scheduler not running"}


@app.get("/health")
def health_check() -> Response:
    """
    Health check endpoint.
    Checks: main MongoDB, external DB (if configured), Groq API key, OpenAI (optional), scheduler.
    Groq-only: GROQ_API_KEY required for LLM; RAG uses local embeddings (no OpenAI).
    HTTP 200 for ok/degraded, 503 for unhealthy.
    """
    checks = {
        "database": _check_main_database(),
        "external_database": _check_external_database(),
        "groq_api_key": _check_groq_api_key(),
        "openai_api_key": _check_openai_api_key(),
        "scheduler": _check_scheduler(),
    }
    critical_ok = (
        checks["database"]["status"] == "ok"
        and checks["scheduler"]["status"] == "ok"
    )
    external = checks["external_database"]["status"]
    groq_ok = checks["groq_api_key"]["status"] == "ok"
    openai_ok = checks["openai_api_key"]["status"] == "ok"
    llm_ok = groq_ok or openai_ok  # At least one LLM (Groq or OpenAI)
    if not critical_ok:
        overall = "unhealthy"
    elif external == "error" or not llm_ok:
        overall = "degraded"
    else:
        overall = "ok"
    payload = {"status": overall, "checks": checks}
    status_code = 503 if overall == "unhealthy" else 200
    return JSONResponse(content=payload, status_code=status_code)

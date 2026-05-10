"""Database connection API routes."""

import logging

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.models.app_settings import AppSettings
from app.services.external_db import create_external_engine_from_credentials, get_external_engine
from app.services.company_policy_search import get_company_policy_summary

router = APIRouter(prefix="/database", tags=["database"])
logger = logging.getLogger(__name__)

DEFAULT_PORTS = {"postgresql": 5432, "mysql": 3306}
_KEYS = ("external_db_host", "external_db_port", "external_db_user", "external_db_name", "external_db_dialect")


def _save_connection_settings(
    host: str, port: int, user: str, db_name: str, dialect: str = "postgresql"
) -> None:
    """Persist connection details (not password) so the UI can pre-fill and show status."""
    for key, value in [
        ("external_db_host", host),
        ("external_db_port", str(port)),
        ("external_db_user", user),
        ("external_db_name", db_name),
        ("external_db_dialect", dialect),
    ]:
        row = AppSettings.objects(key=key).first()
        if row:
            row.value = value
            row.save()
        else:
            AppSettings(key=key, value=value).save()


def _get_connection_settings() -> dict:
    """Return saved host, port, user, db_name from AppSettings."""
    rows = AppSettings.objects(key__in=_KEYS)
    return {r.key: r.value for r in rows}


@router.get("/status")
def database_status() -> dict:
    """
    Return whether the external database is currently connected and last-used connection details.
    Used to pre-fill the connection form and show "Connected to host / db_name" after page reload.
    """
    engine = get_external_engine()
    saved = _get_connection_settings()
    return {
        "connected": engine is not None,
        "host": saved.get("external_db_host"),
        "db_name": saved.get("external_db_name"),
        "username": saved.get("external_db_user"),
        "port": saved.get("external_db_port"),
        "dialect": saved.get("external_db_dialect") or "postgresql",
    }


class DatabaseConnectRequest(BaseModel):
    """Request body for POST /database/connect. Connect to any DB via credentials."""

    host: str
    username: str
    password: str
    db_name: str
    port: int | None = None  # default by dialect: 5432 postgresql, 3306 mysql
    dialect: str = "postgresql"  # "postgresql" | "mysql"


@router.post("/connect")
def database_connect(body: DatabaseConnectRequest) -> dict:
    """
    Connect to an external database using the provided credentials.
    Supports PostgreSQL and MySQL (and any dialect supported by SQLAlchemy).
    Stores the engine in memory and saves host/port/username/db_name/dialect (not password) for status.
    """
    dialect = (body.dialect or "postgresql").strip().lower()
    if dialect not in ("postgresql", "mysql"):
        dialect = "postgresql"
    port = body.port if body.port is not None else DEFAULT_PORTS.get(dialect, 5432)
    driver = "pymysql" if dialect == "mysql" else "psycopg2"
    try:
        create_external_engine_from_credentials(
            host=body.host,
            port=port,
            user=body.username,
            password=body.password,
            database=body.db_name,
            dialect=dialect,
            driver=driver,
        )
    except Exception as e:
        logger.error(
            "Database connection failed | host=%s | db_name=%s | dialect=%s | error=%s",
            body.host,
            body.db_name,
            dialect,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=422,
            detail=f"Failed to connect to database: {e}",
        ) from e
    _save_connection_settings(body.host, port, body.username, body.db_name, dialect)
    logger.info(
        "Database connected | host=%s | db_name=%s | user=%s | dialect=%s",
        body.host,
        body.db_name,
        body.username,
        dialect,
    )
    return {"message": "Connected successfully"}


@router.get("/company-data")
def database_company_data() -> dict:
    """
    Return connection status (username, host, db_name) and fetched data from the company
    database (policy_documents count and list). Used by the dashboard after connect.
    """
    saved = _get_connection_settings()
    engine = get_external_engine()
    connected = engine is not None
    out = {
        "connected": connected,
        "host": saved.get("external_db_host"),
        "db_name": saved.get("external_db_name"),
        "username": saved.get("external_db_user"),
        "port": saved.get("external_db_port"),
        "dialect": saved.get("external_db_dialect") or "postgresql",
    }
    if connected:
        summary = get_company_policy_summary(limit=20)
        out["count"] = summary.get("count", 0)
        out["documents"] = summary.get("documents", [])
        if summary.get("error"):
            out["data_error"] = summary["error"]
    return out

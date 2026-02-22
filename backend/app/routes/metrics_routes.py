"""Metrics API: RAG Ask aggregates for development/optimization."""

from fastapi import APIRouter, Depends

from app.routes.auth_routes import get_current_user
from app.models import User
from app.services.rag_metrics import get_aggregates, get_recent

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/rag")
def get_rag_metrics(
    current_user: User = Depends(get_current_user),
    recent: bool = False,
) -> dict:
    """
    Return RAG Ask metrics: aggregates (count, avg/p95 latency, avg tokens) or recent entries.
    Query param recent=true returns last N raw entries; otherwise returns aggregates.
    """
    if recent:
        return {"recent": get_recent()}
    return get_aggregates()

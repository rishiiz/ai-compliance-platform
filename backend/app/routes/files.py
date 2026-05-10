"""Serve policy files stored in the app database (when not using Supabase Storage)."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.models.policy_file_storage import PolicyFileStorage

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/download/{file_id}", response_class=Response)
def download_file(file_id: str) -> Response:
    """
    Download a policy file stored in the app database (MongoDB).
    Used when storage is not Supabase; frontend can use {API_URL}/files/download/{id}.
    """
    row = PolicyFileStorage.objects(id=file_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    return Response(
        content=bytes(row.data),
        media_type=row.content_type,
        headers={
            "Content-Disposition": f'inline; filename="{row.storage_path.split("/")[-1]}"',
        },
    )

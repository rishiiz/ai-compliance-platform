"""User management (admin)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.utils.password import hash_password

router = APIRouter(prefix="/users", tags=["users"])


def _user_to_item(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "department": u.department or "",
        "two_fa_enabled": u.two_fa_enabled,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("")
def list_users(db: Session = Depends(get_db)) -> list:
    """List all users (admin)."""
    users = db.query(User).order_by(User.email).all()
    return [_user_to_item(u) for u in users]


class CreateUserRequest(BaseModel):
    email: str
    name: str
    role: str = "Viewer"
    department: str | None = None
    password: str | None = None


@router.post("")
def create_user(body: CreateUserRequest, db: Session = Depends(get_db)) -> dict:
    """Add a user (admin). Optional password sets their login password."""
    existing = db.query(User).filter(User.email == body.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    role = body.role.strip() if body.role else "Viewer"
    if role not in ("Admin", "Compliance Officer", "Viewer"):
        role = "Viewer"
    password_hash = hash_password(body.password) if body.password and body.password.strip() else None
    user = User(
        email=body.email.strip().lower(),
        name=body.name.strip() or body.email.split("@")[0],
        role=role,
        department=body.department.strip() if body.department else None,
        password_hash=password_hash,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_to_item(user)


class SetPasswordRequest(BaseModel):
    password: str


@router.patch("/{user_id}/password")
def set_user_password(user_id: int, body: SetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    """Set or reset a user's login password (admin)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not body.password or not body.password.strip():
        raise HTTPException(status_code=400, detail="Password required")
    user.password_hash = hash_password(body.password.strip())
    db.commit()
    db.refresh(user)
    return _user_to_item(user)


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)) -> dict:
    """Delete a user (admin only). Cannot delete the last Admin."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "Admin":
        admin_count = db.query(User).filter(User.role == "Admin").count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the last admin. Add another admin first.",
            )
    db.delete(user)
    db.commit()
    return {"ok": True, "id": user_id}

"""User model for auth, profile, 2FA, and user management."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """Users for login, profile, and 2FA."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(64), nullable=False)  # Admin, Compliance Officer, Viewer
    department = Column(String(128), nullable=True)
    password_hash = Column(String(255), nullable=True)  # optional for demo
    two_fa_secret = Column(String(64), nullable=True)
    two_fa_enabled = Column(Boolean, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

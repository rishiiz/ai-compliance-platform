"""Database connection and session management."""

import os
from mongoengine import connect, disconnect

from app.config import settings

def init_db() -> None:
    """Initialize MongoDB connection and seed default data if needed."""
    # Disconnect if already connected (useful for testing or hot-reloading)
    disconnect()
    
    # Extract DB name from the URI if possible, or default to compliance_db
    # e.g., mongodb://localhost:27017/compliance_db
    db_uri = settings.DATABASE_URL
    if not db_uri.startswith("mongodb"):
        # Fallback for when the .env still has a postgres URL but we're starting up
        # In a real environment, they MUST update their .env
        db_uri = "mongodb://localhost:27017/compliance_db"
        
    connect(host=db_uri)
    
    _seed_default_admin()
    _seed_notifications()


def get_db():
    """
    Dependency that yields a dummy session.
    With mongoengine, we use a global connection, so this is kept for compatibility
    temporarily during migration or just returns None.
    """
    try:
        yield None
    finally:
        pass


def _seed_default_admin() -> None:
    """Ensure default admin user exists: admin@company.com / Admin@123."""
    from app.models.user import User
    from app.utils.password import hash_password

    existing = User.objects(email="admin@company.com").first()
    if existing:
        if not existing.password_hash:
            existing.password_hash = hash_password("Admin@123")
            existing.save()
        return

    admin = User(
        email="admin@company.com",
        name="Admin User",
        role="Admin",
        department="IT",
        password_hash=hash_password("Admin@123"),
    )
    admin.save()


def _seed_notifications() -> None:
    """Create a welcome notification if none exist."""
    from app.models.notification import Notification

    if Notification.objects().first() is not None:
        return

    Notification(
        type="info",
        title="Welcome",
        body="Connect policies and run scans to see violations and compliance metrics here.",
        read=False,
    ).save()

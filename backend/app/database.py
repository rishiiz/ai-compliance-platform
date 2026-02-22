"""Database connection and session management."""

import re

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _ensure_postgres_database() -> None:
    """
    If DATABASE_URL is PostgreSQL, create the database if it does not exist.
    Connects to the default 'postgres' db to run CREATE DATABASE.
    """
    url = settings.DATABASE_URL
    if "postgresql" not in url or "sqlite" in url:
        return
    # Parse database name from URL (e.g. postgresql://user:pass@host:port/dbname)
    match = re.search(r"/([^/?]+)(?:\?|$)", url)
    if not match:
        return
    db_name = match.group(1).strip()
    if not db_name or db_name in ("postgres", "template0", "template1"):
        return
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", db_name):
        return  # refuse to create non-identifier names
    # Build URL to default 'postgres' database (same host/user/pass)
    base_url = re.sub(r"/[^/?]+(?:\?.*)?$", "/postgres", url)
    admin_engine = create_engine(
        base_url,
        isolation_level="AUTOCOMMIT",
    )
    with admin_engine.connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        ).fetchone()
        if not row:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()


def _ensure_mysql_database() -> None:
    """
    If DATABASE_URL is MySQL, create the database if it does not exist.
    """
    url = settings.DATABASE_URL
    if "mysql" not in url:
        return
    # Parse database name from URL (e.g. mysql+pymysql://user:pass@host:port/dbname)
    match = re.search(r"/([^/?]+)(?:\?|$)", url)
    if not match:
        return
    db_name = match.group(1).strip()
    if not db_name:
        return
    # Build URL without database name to connect to server
    base_url = re.sub(r"/[^/?]+(?:\?.*)?$", "/", url)
    admin_engine = create_engine(base_url)
    with admin_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}`"))
    admin_engine.dispose()


def get_db():
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create the database if missing (PostgreSQL or MySQL), then create all tables. Seed default admin if none."""
    _ensure_postgres_database()
    _ensure_mysql_database()
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _add_violation_suggested_remediation_column()
    _add_policy_extracted_text_column()
    _seed_default_admin()
    _seed_notifications()


def _add_violation_suggested_remediation_column() -> None:
    """Add suggested_remediation column to violations if it does not exist."""
    dialect_name = engine.dialect.name
    with engine.connect() as conn:
        try:
            if dialect_name == "postgresql":
                conn.execute(text("ALTER TABLE violations ADD COLUMN IF NOT EXISTS suggested_remediation TEXT"))
            else:
                # For MySQL/SQLite, we try to add and ignore if it already exists
                try:
                    conn.execute(text("ALTER TABLE violations ADD COLUMN suggested_remediation TEXT"))
                except Exception as e:
                    if "Duplicate column" in str(e) or "already exists" in str(e):
                        pass
                    else:
                        raise e
            conn.commit()
        except Exception:
            conn.rollback()


def _add_policy_extracted_text_column() -> None:
    """Add extracted_text column to policies if it does not exist."""
    dialect_name = engine.dialect.name
    with engine.connect() as conn:
        try:
            if dialect_name == "postgresql":
                conn.execute(text("ALTER TABLE policies ADD COLUMN IF NOT EXISTS extracted_text TEXT"))
            else:
                # For MySQL/SQLite, we try to add and ignore if it already exists
                try:
                    conn.execute(text("ALTER TABLE policies ADD COLUMN extracted_text TEXT"))
                except Exception as e:
                    if "Duplicate column" in str(e) or "already exists" in str(e):
                        pass
                    else:
                        raise e
            conn.commit()
        except Exception:
            conn.rollback()


def _seed_default_admin() -> None:
    """Ensure default admin user exists: admin@company.com / Admin@123."""
    from app.models import User
    from app.utils.password import hash_password

    session = SessionLocal()
    try:
        existing = session.query(User).filter(User.email == "admin@company.com").first()
        if existing:
            if not existing.password_hash:
                existing.password_hash = hash_password("Admin@123")
                session.commit()
            return
        admin = User(
            email="admin@company.com",
            name="Admin User",
            role="Admin",
            department="IT",
            password_hash=hash_password("Admin@123"),
        )
        session.add(admin)
        session.commit()
    finally:
        session.close()


def _seed_notifications() -> None:
    """Create a welcome notification if none exist."""
    from app.models import Notification

    session = SessionLocal()
    try:
        if session.query(Notification).first() is not None:
            return
        session.add(
            Notification(
                type="info",
                title="Welcome",
                body="Connect policies and run scans to see violations and compliance metrics here.",
                read=False,
            )
        )
        session.commit()
    finally:
        session.close()

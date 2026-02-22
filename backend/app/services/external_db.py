"""External database connection with dynamic engine from credentials."""

from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_external_engine: Optional[Engine] = None


def create_external_engine_from_credentials(
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
    dialect: str = "postgresql",
    driver: str = "",
) -> Engine:
    """
    Build a connection URL from credentials, create the engine, and store it in memory.

    Args:
        host: Database host.
        port: Database port.
        user: Username.
        password: Password.
        database: Database name.
        dialect: Dialect name (e.g. postgresql, mysql).
        driver: Optional driver (e.g. psycopg2 for postgresql).

    Returns:
        The created and stored engine.
    """
    driver_part = f"+{driver}" if driver else ""
    url = (
        f"{dialect}{driver_part}://{user}:{password}@{host}:{port}/{database}"
    )
    return create_external_engine(url)


def create_external_engine(
    connection_url: str,
    *,
    connect_args: Optional[dict] = None,
) -> Engine:
    """
    Create a SQLAlchemy engine from the given connection URL and store it in memory.

    Args:
        connection_url: Full database URL (e.g. postgresql://user:pass@host:5432/db).
        connect_args: Optional extra arguments passed to the driver (e.g. for SQLite:
            {"check_same_thread": False}).

    Returns:
        The created and stored engine.
    """
    global _external_engine
    kwargs = {}
    if connect_args is not None:
        kwargs["connect_args"] = connect_args
    elif "sqlite" in connection_url:
        kwargs["connect_args"] = {"check_same_thread": False}
    _external_engine = create_engine(connection_url, **kwargs)
    return _external_engine


def get_external_engine() -> Optional[Engine]:
    """
    Return the externally configured engine stored in memory.

    Returns:
        The engine previously set via create_external_engine(), or None if none was set.
    """
    return _external_engine

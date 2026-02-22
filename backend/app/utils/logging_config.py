"""Structured logging configuration using Python logging module."""

import logging
import sys


def setup_logging(
    level: int | str = logging.INFO,
    format_string: str | None = None,
) -> None:
    """
    Configure root logger and app loggers with a consistent format.
    Call once at application startup (e.g. in lifespan).
    """
    if format_string is None:
        format_string = (
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Reduce noise from third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

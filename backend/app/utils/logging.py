"""Logging utilities with correlation-id support."""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Final

_LOG_FORMAT: Final[str] = (
    "ts=%(asctime)s level=%(levelname)s logger=%(name)s "
    "correlation_id=%(correlation_id)s message=%(message)s"
)
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def set_correlation_id(correlation_id: str) -> None:
    """Bind a correlation id to the current execution context."""

    _correlation_id.set(correlation_id)


def clear_correlation_id() -> None:
    """Remove request-scoped correlation id from current context."""

    _correlation_id.set("-")


def get_correlation_id() -> str:
    """Return current request correlation id, if any."""

    return _correlation_id.get()


class CorrelationIdFilter(logging.Filter):
    """Inject correlation-id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


def configure_logging(log_level: str) -> None:
    """Configure root logging with structured, correlation-friendly formatting."""

    root_logger = logging.getLogger()
    resolved_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(resolved_level)

    formatter = logging.Formatter(_LOG_FORMAT)
    correlation_filter = CorrelationIdFilter()

    if not root_logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(correlation_filter)
        root_logger.addHandler(stream_handler)
        return

    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
        has_correlation_filter = any(
            isinstance(active_filter, CorrelationIdFilter)
            for active_filter in handler.filters
        )
        if not has_correlation_filter:
            handler.addFilter(correlation_filter)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger."""

    return logging.getLogger(name)

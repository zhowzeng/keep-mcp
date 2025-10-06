from __future__ import annotations

import logging
from typing import Any

import structlog
from structlog import contextvars

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structlog + stdlib logging once."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def get_logger(name: str = "keep_mcp") -> structlog.stdlib.BoundLogger:
    configure_logging()
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Attach contextual information to the current logger."""
    contextvars.bind_contextvars(**kwargs)

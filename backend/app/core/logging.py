"""Structured logging configuration for CampaignX.

Call ``setup_logging()`` once at application startup (in main.py lifespan).
All subsequent ``logging.getLogger(__name__)`` or ``get_logger(__name__)``
calls inherit the handlers and formatters.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# ── Correlation ID context variable ──────────────────────────────────────────
# Stored per-async-task so every log line within a request carries the same ID.
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    return _correlation_id.get()


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


# ── ANSI color helpers (no extra deps — pure escape codes) ────────────────────

_RESET = "\033[0m"
_BOLD = "\033[1m"
_LEVEL_COLORS: dict[str, str] = {
    "DEBUG": "\033[36m",     # cyan
    "INFO": "\033[32m",      # green
    "WARNING": "\033[33m",   # yellow
    "ERROR": "\033[31m",     # red
    "CRITICAL": "\033[35m",  # magenta
}


def _supports_color(stream: Any) -> bool:
    """Return True when *stream* looks like a color-capable terminal."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(stream, "isatty") and stream.isatty()


# ── Formatters ────────────────────────────────────────────────────────────────

class _ColorConsoleFormatter(logging.Formatter):
    """Human-readable colored formatter for development consoles."""

    _FMT = "{color}{bold}{level:<8}{reset} {dim}{ts}{reset}  {name}  {msg}"

    def __init__(self, use_color: bool = True) -> None:
        super().__init__()
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelname, "") if self._use_color else ""
        reset = _RESET if self._use_color else ""
        bold = _BOLD if self._use_color else ""
        dim = "\033[2m" if self._use_color else ""
        ts = self.formatTime(record, datefmt="%H:%M:%S")
        cid = get_correlation_id()

        parts = [
            f"{color}{bold}{record.levelname:<8}{reset}",
            f"{dim}{ts}{reset}",
            f"[{cid[:8]}]" if cid != "-" else "",
            f"{record.name}",
            record.getMessage(),
        ]
        line = "  ".join(p for p in parts if p)

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


class _JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects for production / file handler."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)
        # Append any extra fields attached via logger.info(..., extra={...})
        _std_keys = logging.LogRecord.__dict__.keys() | {
            "message", "asctime", "taskName"
        }
        extra = {k: v for k, v in record.__dict__.items()
                 if k not in _std_keys and not k.startswith("_")}
        if extra:
            payload.update(extra)
        return json.dumps(payload, default=str)


# ── Logger factory ────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """Return a standard library logger configured by ``setup_logging()``.

    Usage::

        logger = get_logger(__name__)
        logger.info("hello")
    """
    return logging.getLogger(name)


# ── Public setup function ─────────────────────────────────────────────────────

def setup_logging(log_level: str = "INFO", log_file: str = "logs/app.log") -> None:
    """Configure root logger with console + rotating file handlers.

    - **Console**: colored human-readable lines in dev; plain in non-TTY/prod.
    - **File**: rotating JSON, 10 MB per file, 5 backups.

    Args:
        log_level: One of DEBUG / INFO / WARNING / ERROR / CRITICAL.
        log_file:  Path to the rotating log file.  Parent dir created
                   automatically.  Pass empty string to disable file logging.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    use_color = _supports_color(sys.stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(_ColorConsoleFormatter(use_color=use_color))

    handlers: list[logging.Handler] = [console_handler]

    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(_JSONFormatter())
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)

    # Quieten noisy third-party loggers
    for noisy in ("motor", "pymongo", "httpx", "httpcore", "urllib3", "passlib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging initialised - level=%s file=%s color=%s",
        log_level, log_file or "disabled", use_color,
    )


# ── Structured event helpers ──────────────────────────────────────────────────

_mock_api_logger = logging.getLogger("campaignx.mock_api")
_workflow_logger = logging.getLogger("campaignx.workflow")
_req_logger = logging.getLogger("campaignx.http")


def log_mock_api_call(
    *,
    method: str,
    url: str,
    status_code: int | None,
    duration_ms: float,
    error: str | None = None,
    payload_size: int | None = None,
) -> None:
    """Emit a structured log line for every Mock Campaign API call.

    Args:
        method:       HTTP method (GET, POST, …).
        url:          Full request URL (no auth tokens in path).
        status_code:  HTTP response status, or None on network failure.
        duration_ms:  Round-trip time in milliseconds.
        error:        Exception message if the call failed.
        payload_size: Response body size in bytes (optional).
    """
    extra: dict[str, Any] = {
        "mock_api_method": method,
        "mock_api_url": url,
        "mock_api_status": status_code,
        "mock_api_duration_ms": duration_ms,
    }
    if payload_size is not None:
        extra["mock_api_payload_bytes"] = payload_size
    if error:
        extra["mock_api_error"] = error
        _mock_api_logger.warning(
            "Mock API %s %s -> ERROR %s  (%.1f ms): %s",
            method, url, status_code, duration_ms, error,
            extra=extra,
        )
    else:
        _mock_api_logger.info(
            "Mock API %s %s -> %d  (%.1f ms)",
            method, url, status_code, duration_ms,
            extra=extra,
        )


def log_workflow_transition(
    *,
    campaign_id: str,
    from_state: str,
    to_state: str,
    node: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Emit a structured log line for every LangGraph node/state transition.

    Args:
        campaign_id: The campaign being processed.
        from_state:  Previous workflow state or node name.
        to_state:    Next state or node name.
        node:        The graph node that triggered the transition.
        details:     Any extra context (variant count, error, etc.).
    """
    extra: dict[str, Any] = {
        "campaign_id": campaign_id,
        "wf_from": from_state,
        "wf_to": to_state,
        "wf_node": node,
    }
    if details:
        extra["wf_details"] = details
    _workflow_logger.info(
        "Workflow [%s] %s -> %s  (node: %s)",
        campaign_id, from_state, to_state, node,
        extra=extra,
    )


# ── Request / response logging middleware ─────────────────────────────────────

_SKIP_PATHS = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Assign a correlation ID per request and log method, path, status, duration.

    The correlation ID is exposed in:
    - The ``X-Correlation-ID`` response header
    - Every log line emitted during that request (via ``_correlation_id`` ContextVar)
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Honour an upstream-supplied ID (e.g. from API gateway), else generate one
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_correlation_id(cid)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        response.headers["X-Correlation-ID"] = cid

        if request.url.path not in _SKIP_PATHS:
            level = logging.WARNING if response.status_code >= 400 else logging.INFO
            _req_logger.log(
                level,
                "%s %s -> %d  (%.1f ms)",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": response.status_code,
                    "duration_ms": duration_ms,
                    "client_host": request.client.host if request.client else None,
                    "correlation_id": cid,
                },
            )
        return response

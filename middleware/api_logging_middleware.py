import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from uuid import uuid4

from starlette.requests import Request


API_LOGGER_NAME = "underwriting.api"
SERVICE_NAME = os.getenv("K_SERVICE", "underwriting-backend")
SAFE_REQUEST_HEADERS = (
    "accept",
    "content-length",
    "content-type",
    "user-agent",
    "x-client-platform",
    "x-request-id",
    "x-trace-id",
)
SENSITIVE_QUERY_KEYS = {
    "authorization",
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "pan",
    "aadhaar",
}
_SENSITIVE_ERROR_PATTERN = re.compile(
    r"(?i)(password|token|secret|authorization|cookie|api[_-]?key|pan|aadhaar)\s*[:=]\s*[^,\s]+"
)


def _json_logger() -> logging.Logger:
    logger = logging.getLogger(API_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(logging.INFO)
    return logger


logger = _json_logger()

EXCLUDED_ROLES = ('ADMIN','SUPER_ADMIN')

def _get_or_create_id(request: Request, state_key: str, header_name: str) -> str:
    value = request.headers.get(header_name)
    if not value:
        value = str(uuid4())

    if state_key == "request_id":
        request.state.request_id = value
    else:
        request.state.trace_id = value

    return value

def _request_headers(request: Request) -> dict[str, str]:
    return {
        header: request.headers[header]
        for header in SAFE_REQUEST_HEADERS
        if header in request.headers
    }


def _request_size(request: Request) -> int | None:
    content_length = request.headers.get("content-length")
    try:
        return int(content_length) if content_length is not None else None
    except ValueError:
        return None


def _query_params(request: Request) -> dict[str, str]:
    return {
        key: "[REDACTED]" if key.lower() in SENSITIVE_QUERY_KEYS else value
        for key, value in request.query_params.multi_items()
    }


def _response_size(response) -> int | None:
    content_length = response.headers.get("content-length")
    try:
        return int(content_length) if content_length is not None else None
    except ValueError:
        return None


def _client_ip(request: Request) -> str | None:
    # Cloud Run's proxy chain is not configured as a trusted proxy in this app.
    # Avoid treating user-supplied X-Forwarded-For as authoritative.
    return request.client.host if request.client else None


def _safe_error_message(exc: Exception) -> str:
    message = str(exc)[:500]
    return _SENSITIVE_ERROR_PATTERN.sub(r"\1=[REDACTED]", message)


def _user_context(request: Request) -> dict[str, object | None]:
    state = request.state._state
    return {
        "user_id": state.get("user_id"),
        "organization_id": state.get("organization_id"),
        "role": state.get("role"),
    }


def _build_record(
    request: Request,
    request_id: str,
    trace_id: str,
    start_time: float,
    response=None,
    exception: Exception | None = None,
) -> dict[str, object]:
    status_code = response.status_code if response is not None else 500
    failed = exception is not None or status_code >= 400
    error_type = type(exception).__name__ if exception is not None else None
    error_code = (
        exception.status_code
        if exception is not None and hasattr(exception, "status_code")
        else None
    )

    if exception is None and status_code >= 400:
        error_type = "HTTPError"
        error_code = status_code

    return {
        "_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "FAILED" if failed else "SUCCESS",
        "request": {
            "request_id": request_id,
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": _query_params(request),
            "headers": _request_headers(request),
            "request_size_bytes": _request_size(request),
        },
        "response": {
            "status_code": status_code,
            "response_size_bytes": _response_size(response) if response is not None else None,
        },
        "user": _user_context(request),
        "client": {
            "ip_address": _client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "platform": request.headers.get("x-client-platform"),
        },
        "service": {
            "service_name": SERVICE_NAME,
            "revision": os.getenv("K_REVISION"),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "git_commit": os.getenv("GIT_COMMIT"),
        },
        "performance": {
            "duration_ms": round((time.perf_counter() - start_time) * 1000, 2),
        },
        "error": {
            "occurred": failed,
            "type": error_type,
            "code": error_code,
            "message": _safe_error_message(exception) if exception is not None else None,
        },
    }


def _emit(record: dict[str, object]) -> None:
    logger.info(json.dumps(record, separators=(",", ":"), default=str))


async def _log_request_safely(
    request: Request,
    request_id: str,
    trace_id: str,
    start_time: float,
    response=None,
    exception: Exception | None = None,
) -> None:
    try:
        requester_role = request.state.role
        if requester_role in EXCLUDED_ROLES:
            return 
        
        record = _build_record(
            request,
            request_id,
            trace_id,
            start_time,
            response=response,
            exception=exception,
        )

        _emit(record)

        db = request.app.state.mongo_db
        
        await db.logs.insert_one(record)

    except Exception:
        # Logging failures must never affect the API response.
        pass


async def api_logging(request: Request, call_next):
    start_time = time.perf_counter()
    request_id = _get_or_create_id(request, "request_id", "x-request-id")
    trace_id = _get_or_create_id(request, "trace_id", "x-trace-id")
    response = None
    exception = None

    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        exception = exc
        raise
    finally:
        await _log_request_safely(
            request,
            request_id,
            trace_id,
            start_time,
            response=response,
            exception=exception,
        )

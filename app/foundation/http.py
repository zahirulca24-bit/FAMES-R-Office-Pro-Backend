from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


@dataclass(frozen=True, slots=True)
class ApiError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, object] | None = None


def error_response(error: ApiError, correlation_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "success": False,
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details or {},
            },
            "meta": {"correlation_id": correlation_id},
        },
        headers={"X-Correlation-ID": correlation_id},
    )


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get("X-Correlation-ID", "").strip()
        correlation_id = supplied[:100] if supplied else str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


def correlation_id_from_request(request: Request) -> str:
    return str(getattr(request.state, "correlation_id", "unknown"))

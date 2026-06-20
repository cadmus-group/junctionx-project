"""RFC 7807 problem-detail exception handling."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """Base class for domain errors mapped to problem details."""

    status: int = 400
    title: str = "Domain error"

    def __init__(self, detail: str | None = None):
        self.detail = detail
        super().__init__(detail or self.title)


class NotFoundError(DomainError):
    status = 404
    title = "Resource not found"


class ConflictError(DomainError):
    status = 409
    title = "Conflict"


class UnauthorizedError(DomainError):
    status = 401
    title = "Unauthorized"


def _problem(status: int, title: str, detail: str | None, instance: str) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=status,
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": instance,
        },
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> ORJSONResponse:
        return _problem(exc.status, exc.title, exc.detail, str(request.url.path))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> ORJSONResponse:
        return _problem(
            exc.status_code, str(exc.detail), None, str(request.url.path)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        return _problem(
            422, "Validation error", str(exc.errors()), str(request.url.path)
        )

    @app.exception_handler(SQLAlchemyError)
    async def _database(request: Request, exc: SQLAlchemyError) -> ORJSONResponse:
        logger.exception("Database error on %s", request.url.path)
        return _problem(
            500,
            "Database error",
            "A database error occurred. Run migrations if this is a fresh install.",
            str(request.url.path),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> ORJSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)
        return _problem(
            500,
            "Internal server error",
            "An unexpected error occurred.",
            str(request.url.path),
        )

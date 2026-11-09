"""Turns domain errors into HTTP responses, so services never deal with HTTP."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AuthenticationError,
    DomainError,
    InvalidPhotoError,
    NotFoundError,
    RateLimitExceededError,
)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: 404,
    InvalidPhotoError: 422,
    AuthenticationError: 401,
    RateLimitExceededError: 429,
}


def _handler_for(status_code: int):
    async def handle(_: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(
            {"detail": error.message}, status_code=status_code, headers=error.headers
        )

    return handle


def register_error_handlers(app: FastAPI) -> None:
    for error_class, status_code in _STATUS_BY_ERROR.items():
        app.add_exception_handler(error_class, _handler_for(status_code))

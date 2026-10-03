"""Centralized error handling and exception classes."""

from typing import Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse


class QreateError(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = 500, detail: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class NotFoundError(QreateError):
    def __init__(self, resource: str, resource_id: str = ""):
        msg = f"{resource} not found" + (f": {resource_id}" if resource_id else "")
        super().__init__(msg, status_code=404)


class ValidationError(QreateError):
    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class AgnesAPIError(QreateError):
    def __init__(self, message: str, status_code: int = 502, detail: Optional[dict] = None):
        super().__init__(message, status_code=status_code, detail=detail)


class AgnesQueueFullError(AgnesAPIError):
    def __init__(self, waited_seconds: int = 0):
        super().__init__(
            f"Agnes video queue is full. Tried for {waited_seconds}s. Please retry later.",
            status_code=503,
        )


class CloudinaryError(QreateError):
    def __init__(self, message: str):
        super().__init__(f"Cloudinary upload failed: {message}", status_code=502)


class DatabaseError(QreateError):
    def __init__(self, message: str):
        super().__init__(f"Database error: {message}", status_code=503)


async def qreate_exception_handler(request: Request, exc: QreateError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": exc.detail,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "An unexpected error occurred. Please try again."},
    )

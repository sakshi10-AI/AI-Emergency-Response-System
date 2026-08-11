"""
Global Exception Handler Middleware

Formats standardized JSON error responses for custom app exceptions and unhandled system errors.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from utils.exceptions import CustomAppException
from utils.logger import app_logger
from datetime import datetime

async def custom_app_exception_handler(request: Request, exc: CustomAppException):
    """Handler for domain-specific application exceptions."""
    app_logger.warning(f"AppException: [{exc.error_code}] {exc.message} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for Pydantic input validation failures."""
    app_logger.warning(f"ValidationError: {exc.errors()} - Path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "Invalid request parameters or body payload.",
            "details": exc.errors(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

async def global_exception_handler(request: Request, exc: Exception):
    """Fallback handler for unhandled server errors."""
    app_logger.error(f"Unhandled Internal Server Error: {str(exc)} - Path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred. Please contact system administrator.",
            "details": {},
            "timestamp": datetime.utcnow().isoformat()
        }
    )

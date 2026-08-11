"""
Custom System Exceptions

Defines domain-specific exception classes for structured error handling.
"""
from typing import Optional, Any, Dict

class CustomAppException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, status_code: int = 400, error_code: str = "BAD_REQUEST", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

class ResourceNotFoundError(CustomAppException):
    """Raised when a requested database resource does not exist."""
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=404, error_code="RESOURCE_NOT_FOUND", details=details)

class AuthenticationError(CustomAppException):
    """Raised when authentication fails or token is invalid."""
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=401, error_code="AUTHENTICATION_FAILED", details=details)

class PermissionDeniedError(CustomAppException):
    """Raised when a user lacks required role permissions."""
    def __init__(self, message: str = "Permission denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=403, error_code="PERMISSION_DENIED", details=details)

class DatabaseOperationError(CustomAppException):
    """Raised when a database query or transaction fails."""
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=500, error_code="DATABASE_ERROR", details=details)

class AgentExecutionError(CustomAppException):
    """Raised when a Google Gemini AI agent invocation fails."""
    def __init__(self, message: str = "AI Agent execution error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=502, error_code="AI_AGENT_ERROR", details=details)

"""
Standard error response models for API consistency.
All API endpoints should use these models for error responses.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""
    # Authentication & Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Resource
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # Server
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Business Logic
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    INVALID_OPERATION = "INVALID_OPERATION"


class ErrorResponse(BaseModel):
    """
    Standard error response model.
    All API error responses should follow this structure.
    """
    error: bool = Field(default=True, description="Always true for error responses")
    error_code: ErrorCode = Field(..., description="Standard error code")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    field: Optional[str] = Field(None, description="Field name if validation error")
    timestamp: Optional[str] = Field(None, description="Error timestamp (ISO format)")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional error metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid input provided",
                "detail": "Email field is required",
                "field": "email",
                "timestamp": "2024-01-01T00:00:00Z",
                "request_id": "req_123456",
                "metadata": {}
            }
        }


def create_error_response(
    error_code: ErrorCode,
    message: str,
    detail: Optional[str] = None,
    field: Optional[str] = None,
    status_code: int = 400,
    request_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> tuple[ErrorResponse, int]:
    """
    Helper function to create standardized error responses.
    
    Args:
        error_code: Standard error code
        message: Human-readable error message
        detail: Additional error details
        field: Field name if validation error
        status_code: HTTP status code
        request_id: Request ID for tracking
        metadata: Additional error metadata
    
    Returns:
        Tuple of (ErrorResponse, status_code)
    """
    from datetime import datetime
    
    error_response = ErrorResponse(
        error=True,
        error_code=error_code,
        message=message,
        detail=detail,
        field=field,
        timestamp=datetime.utcnow().isoformat() + "Z",
        request_id=request_id,
        metadata=metadata or {}
    )
    
    return error_response, status_code


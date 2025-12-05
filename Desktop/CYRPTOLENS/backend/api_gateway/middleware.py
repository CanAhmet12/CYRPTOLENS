"""
API Gateway middleware.
Handles versioning, deprecation warnings, and common request/response processing.
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from shared.api_versioning import (
    get_api_version,
    add_version_headers,
    check_version_deprecation,
    CURRENT_API_VERSION,
)


class APIVersioningMiddleware(BaseHTTPMiddleware):
    """Middleware for API versioning and deprecation warnings."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip versioning for health checks and docs
        if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
            response = await call_next(request)
            return response
        
        # Get API version from request
        version = get_api_version(request)
        
        # Check for deprecation
        deprecation_warning = check_version_deprecation(version)
        
        # Process request
        response = await call_next(request)
        
        # Add version headers
        add_version_headers(response, version)
        
        # Add deprecation warning to response if needed
        if deprecation_warning and isinstance(response, JSONResponse):
            # Add warning to response body if it's JSON
            try:
                body = response.body
                import json
                data = json.loads(body)
                if isinstance(data, dict):
                    data["_warning"] = deprecation_warning
                    return JSONResponse(
                        content=data,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                    )
            except:
                pass  # If response is not JSON, just add headers
        
        return response


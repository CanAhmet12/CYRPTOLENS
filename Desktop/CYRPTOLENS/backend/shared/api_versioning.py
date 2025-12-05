"""
API Versioning utilities.
Provides version management and deprecation warnings.
"""
from typing import Optional
from datetime import datetime
from enum import Enum
from fastapi import Request, Response
from fastapi.responses import JSONResponse


class APIVersion(str, Enum):
    """Supported API versions."""
    V1 = "v1"
    V2 = "v2"  # Future version


# Current API version
CURRENT_API_VERSION = APIVersion.V1

# Deprecated versions (will be removed in future)
DEPRECATED_VERSIONS: list[APIVersion] = []

# Version deprecation dates
VERSION_DEPRECATION_DATES: dict[APIVersion, Optional[datetime]] = {}


def get_api_version(request: Request) -> APIVersion:
    """
    Extract API version from request path.
    Defaults to current version if not specified.
    """
    path = request.url.path
    
    # Check for /api/v1/, /api/v2/, etc.
    if "/api/v1/" in path:
        return APIVersion.V1
    elif "/api/v2/" in path:
        return APIVersion.V2
    else:
        # Default to current version
        return CURRENT_API_VERSION


def add_version_headers(response: Response, version: APIVersion = CURRENT_API_VERSION):
    """
    Add version headers to response.
    """
    response.headers["API-Version"] = version.value
    response.headers["API-Current-Version"] = CURRENT_API_VERSION.value
    
    if version in DEPRECATED_VERSIONS:
        deprecation_date = VERSION_DEPRECATION_DATES.get(version)
        if deprecation_date:
            response.headers["API-Deprecated"] = "true"
            response.headers["API-Deprecation-Date"] = deprecation_date.isoformat()
            response.headers["Sunset"] = deprecation_date.isoformat()


def create_deprecation_warning(version: APIVersion, sunset_date: Optional[datetime] = None) -> dict:
    """
    Create deprecation warning message.
    """
    warning = {
        "warning": f"API version {version.value} is deprecated",
        "current_version": CURRENT_API_VERSION.value,
        "migration_guide": f"https://docs.cryptolens.com/api/migration/{version.value}-to-{CURRENT_API_VERSION.value}",
    }
    
    if sunset_date:
        warning["sunset_date"] = sunset_date.isoformat()
        warning["message"] = f"API version {version.value} will be removed on {sunset_date.isoformat()}"
    
    return warning


def check_version_deprecation(version: APIVersion) -> Optional[dict]:
    """
    Check if version is deprecated and return warning if so.
    """
    if version in DEPRECATED_VERSIONS:
        sunset_date = VERSION_DEPRECATION_DATES.get(version)
        return create_deprecation_warning(version, sunset_date)
    return None


"""
API versioning middleware.

Provides:
- API version headers in responses
- Deprecation warnings for old API versions
- Version information in response metadata
"""

import logging
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


logger = logging.getLogger(__name__)


# API version configuration
API_VERSIONS = {
    "v1": {
        "status": "stable",
        "deprecated": False,
        "sunset_date": None,  # ISO 8601 date when version will be removed
        "deprecation_message": None,
    },
    # Future versions can be added here
    # "v2": {
    #     "status": "beta",
    #     "deprecated": False,
    #     "sunset_date": None,
    #     "deprecation_message": None,
    # },
}

# Paths that should not get versioning headers (health checks, docs, etc.)
EXCLUDE_PATHS = {
    "/health",
    "/health/live",
    "/health/ready",
    "/health/startup",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def extract_api_version(path: str) -> str | None:
    """
    Extract API version from request path.

    Args:
        path: Request path (e.g., "/api/v1/agents/invoke")

    Returns:
        Version string (e.g., "v1") or None if not a versioned endpoint

    Examples:
        >>> extract_api_version("/api/v1/agents/invoke")
        "v1"
        >>> extract_api_version("/api/v2/users")
        "v2"
        >>> extract_api_version("/health")
        None
        >>> extract_api_version("/auth/me")
        None
    """
    parts = path.lstrip("/").split("/")

    # Check if path starts with /api/vX
    if len(parts) >= 2 and parts[0] == "api" and parts[1].startswith("v"):
        version = parts[1]
        if version in API_VERSIONS:
            return version

    return None


class APIVersioningMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add API version headers and deprecation warnings.

    Adds the following headers to responses:
    - X-API-Version: Current API version (e.g., "v1")
    - X-API-Deprecated: "true" if version is deprecated
    - Deprecation: Deprecation date (RFC 8594)
    - Sunset: Sunset date when API will be removed (RFC 8594)
    - Link: Link to migration guide for deprecated APIs

    Example Response Headers:
        X-API-Version: v1
        X-API-Deprecated: true
        Deprecation: Sat, 01 Jan 2025 00:00:00 GMT
        Sunset: Sat, 01 Jul 2025 00:00:00 GMT
        Link: <https://docs.example.com/api/v1-migration>; rel="deprecation"
    """

    def __init__(
        self,
        app: ASGIApp,
        migration_guide_url: str | None = None,
    ):
        """
        Initialize versioning middleware.

        Args:
            app: ASGI application
            migration_guide_url: Base URL for migration guides (e.g., "https://docs.example.com/api")
        """
        super().__init__(app)
        self.migration_guide_url = migration_guide_url

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and add version headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with version headers
        """
        # Get response from next middleware
        response = await call_next(request)

        # Skip versioning for excluded paths
        if any(request.url.path.startswith(path) for path in EXCLUDE_PATHS):
            return response

        # Extract API version from path
        version = extract_api_version(request.url.path)

        if version:
            version_info = API_VERSIONS.get(version)

            if version_info:
                # Add version header
                response.headers["X-API-Version"] = version

                # Add status header
                response.headers["X-API-Status"] = version_info["status"]

                # Add deprecation headers if version is deprecated
                if version_info["deprecated"]:
                    response.headers["X-API-Deprecated"] = "true"

                    # Add Deprecation header (RFC 8594)
                    # Format: Deprecation: @<timestamp>
                    # Example: Deprecation: @1672531200 (Unix timestamp)
                    if version_info.get("deprecation_date"):
                        try:
                            deprecation_dt = datetime.fromisoformat(
                                version_info["deprecation_date"]
                            )
                            # Unix timestamp format
                            timestamp = int(deprecation_dt.timestamp())
                            response.headers["Deprecation"] = f"@{timestamp}"
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Invalid deprecation_date for {version}: "
                                f"{version_info.get('deprecation_date')}"
                            )

                    # Add Sunset header (RFC 8594)
                    if version_info["sunset_date"]:
                        try:
                            sunset_dt = datetime.fromisoformat(
                                version_info["sunset_date"]
                            )
                            # HTTP date format
                            sunset_str = sunset_dt.strftime(
                                "%a, %d %b %Y %H:%M:%S GMT"
                            )
                            response.headers["Sunset"] = sunset_str
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Invalid sunset_date for {version}: "
                                f"{version_info['sunset_date']}"
                            )

                    # Add Link header pointing to migration guide
                    if self.migration_guide_url:
                        migration_url = f"{self.migration_guide_url}/{version}-migration"
                        response.headers["Link"] = (
                            f'<{migration_url}>; rel="deprecation"'
                        )

                    # Log deprecation warning
                    logger.warning(
                        f"Deprecated API version {version} accessed: "
                        f"path={request.url.path}, "
                        f"message={version_info.get('deprecation_message', 'Version is deprecated')}"
                    )

        return response


def get_current_api_version() -> str:
    """
    Get the current stable API version.

    Returns:
        Current stable version string (e.g., "v1")

    Example:
        >>> get_current_api_version()
        "v1"
    """
    for version, info in API_VERSIONS.items():
        if info["status"] == "stable" and not info["deprecated"]:
            return version

    # Fallback to latest version if no stable version found
    return max(API_VERSIONS.keys())


def is_version_deprecated(version: str) -> bool:
    """
    Check if an API version is deprecated.

    Args:
        version: Version string (e.g., "v1")

    Returns:
        True if version is deprecated, False otherwise

    Example:
        >>> is_version_deprecated("v1")
        False
    """
    version_info = API_VERSIONS.get(version)
    if not version_info:
        return True  # Unknown versions are considered deprecated

    return version_info["deprecated"]


def get_version_info(version: str) -> dict | None:
    """
    Get information about an API version.

    Args:
        version: Version string (e.g., "v1")

    Returns:
        Version information dict or None if version doesn't exist

    Example:
        >>> info = get_version_info("v1")
        >>> info["status"]
        "stable"
    """
    return API_VERSIONS.get(version)


# Example of how to deprecate a version:
"""
To deprecate an API version, update the API_VERSIONS configuration:

API_VERSIONS = {
    "v1": {
        "status": "deprecated",
        "deprecated": True,
        "deprecation_date": "2025-01-01T00:00:00Z",  # When it was deprecated
        "sunset_date": "2025-07-01T00:00:00Z",  # When it will be removed
        "deprecation_message": "API v1 is deprecated. Please migrate to v2.",
    },
    "v2": {
        "status": "stable",
        "deprecated": False,
        "sunset_date": None,
        "deprecation_message": None,
    },
}

Then update the migration guide URL when initializing the middleware:

app.add_middleware(
    APIVersioningMiddleware,
    migration_guide_url="https://docs.example.com/api"
)
"""

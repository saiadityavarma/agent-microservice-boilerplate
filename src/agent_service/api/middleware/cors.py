# src/agent_service/api/middleware/cors.py
import logging
from urllib.parse import urlparse

from agent_service.config.settings import Settings

logger = logging.getLogger(__name__)


def get_cors_middleware_config(settings: Settings) -> dict:
    """
    Get CORS middleware configuration based on environment settings.

    Args:
        settings: Application settings instance

    Returns:
        Dictionary of CORSMiddleware kwargs

    Raises:
        ValueError: If origin URLs have invalid format
    """
    # Determine allowed origins based on environment
    allowed_origins = settings.cors_origins.copy() if settings.cors_origins else []

    # In local/dev environments, allow localhost origins by default if none configured
    if settings.environment in ["local", "dev"] and not allowed_origins:
        default_dev_origins = [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:5173",  # Vite default
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:5173",
        ]
        allowed_origins = default_dev_origins
        logger.info(
            f"CORS: No origins configured in {settings.environment} environment, "
            f"using default localhost origins: {default_dev_origins}"
        )

    # Validate origin URLs format
    for origin in allowed_origins:
        if origin == "*":
            # Check for wildcard in production
            if settings.is_production:
                logger.warning(
                    "CORS: Wildcard origin '*' detected in PRODUCTION environment! "
                    "This is a security risk. Please configure specific origins."
                )
            continue

        # Validate URL format
        try:
            parsed = urlparse(origin)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(
                    f"Invalid origin URL format: {origin}. "
                    "Origins must include scheme and domain (e.g., 'http://localhost:3000')"
                )
        except Exception as e:
            raise ValueError(f"Failed to parse origin URL '{origin}': {e}")

    # Warn if no origins configured in staging/production
    if settings.environment in ["staging", "prod"] and not allowed_origins:
        logger.warning(
            f"CORS: No origins configured in {settings.environment.upper()} environment! "
            "All cross-origin requests will be blocked. "
            "Please set CORS_ORIGINS environment variable."
        )

    # Log final configuration
    logger.info(
        f"CORS Configuration: origins={allowed_origins}, "
        f"allow_credentials={settings.cors_allow_credentials}, "
        f"methods={settings.cors_allow_methods}, "
        f"max_age={settings.cors_max_age}"
    )

    return {
        "allow_origins": allowed_origins,
        "allow_credentials": settings.cors_allow_credentials,
        "allow_methods": settings.cors_allow_methods,
        "allow_headers": settings.cors_allow_headers,
        "max_age": settings.cors_max_age,
    }

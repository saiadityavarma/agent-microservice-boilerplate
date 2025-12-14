# src/agent_service/api/middleware/rate_limit.py
"""
Rate limiting middleware using slowapi with Redis backend.

Provides configurable rate limits with tier-based pricing (free, pro, enterprise)
and multiple rate limiting strategies (by user ID, API key, or IP).
"""
import logging
from typing import Callable, Optional
from functools import wraps

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from agent_service.config.settings import get_settings
from agent_service.infrastructure.cache.redis import get_redis

logger = logging.getLogger(__name__)


# Rate limit tiers configuration
RATE_LIMIT_TIERS = {
    "free": "100/hour",
    "pro": "1000/hour",
    "enterprise": "10000/hour",  # Can also be set to unlimited in custom logic
}


def get_user_key(request: Request) -> str:
    """
    Get rate limit key based on authenticated user ID.

    Extracts user ID from request state (set by auth middleware).
    Falls back to IP address if user is not authenticated.

    Args:
        request: FastAPI request object

    Returns:
        Rate limit key string
    """
    # Check if user is authenticated (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    # Fallback to IP
    return get_ip_key(request)


def get_api_key_key(request: Request) -> str:
    """
    Get rate limit key based on API key.

    Extracts API key from Authorization header or X-API-Key header.
    Falls back to IP address if no API key is found.

    Args:
        request: FastAPI request object

    Returns:
        Rate limit key string
    """
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        api_key = auth_header[7:]
        return f"api_key:{api_key[:16]}"  # Use first 16 chars for privacy

    # Check X-API-Key header
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        return f"api_key:{api_key[:16]}"

    # Fallback to IP
    return get_ip_key(request)


def get_ip_key(request: Request) -> str:
    """
    Get rate limit key based on client IP address.

    This is the fallback strategy when user ID or API key is not available.

    Args:
        request: FastAPI request object

    Returns:
        Rate limit key string
    """
    ip = get_remote_address(request)
    return f"ip:{ip}"


def get_tier_from_request(request: Request) -> str:
    """
    Extract user tier from request.

    Checks request state for user object with tier attribute.
    Returns default tier if not found.

    Args:
        request: FastAPI request object

    Returns:
        Tier name (free, pro, or enterprise)
    """
    settings = get_settings()

    # Check if user is authenticated and has tier
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "tier"):
        return user.tier

    # Check if API key has tier metadata
    api_key_meta = getattr(request.state, "api_key_meta", None)
    if api_key_meta and hasattr(api_key_meta, "tier"):
        return api_key_meta.tier

    # Return default tier
    return settings.rate_limit_default_tier


async def get_storage_from_redis():
    """
    Get Redis storage for slowapi.

    Returns None if Redis is not available, which causes slowapi to use in-memory storage.
    """
    redis = await get_redis()
    return redis


def create_rate_limiter() -> Limiter:
    """
    Create and configure rate limiter instance.

    Uses Redis backend if available, falls back to in-memory storage.

    Returns:
        Configured Limiter instance
    """
    settings = get_settings()

    # Create limiter with default key function (IP-based)
    limiter = Limiter(
        key_func=get_ip_key,
        default_limits=[],  # No default limits - apply per route
        storage_uri=settings.redis_url.get_secret_value() if settings.redis_url else "memory://",
        strategy="fixed-window",  # fixed-window, fixed-window-elastic-expiry, or moving-window
        headers_enabled=True,  # Enable X-RateLimit-* headers
    )

    return limiter


# Global limiter instance
limiter = create_rate_limiter()


def rate_limit(limit: str, key_func: Optional[Callable] = None):
    """
    Decorator to apply custom rate limit to a route.

    Usage:
        @router.get("/endpoint")
        @rate_limit("10/minute")
        async def my_endpoint():
            pass

        @router.get("/endpoint")
        @rate_limit("100/hour", key_func=get_user_key)
        async def my_endpoint():
            pass

    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour")
        key_func: Optional custom key function (defaults to IP-based)

    Returns:
        Decorated function with rate limiting
    """
    def decorator(func: Callable):
        # Use provided key_func or default to IP
        key_function = key_func or get_ip_key

        # Apply slowapi limiter decorator
        limited_func = limiter.limit(limit, key_func=key_function)(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await limited_func(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit_by_tier(key_func: Optional[Callable] = None):
    """
    Decorator to apply tier-based rate limit to a route.

    Automatically selects rate limit based on user's tier (free, pro, enterprise).

    Usage:
        @router.get("/endpoint")
        @rate_limit_by_tier()
        async def my_endpoint():
            pass

        @router.get("/endpoint")
        @rate_limit_by_tier(key_func=get_user_key)
        async def my_endpoint():
            pass

    Args:
        key_func: Optional custom key function (defaults to user-based)

    Returns:
        Decorated function with tier-based rate limiting
    """
    def decorator(func: Callable):
        # Use provided key_func or default to user-based
        key_function = key_func or get_user_key

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            if not request:
                # No request found, skip rate limiting
                logger.warning("No request found in rate_limit_by_tier decorator")
                return await func(*args, **kwargs)

            # Get user tier
            tier = get_tier_from_request(request)
            limit = RATE_LIMIT_TIERS.get(tier, RATE_LIMIT_TIERS["free"])

            # Apply rate limit dynamically
            limited_func = limiter.limit(limit, key_func=key_function)(func)
            return await limited_func(*args, **kwargs)

        return wrapper

    return decorator


def add_rate_limit_headers(response: Response, request: Request) -> Response:
    """
    Add X-RateLimit-* headers to response.

    Headers added:
    - X-RateLimit-Limit: Maximum requests allowed in window
    - X-RateLimit-Remaining: Requests remaining in current window
    - X-RateLimit-Reset: Unix timestamp when the window resets

    Args:
        response: FastAPI response object
        request: FastAPI request object

    Returns:
        Response with rate limit headers added
    """
    # slowapi automatically adds these headers when headers_enabled=True
    # This function is here for reference and custom header additions if needed

    # Access rate limit info from request state (set by slowapi)
    rate_limit_info = getattr(request.state, "view_rate_limit", None)

    if rate_limit_info:
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info.limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.remaining)
        response.headers["X-RateLimit-Reset"] = str(rate_limit_info.reset_time)

    return response


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Returns a JSON response with clear error message and rate limit headers.

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception

    Returns:
        JSONResponse with 429 status code
    """
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "detail": str(exc.detail),
        },
        headers={
            "Retry-After": str(exc.retry_after) if hasattr(exc, "retry_after") else "60",
        },
    )


class RateLimitMiddleware:
    """
    Rate limiting middleware for FastAPI.

    Integrates slowapi rate limiter into FastAPI middleware stack.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # slowapi handles rate limiting via decorators
        # This middleware is just a placeholder for future enhancements
        await self.app(scope, receive, send)


def setup_rate_limiting(app):
    """
    Setup rate limiting for FastAPI application.

    Adds rate limit middleware and error handlers.

    Args:
        app: FastAPI application instance
    """
    settings = get_settings()

    if not settings.rate_limit_enabled:
        logger.info("Rate limiting is disabled")
        return

    # Add slowapi middleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Note: slowapi works via decorators, not middleware
    # The actual rate limiting is applied by decorating routes
    logger.info(f"Rate limiting enabled with default tier: {settings.rate_limit_default_tier}")

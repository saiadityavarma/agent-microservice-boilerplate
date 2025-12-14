import time
import hashlib
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from agent_service.infrastructure.observability.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request metrics with detailed labels for observability."""

    def _hash_id(self, value: str, prefix: str = "") -> str:
        """
        Hash an ID for cardinality control in metrics.

        Uses first 8 characters of SHA256 hash to reduce cardinality
        while maintaining reasonable uniqueness for debugging.

        Args:
            value: The value to hash (user_id or api_key_id)
            prefix: Optional prefix for the hashed value

        Returns:
            Hashed value with optional prefix (e.g., "u_a1b2c3d4")
        """
        hash_obj = hashlib.sha256(value.encode())
        short_hash = hash_obj.hexdigest()[:8]
        return f"{prefix}{short_hash}" if prefix else short_hash

    def _extract_auth_info(self, request: Request) -> tuple[str, Optional[str], Optional[str]]:
        """
        Extract authentication information from request.

        Returns:
            Tuple of (auth_type, user_id_hash, api_key_id_hash)
            auth_type can be: "jwt", "api_key", or "none"
        """
        auth_type = "none"
        user_id_hash = None
        api_key_id_hash = None

        # Check for user info in request state (set by auth dependencies)
        if hasattr(request.state, "user"):
            user_info = request.state.user

            # Hash the user ID for cardinality control
            if user_info.id:
                user_id_hash = self._hash_id(user_info.id, prefix="u_")

            # Determine auth type and extract API key ID if present
            if user_info.metadata and "api_key_id" in user_info.metadata:
                auth_type = "api_key"
                api_key_id_hash = self._hash_id(
                    str(user_info.metadata["api_key_id"]),
                    prefix="k_"
                )
            else:
                auth_type = "jwt"

        return auth_type, user_id_hash, api_key_id_hash

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start

        # Extract authentication information
        auth_type, user_id_hash, api_key_id_hash = self._extract_auth_info(request)

        # Record request count with detailed labels
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()

        # Record request latency
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

        return response

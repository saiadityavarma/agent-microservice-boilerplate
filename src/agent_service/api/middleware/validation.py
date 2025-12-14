"""
Request validation middleware.

Provides middleware for validating incoming HTTP requests, including
Content-Type checks, suspicious pattern detection, and request body validation.
"""

import json
import structlog
from typing import Callable, Optional
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from agent_service.api.validators.validators import (
    validate_prompt_injection,
    validate_no_scripts,
)


logger = structlog.get_logger(__name__)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate incoming HTTP requests.

    Performs early validation checks before requests reach route handlers:
    - Content-Type validation
    - Request size limits
    - Suspicious pattern detection
    - Null byte detection
    """

    def __init__(
        self,
        app: ASGIApp,
        max_body_size: int = 10 * 1024 * 1024,  # 10MB default
        allowed_content_types: Optional[set[str]] = None,
        check_prompt_injection: bool = True,
        check_scripts: bool = True,
    ):
        """
        Initialize validation middleware.

        Args:
            app: ASGI application
            max_body_size: Maximum allowed request body size in bytes
            allowed_content_types: Set of allowed Content-Type headers
            check_prompt_injection: Enable prompt injection detection
            check_scripts: Enable script tag detection
        """
        super().__init__(app)
        self.max_body_size = max_body_size
        self.allowed_content_types = allowed_content_types or {
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data',
        }
        self.check_prompt_injection = check_prompt_injection
        self.check_scripts = check_scripts

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through validation checks.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Skip validation for certain paths
        if self._should_skip_validation(request.url.path):
            return await call_next(request)

        # Validate Content-Type for methods with body
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('content-type', '')

            # Extract base content type (ignore charset, boundary, etc.)
            base_content_type = content_type.split(';')[0].strip().lower()

            # Check if content type is allowed
            if base_content_type and not self._is_allowed_content_type(base_content_type):
                logger.warning(
                    "rejected_content_type",
                    content_type=content_type,
                    path=request.url.path,
                    method=request.method,
                )
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={
                        "error": "Unsupported Media Type",
                        "detail": f"Content-Type '{content_type}' is not allowed",
                    },
                )

        # Check for suspicious headers
        suspicious_header_check = self._check_suspicious_headers(request)
        if suspicious_header_check:
            return suspicious_header_check

        # Validate request body for JSON requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('content-type', '').lower()
            if 'application/json' in content_type:
                body_check = await self._validate_json_body(request)
                if body_check:
                    return body_check

        # Process request
        response = await call_next(request)

        return response

    def _should_skip_validation(self, path: str) -> bool:
        """
        Check if validation should be skipped for this path.

        Args:
            path: Request path

        Returns:
            True if validation should be skipped
        """
        # Skip validation for health checks and metrics
        skip_paths = [
            '/health',
            '/healthz',
            '/metrics',
            '/docs',
            '/redoc',
            '/openapi.json',
        ]

        return any(path.startswith(skip_path) for skip_path in skip_paths)

    def _is_allowed_content_type(self, content_type: str) -> bool:
        """
        Check if content type is allowed.

        Args:
            content_type: Content-Type header value

        Returns:
            True if content type is allowed
        """
        # Check exact match
        if content_type in self.allowed_content_types:
            return True

        # Check prefix match for multipart/form-data (has boundary parameter)
        if content_type.startswith('multipart/form-data'):
            return 'multipart/form-data' in self.allowed_content_types

        return False

    def _check_suspicious_headers(self, request: Request) -> Optional[JSONResponse]:
        """
        Check for suspicious patterns in request headers.

        Args:
            request: HTTP request

        Returns:
            JSONResponse if suspicious patterns found, None otherwise
        """
        # Check for null bytes in headers
        for name, value in request.headers.items():
            if '\x00' in value or '\u0000' in value:
                logger.warning(
                    "null_byte_in_header",
                    header=name,
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Bad Request",
                        "detail": "Invalid characters in request headers",
                    },
                )

            # Check for excessively long header values
            if len(value) > 8192:  # 8KB limit per header
                logger.warning(
                    "oversized_header",
                    header=name,
                    size=len(value),
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=status.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE,
                    content={
                        "error": "Request Header Fields Too Large",
                        "detail": f"Header '{name}' exceeds maximum size",
                    },
                )

        return None

    async def _validate_json_body(self, request: Request) -> Optional[JSONResponse]:
        """
        Validate JSON request body.

        Args:
            request: HTTP request

        Returns:
            JSONResponse if validation fails, None otherwise
        """
        try:
            # Read body
            body = await request.body()

            # Check body size
            if len(body) > self.max_body_size:
                logger.warning(
                    "oversized_body",
                    size=len(body),
                    max_size=self.max_body_size,
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "error": "Payload Too Large",
                        "detail": f"Request body exceeds maximum size of {self.max_body_size} bytes",
                    },
                )

            # Check for null bytes in body
            if b'\x00' in body:
                logger.warning(
                    "null_byte_in_body",
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Bad Request",
                        "detail": "Invalid characters in request body",
                    },
                )

            # Try to parse JSON
            try:
                body_str = body.decode('utf-8')
                data = json.loads(body_str)
            except json.JSONDecodeError as e:
                logger.warning(
                    "invalid_json",
                    error=str(e),
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Bad Request",
                        "detail": "Invalid JSON in request body",
                    },
                )
            except UnicodeDecodeError:
                logger.warning(
                    "invalid_encoding",
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Bad Request",
                        "detail": "Invalid character encoding in request body",
                    },
                )

            # Validate string values in JSON
            validation_error = self._validate_json_values(data, request.url.path)
            if validation_error:
                return validation_error

            # Note: We need to restore the body for downstream handlers
            # This is done by FastAPI automatically when we call request.body()

        except Exception as e:
            logger.error(
                "body_validation_error",
                error=str(e),
                path=request.url.path,
            )
            # Don't fail the request on internal validation errors
            # Let it proceed to route handler

        return None

    def _validate_json_values(
        self,
        data: any,
        path: str,
        max_depth: int = 10,
        current_depth: int = 0
    ) -> Optional[JSONResponse]:
        """
        Recursively validate JSON values for suspicious patterns.

        Args:
            data: JSON data to validate
            path: Request path (for logging)
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth

        Returns:
            JSONResponse if validation fails, None otherwise
        """
        # Prevent excessive recursion
        if current_depth > max_depth:
            logger.warning(
                "json_too_deep",
                path=path,
                depth=current_depth,
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Bad Request",
                    "detail": "JSON structure too deeply nested",
                },
            )

        if isinstance(data, dict):
            # Limit number of keys
            if len(data) > 1000:
                logger.warning(
                    "too_many_keys",
                    path=path,
                    count=len(data),
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Bad Request",
                        "detail": "Too many keys in JSON object",
                    },
                )

            # Validate each value
            for key, value in data.items():
                # Check key for null bytes
                if '\x00' in str(key):
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "error": "Bad Request",
                            "detail": "Invalid characters in JSON keys",
                        },
                    )

                result = self._validate_json_values(value, path, max_depth, current_depth + 1)
                if result:
                    return result

        elif isinstance(data, list):
            # Limit list size
            if len(data) > 10000:
                logger.warning(
                    "oversized_array",
                    path=path,
                    count=len(data),
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Bad Request",
                        "detail": "Array too large",
                    },
                )

            # Validate each item
            for item in data:
                result = self._validate_json_values(item, path, max_depth, current_depth + 1)
                if result:
                    return result

        elif isinstance(data, str):
            # Check for null bytes
            if '\x00' in data or '\u0000' in data:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Bad Request",
                        "detail": "Invalid characters in string values",
                    },
                )

            # Check string length
            if len(data) > 100000:  # 100KB per string
                logger.warning(
                    "oversized_string",
                    path=path,
                    size=len(data),
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Bad Request",
                        "detail": "String value too large",
                    },
                )

            # Optional: Check for prompt injection
            if self.check_prompt_injection:
                if not validate_prompt_injection(data, strict=False):
                    logger.warning(
                        "potential_injection",
                        path=path,
                    )
                    # Note: We log but don't reject - let route handler decide
                    # Uncomment to enforce:
                    # return JSONResponse(...)

            # Optional: Check for scripts
            if self.check_scripts:
                if not validate_no_scripts(data):
                    logger.warning(
                        "script_content_detected",
                        path=path,
                    )
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "error": "Bad Request",
                            "detail": "Script content not allowed",
                        },
                    )

        return None


def setup_validation_middleware(
    app: ASGIApp,
    max_body_size: int = 10 * 1024 * 1024,
    allowed_content_types: Optional[set[str]] = None,
    check_prompt_injection: bool = True,
    check_scripts: bool = True,
) -> None:
    """
    Setup request validation middleware.

    Args:
        app: FastAPI application
        max_body_size: Maximum request body size in bytes
        allowed_content_types: Set of allowed Content-Type headers
        check_prompt_injection: Enable prompt injection detection
        check_scripts: Enable script tag detection
    """
    app.add_middleware(
        RequestValidationMiddleware,
        max_body_size=max_body_size,
        allowed_content_types=allowed_content_types,
        check_prompt_injection=check_prompt_injection,
        check_scripts=check_scripts,
    )
    logger.info(
        "validation_middleware_configured",
        max_body_size=max_body_size,
        check_prompt_injection=check_prompt_injection,
        check_scripts=check_scripts,
    )

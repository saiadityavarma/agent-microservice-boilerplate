"""
Built-in HTTP request tools.

Provides tools for making HTTP requests with various methods.
Includes automatic error handling, timeout support, and response formatting.
"""

from typing import Any, Literal
import httpx

from agent_service.tools.decorators import tool, confirmed_tool


@tool(
    name="http_get",
    description="Make an HTTP GET request to a URL",
    timeout=30.0,
)
async def http_get(
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Make an HTTP GET request.

    Args:
        url: URL to request
        headers: Optional HTTP headers
        params: Optional query parameters

    Returns:
        Response data including status code, headers, and body

    Example:
        >>> result = await http_get("https://api.example.com/data")
        >>> print(result["status_code"])
        200
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers or {},
            params=params or {},
        )

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "json": response.json() if _is_json_response(response) else None,
        }


@confirmed_tool(
    name="http_post",
    description="Make an HTTP POST request to a URL",
    timeout=30.0,
)
async def http_post(
    url: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Make an HTTP POST request.

    Args:
        url: URL to request
        body: Request body (will be sent as JSON)
        headers: Optional HTTP headers
        params: Optional query parameters

    Returns:
        Response data including status code, headers, and body

    Example:
        >>> result = await http_post(
        ...     "https://api.example.com/create",
        ...     body={"name": "John", "email": "john@example.com"}
        ... )
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=body,
            headers=headers or {},
            params=params or {},
        )

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "json": response.json() if _is_json_response(response) else None,
        }


@confirmed_tool(
    name="http_put",
    description="Make an HTTP PUT request to a URL",
    timeout=30.0,
)
async def http_put(
    url: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Make an HTTP PUT request.

    Args:
        url: URL to request
        body: Request body (will be sent as JSON)
        headers: Optional HTTP headers
        params: Optional query parameters

    Returns:
        Response data including status code, headers, and body

    Example:
        >>> result = await http_put(
        ...     "https://api.example.com/users/123",
        ...     body={"name": "John Updated"}
        ... )
    """
    async with httpx.AsyncClient() as client:
        response = await client.put(
            url,
            json=body,
            headers=headers or {},
            params=params or {},
        )

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "json": response.json() if _is_json_response(response) else None,
        }


@confirmed_tool(
    name="http_delete",
    description="Make an HTTP DELETE request to a URL",
    timeout=30.0,
)
async def http_delete(
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Make an HTTP DELETE request.

    Args:
        url: URL to request
        headers: Optional HTTP headers
        params: Optional query parameters

    Returns:
        Response data including status code, headers, and body

    Example:
        >>> result = await http_delete("https://api.example.com/users/123")
        >>> print(result["status_code"])
        204
    """
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            url,
            headers=headers or {},
            params=params or {},
        )

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "json": response.json() if _is_json_response(response) else None,
        }


@confirmed_tool(
    name="http_request",
    description="Make an HTTP request with any method (GET, POST, PUT, DELETE, PATCH, etc.)",
    timeout=30.0,
)
async def http_request(
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    url: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Make an HTTP request with any method.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
        url: URL to request
        body: Request body (will be sent as JSON, ignored for GET/HEAD/OPTIONS)
        headers: Optional HTTP headers
        params: Optional query parameters

    Returns:
        Response data including status code, headers, and body

    Example:
        >>> result = await http_request(
        ...     method="PATCH",
        ...     url="https://api.example.com/users/123",
        ...     body={"email": "new@example.com"}
        ... )
    """
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method,
            url=url,
            json=body if method not in ["GET", "HEAD", "OPTIONS"] else None,
            headers=headers or {},
            params=params or {},
        )

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "json": response.json() if _is_json_response(response) else None,
        }


def _is_json_response(response: httpx.Response) -> bool:
    """
    Check if response is JSON.

    Args:
        response: HTTP response

    Returns:
        True if response is JSON, False otherwise
    """
    content_type = response.headers.get("content-type", "")
    return "application/json" in content_type.lower()

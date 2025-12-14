"""
Built-in tools for common operations.

This package provides ready-to-use tools for:
- HTTP requests (GET, POST, PUT, DELETE, etc.)
- SQL queries (read-only by default)
- And more...

All built-in tools are automatically registered when imported.
"""

from agent_service.tools.builtin.http import (
    http_get,
    http_post,
    http_put,
    http_delete,
    http_request,
)
from agent_service.tools.builtin.sql import (
    sql_query,
    sql_execute,
)

__all__ = [
    "http_get",
    "http_post",
    "http_put",
    "http_delete",
    "http_request",
    "sql_query",
    "sql_execute",
]

"""
Built-in SQL query tools.

Provides tools for executing SQL queries safely with read-only and
read-write modes. Includes query validation, parameter sanitization,
and result formatting.
"""

from typing import Any, Literal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent_service.tools.decorators import tool, confirmed_tool
from agent_service.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


# Dangerous SQL keywords that should be blocked in read-only mode
DANGEROUS_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "CREATE",
    "ALTER",
    "TRUNCATE",
    "REPLACE",
    "MERGE",
    "GRANT",
    "REVOKE",
]


def _validate_read_only_query(query: str) -> None:
    """
    Validate that a query is read-only (SELECT only).

    Args:
        query: SQL query to validate

    Raises:
        ValueError: If query contains write operations
    """
    query_upper = query.upper().strip()

    # Check for dangerous keywords
    for keyword in DANGEROUS_KEYWORDS:
        if keyword in query_upper:
            raise ValueError(
                f"Query contains forbidden keyword '{keyword}'. "
                "Use sql_execute for write operations."
            )

    # Check that query starts with SELECT or WITH (for CTEs)
    if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
        raise ValueError(
            "Query must start with SELECT or WITH. "
            "Use sql_execute for other operations."
        )


def _format_results(rows: list[Any]) -> list[dict[str, Any]]:
    """
    Format SQL results as list of dictionaries.

    Args:
        rows: Raw SQL rows

    Returns:
        List of row dictionaries

    Example:
        >>> rows = [(1, "John"), (2, "Jane")]
        >>> _format_results(rows)
        [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]
    """
    if not rows:
        return []

    # Convert rows to dictionaries
    result = []
    for row in rows:
        if hasattr(row, "_mapping"):
            # SQLAlchemy Row object
            result.append(dict(row._mapping))
        elif hasattr(row, "__dict__"):
            # ORM model object
            result.append({
                k: v for k, v in row.__dict__.items()
                if not k.startswith("_")
            })
        else:
            # Tuple or other
            result.append(row)

    return result


@tool(
    name="sql_query",
    description="Execute a read-only SQL query (SELECT only)",
    timeout=30.0,
)
async def sql_query(
    query: str,
    params: dict[str, Any] | None = None,
    limit: int | None = 100,
) -> dict[str, Any]:
    """
    Execute a read-only SQL query.

    This tool only allows SELECT queries for safety. Use sql_execute
    for write operations (INSERT, UPDATE, DELETE).

    Args:
        query: SQL SELECT query
        params: Query parameters (will be safely bound)
        limit: Maximum number of rows to return (default: 100)

    Returns:
        Query results with row count and data

    Raises:
        ValueError: If query is not read-only
        Exception: Database errors

    Example:
        >>> result = await sql_query(
        ...     query="SELECT * FROM users WHERE email = :email",
        ...     params={"email": "john@example.com"}
        ... )
        >>> print(result["row_count"])
        1
        >>> print(result["rows"][0])
        {"id": 1, "email": "john@example.com", "name": "John"}
    """
    # Validate query is read-only
    _validate_read_only_query(query)

    # Get database session
    from agent_service.infrastructure.database.connection import db

    if not db.is_connected:
        raise RuntimeError("Database not connected")

    # Add LIMIT if specified and not already in query
    if limit is not None and "LIMIT" not in query.upper():
        query = f"{query} LIMIT {limit}"

    logger.info("executing_sql_query", query=query[:100], params=list(params.keys()) if params else [])

    async with db.session() as session:
        # Execute query with parameters
        result = await session.execute(
            text(query),
            params or {},
        )

        # Fetch all rows
        rows = result.fetchall()

        # Format results
        formatted_rows = _format_results(rows)

        logger.info("sql_query_completed", row_count=len(formatted_rows))

        return {
            "row_count": len(formatted_rows),
            "rows": formatted_rows,
            "columns": list(formatted_rows[0].keys()) if formatted_rows else [],
        }


@confirmed_tool(
    name="sql_execute",
    description="Execute a SQL statement (INSERT, UPDATE, DELETE, etc.) - REQUIRES CONFIRMATION",
    timeout=30.0,
)
async def sql_execute(
    query: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute a SQL statement with write operations.

    This tool allows INSERT, UPDATE, DELETE and other write operations.
    It requires user confirmation before execution.

    Args:
        query: SQL statement to execute
        params: Query parameters (will be safely bound)

    Returns:
        Execution results with rows affected

    Raises:
        Exception: Database errors

    Example:
        >>> result = await sql_execute(
        ...     query="UPDATE users SET name = :name WHERE id = :id",
        ...     params={"name": "John Updated", "id": 1}
        ... )
        >>> print(result["rows_affected"])
        1
    """
    # Get database session
    from agent_service.infrastructure.database.connection import db

    if not db.is_connected:
        raise RuntimeError("Database not connected")

    logger.warning(
        "executing_sql_statement",
        query=query[:100],
        params=list(params.keys()) if params else [],
    )

    async with db.session() as session:
        # Execute statement with parameters
        result = await session.execute(
            text(query),
            params or {},
        )

        # Get affected rows
        rows_affected = result.rowcount

        # Commit is handled by the context manager
        logger.info("sql_execute_completed", rows_affected=rows_affected)

        return {
            "rows_affected": rows_affected,
            "success": True,
        }


@tool(
    name="sql_query_one",
    description="Execute a read-only SQL query and return only the first row",
    timeout=30.0,
)
async def sql_query_one(
    query: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Execute a read-only SQL query and return only the first row.

    Convenience wrapper around sql_query for single-row queries.

    Args:
        query: SQL SELECT query
        params: Query parameters (will be safely bound)

    Returns:
        First row as dictionary, or None if no results

    Example:
        >>> user = await sql_query_one(
        ...     query="SELECT * FROM users WHERE id = :id",
        ...     params={"id": 1}
        ... )
        >>> print(user["email"] if user else "Not found")
        john@example.com
    """
    result = await sql_query(query=query, params=params, limit=1)

    if result["row_count"] == 0:
        return None

    return result["rows"][0]


@tool(
    name="sql_query_scalar",
    description="Execute a read-only SQL query and return a single scalar value",
    timeout=30.0,
)
async def sql_query_scalar(
    query: str,
    params: dict[str, Any] | None = None,
) -> Any:
    """
    Execute a read-only SQL query and return a single scalar value.

    Useful for COUNT, SUM, AVG, etc. queries.

    Args:
        query: SQL SELECT query that returns a single value
        params: Query parameters (will be safely bound)

    Returns:
        Single scalar value, or None if no results

    Example:
        >>> count = await sql_query_scalar(
        ...     query="SELECT COUNT(*) FROM users WHERE is_active = :active",
        ...     params={"active": True}
        ... )
        >>> print(count)
        42
    """
    result = await sql_query_one(query=query, params=params)

    if result is None:
        return None

    # Return first value from the row
    return next(iter(result.values()))

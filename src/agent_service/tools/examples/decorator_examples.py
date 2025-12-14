"""
Examples of using the @tool decorator.

This module demonstrates various ways to create tools using decorators
instead of implementing the ITool interface manually.
"""

from typing import Any, Literal
import asyncio

from agent_service.tools.decorators import tool, confirmed_tool


# ============================================================================
# Example 1: Simple Tool
# ============================================================================


@tool(name="greet", description="Greet someone by name")
async def greet(name: str, greeting: str = "Hello") -> str:
    """
    Simple greeting tool.

    This demonstrates the minimal tool implementation with type annotations.
    """
    return f"{greeting}, {name}!"


# ============================================================================
# Example 2: Tool with Multiple Parameters
# ============================================================================


@tool(
    name="calculate",
    description="Perform basic arithmetic operations"
)
async def calculate(
    operation: Literal["add", "subtract", "multiply", "divide"],
    a: float,
    b: float,
) -> dict[str, Any]:
    """
    Calculator tool with multiple parameters.

    Demonstrates type annotations including Literal types.
    """
    result = 0.0

    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b

    return {
        "operation": operation,
        "a": a,
        "b": b,
        "result": result,
    }


# ============================================================================
# Example 3: Tool with Complex Return Type
# ============================================================================


@tool(
    name="analyze_text",
    description="Analyze text and return statistics"
)
async def analyze_text(text: str) -> dict[str, Any]:
    """
    Text analysis tool.

    Demonstrates complex return types.
    """
    words = text.split()
    lines = text.split("\n")

    return {
        "character_count": len(text),
        "word_count": len(words),
        "line_count": len(lines),
        "average_word_length": sum(len(word) for word in words) / len(words) if words else 0,
        "longest_word": max(words, key=len) if words else "",
    }


# ============================================================================
# Example 4: Tool with Optional Parameters
# ============================================================================


@tool(
    name="search",
    description="Search for items with optional filters"
)
async def search(
    query: str,
    category: str | None = None,
    max_results: int = 10,
    include_metadata: bool = False,
) -> list[dict[str, Any]]:
    """
    Search tool with optional parameters.

    Demonstrates optional parameters with type annotations.
    """
    # Simulate search results
    results = [
        {
            "title": f"Result {i+1} for '{query}'",
            "category": category or "general",
            "score": 1.0 - (i * 0.1),
        }
        for i in range(min(max_results, 5))
    ]

    if include_metadata:
        for result in results:
            result["metadata"] = {
                "source": "example",
                "timestamp": "2025-01-01T00:00:00Z",
            }

    return results


# ============================================================================
# Example 5: Tool with Timeout
# ============================================================================


@tool(
    name="slow_operation",
    description="Simulates a slow operation with timeout",
    timeout=5.0,
)
async def slow_operation(duration: float) -> str:
    """
    Tool with timeout handling.

    Demonstrates the timeout parameter. If duration > 5 seconds,
    the tool will timeout.
    """
    await asyncio.sleep(duration)
    return f"Completed after {duration} seconds"


# ============================================================================
# Example 6: Confirmed Tool (Requires User Confirmation)
# ============================================================================


@confirmed_tool(
    name="delete_item",
    description="Delete an item (REQUIRES CONFIRMATION)"
)
async def delete_item(item_id: str) -> dict[str, Any]:
    """
    Tool that requires user confirmation.

    Demonstrates the @confirmed_tool decorator.
    """
    # Simulate deletion
    return {
        "deleted": True,
        "item_id": item_id,
        "message": f"Item {item_id} has been deleted",
    }


# ============================================================================
# Example 7: Tool with List and Dict Parameters
# ============================================================================


@tool(
    name="process_batch",
    description="Process a batch of items with configuration"
)
async def process_batch(
    items: list[str],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Batch processing tool.

    Demonstrates list and dict type annotations.
    """
    config = config or {}
    uppercase = config.get("uppercase", False)
    prefix = config.get("prefix", "")

    processed = []
    for item in items:
        processed_item = item
        if uppercase:
            processed_item = processed_item.upper()
        if prefix:
            processed_item = f"{prefix}{processed_item}"
        processed.append(processed_item)

    return {
        "original_count": len(items),
        "processed_count": len(processed),
        "items": processed,
    }


# ============================================================================
# Example 8: Tool Without Auto-Registration
# ============================================================================


@tool(
    name="manual_tool",
    description="Tool that is not auto-registered",
    auto_register=False,
)
async def manual_tool(value: str) -> str:
    """
    Tool that is not automatically registered.

    Use this when you want to manually control registration:
        >>> from agent_service.tools.registry import tool_registry
        >>> tool_registry.register(manual_tool)
    """
    return f"Manually registered tool processed: {value}"


# ============================================================================
# Example 9: Tool with Error Handling
# ============================================================================


@tool(
    name="safe_divide",
    description="Safely divide two numbers with error handling"
)
async def safe_divide(
    numerator: float,
    denominator: float,
    default_on_error: float | None = None,
) -> dict[str, Any]:
    """
    Division tool with error handling.

    Demonstrates error handling in tools.
    """
    try:
        if denominator == 0:
            raise ValueError("Division by zero")

        result = numerator / denominator

        return {
            "success": True,
            "result": result,
            "error": None,
        }

    except Exception as e:
        if default_on_error is not None:
            return {
                "success": False,
                "result": default_on_error,
                "error": str(e),
            }
        raise


# ============================================================================
# Example 10: Tool with External API Call
# ============================================================================


@tool(
    name="fetch_weather",
    description="Fetch weather information for a location",
    timeout=10.0,
)
async def fetch_weather(
    location: str,
    units: Literal["metric", "imperial"] = "metric",
) -> dict[str, Any]:
    """
    Weather fetching tool.

    Demonstrates external API calls (simulated).
    """
    # Simulate API call
    await asyncio.sleep(0.5)

    # Simulated response
    temp = 20 if units == "metric" else 68

    return {
        "location": location,
        "temperature": temp,
        "units": units,
        "condition": "Sunny",
        "humidity": 65,
    }


# ============================================================================
# Example 11: Data Validation Tool
# ============================================================================


@tool(
    name="validate_email",
    description="Validate email addresses"
)
async def validate_email(email: str) -> dict[str, Any]:
    """
    Email validation tool.

    Demonstrates input validation.
    """
    import re

    # Simple email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = bool(re.match(pattern, email))

    result = {
        "email": email,
        "is_valid": is_valid,
    }

    if is_valid:
        # Extract parts
        local, domain = email.split("@")
        result["local_part"] = local
        result["domain"] = domain
    else:
        result["error"] = "Invalid email format"

    return result


# ============================================================================
# Example 12: Tool with Nested Data Structures
# ============================================================================


@tool(
    name="transform_data",
    description="Transform nested data structures"
)
async def transform_data(
    data: dict[str, Any],
    transformations: list[dict[str, str]],
) -> dict[str, Any]:
    """
    Data transformation tool.

    Demonstrates working with nested data structures.
    """
    result = data.copy()

    for transform in transformations:
        operation = transform.get("operation")
        field = transform.get("field")

        if not operation or not field:
            continue

        if field in result:
            if operation == "uppercase" and isinstance(result[field], str):
                result[field] = result[field].upper()
            elif operation == "lowercase" and isinstance(result[field], str):
                result[field] = result[field].lower()
            elif operation == "double" and isinstance(result[field], (int, float)):
                result[field] = result[field] * 2

    return result


# ============================================================================
# Example 13: Tool with File Operations (Simulated)
# ============================================================================


@confirmed_tool(
    name="write_file",
    description="Write content to a file (REQUIRES CONFIRMATION)",
    timeout=30.0,
)
async def write_file(
    path: str,
    content: str,
    append: bool = False,
) -> dict[str, Any]:
    """
    File writing tool.

    Demonstrates file operations (simulated for safety).
    """
    # In a real implementation, you would actually write to a file
    # For this example, we just simulate it

    mode = "append" if append else "write"

    return {
        "success": True,
        "path": path,
        "mode": mode,
        "bytes_written": len(content),
        "message": f"Successfully {mode}d {len(content)} bytes to {path}",
    }


# ============================================================================
# Example 14: Tool with Retry Logic
# ============================================================================


@tool(
    name="retry_operation",
    description="Perform an operation with retry logic",
    timeout=30.0,
)
async def retry_operation(
    operation_id: str,
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    Tool with retry logic.

    Demonstrates retry patterns.
    """
    import random

    for attempt in range(max_retries):
        # Simulate operation that might fail
        success = random.random() > 0.5

        if success:
            return {
                "success": True,
                "operation_id": operation_id,
                "attempts": attempt + 1,
                "message": f"Operation succeeded on attempt {attempt + 1}",
            }

        # Wait before retry
        await asyncio.sleep(0.5 * (attempt + 1))

    return {
        "success": False,
        "operation_id": operation_id,
        "attempts": max_retries,
        "message": f"Operation failed after {max_retries} attempts",
    }


# ============================================================================
# Example 15: Aggregation Tool
# ============================================================================


@tool(
    name="aggregate_stats",
    description="Calculate aggregate statistics from a list of numbers"
)
async def aggregate_stats(
    numbers: list[float],
    include_median: bool = True,
) -> dict[str, Any]:
    """
    Statistical aggregation tool.

    Demonstrates working with lists of numbers.
    """
    if not numbers:
        return {
            "error": "No numbers provided",
            "count": 0,
        }

    stats = {
        "count": len(numbers),
        "sum": sum(numbers),
        "mean": sum(numbers) / len(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "range": max(numbers) - min(numbers),
    }

    if include_median:
        sorted_numbers = sorted(numbers)
        n = len(sorted_numbers)
        if n % 2 == 0:
            stats["median"] = (sorted_numbers[n//2 - 1] + sorted_numbers[n//2]) / 2
        else:
            stats["median"] = sorted_numbers[n//2]

    return stats

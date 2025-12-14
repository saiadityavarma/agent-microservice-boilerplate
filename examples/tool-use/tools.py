"""
Custom Tools for Tool-Using Agent

Demonstrates various types of tools:
- Calculator (simple computation)
- Web search (external API simulation)
- File operations (read/write)
- Data processing (transformation)
- API integration (external services)
"""

from typing import Any
from agent_service.tools import tool, confirmed_tool
import json
import math


# ============================================================================
# Calculator Tools
# ============================================================================


@tool(
    name="calculate",
    description="Perform mathematical calculations",
    timeout=5.0
)
async def calculate(expression: str) -> dict[str, Any]:
    """
    Safely evaluate mathematical expressions.

    Args:
        expression: Math expression (e.g., "2 + 2", "sqrt(16)", "10 * 5")

    Returns:
        Calculation result

    Examples:
        calculate("2 + 2") -> {"result": 4}
        calculate("sqrt(16) * 3") -> {"result": 12.0}
    """
    try:
        # Safe evaluation - only allow math operations
        allowed_names = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "pi": math.pi,
            "e": math.e,
        }

        # Evaluate expression safely
        result = eval(expression, {"__builtins__": {}}, allowed_names)

        return {
            "expression": expression,
            "result": result,
            "success": True
        }

    except Exception as e:
        return {
            "expression": expression,
            "error": str(e),
            "success": False
        }


@tool(
    name="convert_units",
    description="Convert between different units",
    timeout=2.0
)
async def convert_units(
    value: float,
    from_unit: str,
    to_unit: str
) -> dict[str, Any]:
    """
    Convert between units.

    Supported conversions:
    - Length: m, km, ft, mi
    - Temperature: C, F, K
    - Weight: kg, lb, oz

    Args:
        value: Value to convert
        from_unit: Source unit
        to_unit: Target unit

    Returns:
        Converted value
    """
    # Length conversions (to meters)
    length_to_meters = {
        "m": 1.0,
        "km": 1000.0,
        "ft": 0.3048,
        "mi": 1609.34
    }

    # Temperature conversions
    if from_unit == "C" and to_unit == "F":
        result = (value * 9/5) + 32
    elif from_unit == "F" and to_unit == "C":
        result = (value - 32) * 5/9
    elif from_unit == "C" and to_unit == "K":
        result = value + 273.15
    elif from_unit == "K" and to_unit == "C":
        result = value - 273.15
    # Length conversions
    elif from_unit in length_to_meters and to_unit in length_to_meters:
        meters = value * length_to_meters[from_unit]
        result = meters / length_to_meters[to_unit]
    else:
        return {
            "error": f"Conversion from {from_unit} to {to_unit} not supported",
            "success": False
        }

    return {
        "original_value": value,
        "original_unit": from_unit,
        "converted_value": result,
        "converted_unit": to_unit,
        "success": True
    }


# ============================================================================
# Web Search Tool (Simulated)
# ============================================================================


@tool(
    name="web_search",
    description="Search the web for information",
    timeout=10.0
)
async def web_search(
    query: str,
    max_results: int = 5
) -> dict[str, Any]:
    """
    Search the web for information.

    In production, integrate with:
    - Google Custom Search API
    - Bing Search API
    - DuckDuckGo API
    - SerpAPI

    Args:
        query: Search query
        max_results: Maximum number of results

    Returns:
        Search results
    """
    import asyncio
    await asyncio.sleep(0.5)  # Simulate API call

    # Simulated search results
    # In production, replace with actual API call
    query_lower = query.lower()

    if "python" in query_lower:
        results = [
            {
                "title": "Python Official Documentation",
                "url": "https://docs.python.org",
                "snippet": "The official Python documentation with tutorials and references."
            },
            {
                "title": "Real Python Tutorials",
                "url": "https://realpython.com",
                "snippet": "High-quality Python tutorials and articles."
            },
            {
                "title": "Python Package Index (PyPI)",
                "url": "https://pypi.org",
                "snippet": "The Python Package Index (PyPI) is a repository of software for Python."
            }
        ]
    elif "weather" in query_lower:
        results = [
            {
                "title": "Weather.com",
                "url": "https://weather.com",
                "snippet": "Get current weather forecasts and conditions."
            }
        ]
    else:
        results = [
            {
                "title": f"Search result for: {query}",
                "url": "https://example.com",
                "snippet": f"Information about {query}"
            }
        ]

    return {
        "query": query,
        "results": results[:max_results],
        "count": len(results[:max_results])
    }


# ============================================================================
# File Operations Tools
# ============================================================================


@tool(
    name="read_file",
    description="Read contents of a file",
    timeout=5.0
)
async def read_file(file_path: str) -> dict[str, Any]:
    """
    Read file contents.

    Args:
        file_path: Path to file

    Returns:
        File contents
    """
    try:
        # In production, add security checks and path validation
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "file_path": file_path,
            "content": content,
            "size": len(content),
            "success": True
        }

    except FileNotFoundError:
        return {
            "file_path": file_path,
            "error": "File not found",
            "success": False
        }
    except Exception as e:
        return {
            "file_path": file_path,
            "error": str(e),
            "success": False
        }


@confirmed_tool(
    name="write_file",
    description="Write content to a file (requires confirmation)",
    timeout=5.0
)
async def write_file(
    file_path: str,
    content: str,
    mode: str = "w"
) -> dict[str, Any]:
    """
    Write content to a file.

    This tool requires confirmation because it modifies the filesystem.

    Args:
        file_path: Path to file
        content: Content to write
        mode: Write mode ('w' for overwrite, 'a' for append)

    Returns:
        Write result
    """
    try:
        # In production, add security checks and path validation
        with open(file_path, mode, encoding="utf-8") as f:
            f.write(content)

        return {
            "file_path": file_path,
            "mode": mode,
            "bytes_written": len(content),
            "success": True
        }

    except Exception as e:
        return {
            "file_path": file_path,
            "error": str(e),
            "success": False
        }


# ============================================================================
# Data Processing Tools
# ============================================================================


@tool(
    name="parse_json",
    description="Parse JSON string into structured data",
    timeout=3.0
)
async def parse_json(json_string: str) -> dict[str, Any]:
    """
    Parse JSON string.

    Args:
        json_string: JSON string to parse

    Returns:
        Parsed data
    """
    try:
        data = json.loads(json_string)
        return {
            "data": data,
            "type": type(data).__name__,
            "success": True
        }
    except json.JSONDecodeError as e:
        return {
            "error": str(e),
            "success": False
        }


@tool(
    name="format_json",
    description="Format data as pretty JSON",
    timeout=3.0
)
async def format_json(data: dict) -> dict[str, Any]:
    """
    Format dictionary as pretty JSON.

    Args:
        data: Dictionary to format

    Returns:
        Formatted JSON string
    """
    try:
        formatted = json.dumps(data, indent=2, sort_keys=True)
        return {
            "formatted": formatted,
            "success": True
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }


@tool(
    name="extract_data",
    description="Extract specific fields from data",
    timeout=3.0
)
async def extract_data(
    data: dict,
    fields: list[str]
) -> dict[str, Any]:
    """
    Extract specific fields from nested data.

    Args:
        data: Source data
        fields: List of field paths (e.g., ["name", "address.city"])

    Returns:
        Extracted data
    """
    extracted = {}

    for field in fields:
        # Support nested field access with dot notation
        parts = field.split(".")
        value = data

        try:
            for part in parts:
                if isinstance(value, dict):
                    value = value[part]
                else:
                    value = None
                    break

            extracted[field] = value

        except (KeyError, TypeError):
            extracted[field] = None

    return {
        "extracted": extracted,
        "fields_found": sum(1 for v in extracted.values() if v is not None),
        "success": True
    }


# ============================================================================
# HTTP Request Tool
# ============================================================================


@tool(
    name="http_request",
    description="Make HTTP GET request to a URL",
    timeout=30.0
)
async def http_request(
    url: str,
    headers: dict | None = None
) -> dict[str, Any]:
    """
    Make HTTP GET request.

    In production, use httpx for real requests.

    Args:
        url: URL to request
        headers: Optional HTTP headers

    Returns:
        Response data
    """
    import asyncio
    await asyncio.sleep(0.3)  # Simulate request

    # Simulated response
    # In production:
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     response = await client.get(url, headers=headers)
    #     return {
    #         "status_code": response.status_code,
    #         "content": response.text,
    #         "headers": dict(response.headers)
    #     }

    return {
        "url": url,
        "status_code": 200,
        "content": f"Simulated response from {url}",
        "simulated": True,
        "success": True
    }


# ============================================================================
# Date/Time Tools
# ============================================================================


@tool(
    name="get_current_time",
    description="Get current date and time",
    timeout=1.0
)
async def get_current_time(timezone: str = "UTC") -> dict[str, Any]:
    """
    Get current date and time.

    Args:
        timezone: Timezone (default: UTC)

    Returns:
        Current time information
    """
    from datetime import datetime

    now = datetime.utcnow()

    return {
        "datetime": now.isoformat(),
        "date": now.date().isoformat(),
        "time": now.time().isoformat(),
        "timestamp": now.timestamp(),
        "timezone": timezone,
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "hour": now.hour,
        "minute": now.minute,
        "second": now.second
    }


@tool(
    name="format_date",
    description="Format date into readable string",
    timeout=2.0
)
async def format_date(
    date_string: str,
    format: str = "%Y-%m-%d"
) -> dict[str, Any]:
    """
    Format date string.

    Args:
        date_string: ISO date string
        format: Output format (strftime format)

    Returns:
        Formatted date
    """
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(date_string)
        formatted = dt.strftime(format)

        return {
            "original": date_string,
            "formatted": formatted,
            "format": format,
            "success": True
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }


# ============================================================================
# Production API Integration Examples
# ============================================================================


async def setup_google_search():
    """
    Example: Google Custom Search API integration.

    Setup:
    1. Get API key: https://developers.google.com/custom-search
    2. Create search engine ID
    3. pip install google-api-python-client

    ```python
    from googleapiclient.discovery import build

    @tool(name="google_search")
    async def google_search(query: str, max_results: int = 5):
        api_key = await ctx.get_secret("GOOGLE_API_KEY")
        search_engine_id = await ctx.get_secret("GOOGLE_SEARCH_ENGINE_ID")

        service = build("customsearch", "v1", developerKey=api_key)
        result = service.cse().list(q=query, cx=search_engine_id, num=max_results).execute()

        return {
            "results": [
                {
                    "title": item["title"],
                    "url": item["link"],
                    "snippet": item.get("snippet", "")
                }
                for item in result.get("items", [])
            ]
        }
    ```
    """
    pass


async def setup_weather_api():
    """
    Example: OpenWeatherMap API integration.

    Setup:
    1. Get API key: https://openweathermap.org/api
    2. pip install httpx

    ```python
    import httpx

    @tool(name="get_weather")
    async def get_weather(city: str, country_code: str = "US"):
        api_key = await ctx.get_secret("OPENWEATHER_API_KEY")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": f"{city},{country_code}",
                    "appid": api_key,
                    "units": "metric"
                }
            )

            data = response.json()
            return {
                "temperature": data["main"]["temp"],
                "description": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"]
            }
    ```
    """
    pass

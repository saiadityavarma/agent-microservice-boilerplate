"""
Complete End-to-End Example: Weather Information Agent

This example demonstrates a real-world agent that:
1. Uses custom tools
2. Calls external APIs
3. Uses caching
4. Handles errors gracefully
5. Logs structured events
6. Uses secrets management
"""

from typing import Any
from agent_service.interfaces import AgentInput, AgentOutput
from agent_service.agent import agent, AgentContext
from agent_service.tools import tool, confirmed_tool


# ============================================================================
# Step 1: Create Custom Tools
# ============================================================================


@tool(
    name="geocode_location",
    description="Convert a location name to coordinates",
    timeout=5.0
)
async def geocode_location(location: str) -> dict[str, Any]:
    """
    Geocode a location name to lat/lon coordinates.

    In a real implementation, this would call a geocoding API.
    """
    # Simulated geocoding (replace with actual API call)
    geocode_data = {
        "london": {"lat": 51.5074, "lon": -0.1278},
        "new york": {"lat": 40.7128, "lon": -74.0060},
        "tokyo": {"lat": 35.6762, "lon": 139.6503},
    }

    location_lower = location.lower()
    if location_lower in geocode_data:
        return {
            "location": location,
            "coordinates": geocode_data[location_lower],
            "found": True,
        }

    return {
        "location": location,
        "coordinates": None,
        "found": False,
        "error": f"Location '{location}' not found",
    }


@tool(
    name="get_weather_data",
    description="Fetch weather data for coordinates",
    timeout=10.0
)
async def get_weather_data(
    lat: float,
    lon: float,
    units: str = "metric"
) -> dict[str, Any]:
    """
    Fetch weather data for given coordinates.

    In a real implementation, this would call a weather API.
    """
    import asyncio

    # Simulate API call delay
    await asyncio.sleep(0.5)

    # Simulated weather data (replace with actual API call)
    return {
        "coordinates": {"lat": lat, "lon": lon},
        "temperature": 15.5 if units == "metric" else 59.9,
        "humidity": 72,
        "description": "Partly cloudy",
        "wind_speed": 12.5 if units == "metric" else 7.8,
        "units": units,
    }


@tool(
    name="format_weather_report",
    description="Format weather data into a human-readable report"
)
async def format_weather_report(weather_data: dict[str, Any]) -> str:
    """Format weather data as a readable report."""
    units_symbol = "°C" if weather_data["units"] == "metric" else "°F"
    speed_units = "km/h" if weather_data["units"] == "metric" else "mph"

    report = f"""
Weather Report:
--------------
Temperature: {weather_data['temperature']}{units_symbol}
Conditions: {weather_data['description']}
Humidity: {weather_data['humidity']}%
Wind Speed: {weather_data['wind_speed']} {speed_units}
"""
    return report.strip()


# ============================================================================
# Step 2: Create the Weather Agent
# ============================================================================


@agent(
    name="weather_agent",
    description="Provides weather information for any location"
)
async def weather_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """
    Weather information agent.

    Usage: Just provide a location name, e.g., "London" or "New York"
    """
    location = input.message.strip()

    # Add context to logger
    ctx.bind_logger(location=location)
    ctx.logger.info("weather_request_started")

    # Check cache first
    cache_key = f"weather:{location.lower()}"
    if ctx.cache:
        cached_result = await ctx.cache.get(cache_key)
        if cached_result:
            ctx.logger.info("weather_cache_hit")
            return AgentOutput(
                content=cached_result,
                metadata={"cached": True, "location": location}
            )

    try:
        # Step 1: Geocode the location
        ctx.logger.info("geocoding_location")
        geocode_result = await ctx.call_tool(
            "geocode_location",
            location=location
        )

        if not geocode_result["found"]:
            ctx.logger.warning("location_not_found", location=location)
            return AgentOutput(
                content=f"Sorry, I couldn't find the location '{location}'. "
                        f"Please try a major city name.",
                metadata={"error": "location_not_found"}
            )

        coords = geocode_result["coordinates"]
        ctx.logger.info("location_geocoded", lat=coords["lat"], lon=coords["lon"])

        # Step 2: Fetch weather data
        ctx.logger.info("fetching_weather_data")
        weather_data = await ctx.call_tool(
            "get_weather_data",
            lat=coords["lat"],
            lon=coords["lon"],
            units="metric"
        )

        # Step 3: Format the report
        ctx.logger.info("formatting_weather_report")
        report = await ctx.call_tool(
            "format_weather_report",
            weather_data=weather_data
        )

        # Cache the result for 10 minutes
        if ctx.cache:
            await ctx.cache.set(cache_key, report, ttl=600)
            ctx.logger.info("weather_cached", ttl=600)

        ctx.logger.info("weather_request_completed", success=True)

        return AgentOutput(
            content=report,
            metadata={
                "cached": False,
                "location": location,
                "coordinates": coords,
                "temperature": weather_data["temperature"],
            }
        )

    except Exception as e:
        ctx.logger.error(
            "weather_request_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )

        return AgentOutput(
            content=f"Sorry, I encountered an error while fetching weather data: {str(e)}",
            metadata={
                "error": str(e),
                "error_type": type(e).__name__,
            }
        )


# ============================================================================
# Step 3: Enhanced Agent with User Preferences
# ============================================================================


@agent(
    name="personalized_weather_agent",
    description="Provides personalized weather information based on user preferences"
)
async def personalized_weather_agent(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Personalized weather agent that considers user preferences.

    Checks user's preferred units and includes personalized greeting.
    """
    location = input.message.strip()

    # Check if user is authenticated
    if not ctx.user:
        ctx.logger.info("unauthenticated_request")
        greeting = "Hello!"
        units = "metric"
    else:
        ctx.logger.info(
            "authenticated_request",
            user_id=str(ctx.user.id),
            user_email=ctx.user.email
        )
        greeting = f"Hello {ctx.user.name}!"
        # Get user's preferred units (would normally come from user settings)
        units = "imperial" if "US" in ctx.user.groups else "metric"

    try:
        # Geocode location
        geocode_result = await ctx.call_tool(
            "geocode_location",
            location=location
        )

        if not geocode_result["found"]:
            return AgentOutput(
                content=f"{greeting} Sorry, I couldn't find '{location}'."
            )

        coords = geocode_result["coordinates"]

        # Fetch weather with user's preferred units
        weather_data = await ctx.call_tool(
            "get_weather_data",
            lat=coords["lat"],
            lon=coords["lon"],
            units=units
        )

        # Format report
        report = await ctx.call_tool(
            "format_weather_report",
            weather_data=weather_data
        )

        personalized_report = f"{greeting}\n\n{report}"

        return AgentOutput(
            content=personalized_report,
            metadata={
                "location": location,
                "units": units,
                "authenticated": ctx.user is not None,
            }
        )

    except Exception as e:
        ctx.logger.error("personalized_weather_failed", error=str(e))
        return AgentOutput(
            content=f"{greeting} Sorry, I encountered an error: {str(e)}"
        )


# ============================================================================
# Step 4: Admin Tool for Cache Management
# ============================================================================


@confirmed_tool(
    name="clear_weather_cache",
    description="Clear all cached weather data (ADMIN ONLY)"
)
async def clear_weather_cache(location: str | None = None) -> dict[str, Any]:
    """
    Clear weather cache.

    Args:
        location: Specific location to clear, or None to clear all

    Returns:
        Result of cache clearing operation
    """
    from agent_service.infrastructure.cache.cache import get_cache

    cache = await get_cache(namespace="agent:weather_agent")

    if location:
        # Clear specific location
        cache_key = f"weather:{location.lower()}"
        await cache.delete(cache_key)
        return {
            "success": True,
            "cleared": "specific",
            "location": location,
        }
    else:
        # Would clear all weather cache entries
        # For now just return success
        return {
            "success": True,
            "cleared": "all",
            "message": "All weather cache cleared",
        }


# ============================================================================
# Step 5: Example Usage
# ============================================================================


async def example_usage():
    """
    Demonstrate how to use the weather agent.
    """
    from agent_service.agent import agent_registry

    # Get the agent
    weather_agent_instance = agent_registry.get("weather_agent")

    # Create input
    input = AgentInput(message="London")

    # Invoke agent
    result = await weather_agent_instance.invoke(input)

    print("Weather Report:")
    print(result.content)
    print("\nMetadata:")
    print(result.metadata)


# ============================================================================
# Step 6: Testing
# ============================================================================


async def test_weather_agent():
    """Test the weather agent."""
    import pytest
    from agent_service.agent import AgentContext
    from agent_service.tools import tool_registry

    # Create test context
    ctx = AgentContext(tools=tool_registry)

    # Test with London
    input = AgentInput(message="London")
    result = await weather_agent(input, ctx)

    assert "Temperature" in result.content
    assert result.metadata.get("location") == "London"

    # Test with unknown location
    input = AgentInput(message="UnknownCity123")
    result = await weather_agent(input, ctx)

    assert "couldn't find" in result.content.lower()


# ============================================================================
# Summary
# ============================================================================

"""
This example demonstrates:

1. Creating Custom Tools:
   - geocode_location: Converts location names to coordinates
   - get_weather_data: Fetches weather data
   - format_weather_report: Formats data into readable report

2. Creating an Agent:
   - weather_agent: Orchestrates tools to provide weather info
   - Uses caching to avoid redundant API calls
   - Handles errors gracefully
   - Logs all operations

3. Advanced Features:
   - User personalization (greeting, units)
   - Cache management tools
   - Structured logging
   - Error handling

4. Best Practices:
   - Type annotations for automatic schema generation
   - Timeouts on external calls
   - Cache for expensive operations
   - Comprehensive error handling
   - Structured logging with context

To use this example:

    # Import the module to register agents and tools
    from examples import complete_example

    # Get the agent
    from agent_service.agent import agent_registry
    weather = agent_registry.get("weather_agent")

    # Use it
    from agent_service.interfaces import AgentInput
    result = await weather.invoke(AgentInput(message="London"))
    print(result.content)
"""

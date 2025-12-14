"""
Framework integration helpers for common agent frameworks.

This module provides adapters and decorators for integrating popular agent
frameworks (LangGraph, CrewAI, OpenAI) with the IAgent interface.

All integrations gracefully handle missing dependencies and will warn if
the required package is not installed.

Examples:
    LangGraph integration:
        >>> from agent_service.agent.integrations import langgraph_agent
        >>> @langgraph_agent(graph=my_graph, name="lg_agent")
        ... class MyAgent(IAgent):
        ...     pass

    CrewAI integration:
        >>> from agent_service.agent.integrations import crewai_agent
        >>> @crewai_agent(crew=my_crew, name="crew_agent")
        ... class MyAgent(IAgent):
        ...     pass

    OpenAI integration:
        >>> from agent_service.agent.integrations import openai_agent
        >>> @openai_agent(model="gpt-4", tools=[...], name="oai_agent")
        ... class MyAgent(IAgent):
        ...     pass
"""

from __future__ import annotations

# Import with graceful degradation
try:
    from agent_service.agent.integrations.langgraph import (
        LangGraphAgent,
        langgraph_agent,
        LANGGRAPH_AVAILABLE,
    )
except ImportError:
    LangGraphAgent = None
    langgraph_agent = None
    LANGGRAPH_AVAILABLE = False

try:
    from agent_service.agent.integrations.crewai import (
        CrewAIAgent,
        crewai_agent,
        CREWAI_AVAILABLE,
    )
except ImportError:
    CrewAIAgent = None
    crewai_agent = None
    CREWAI_AVAILABLE = False

try:
    from agent_service.agent.integrations.openai_functions import (
        OpenAIFunctionAgent,
        openai_agent,
        tool_to_openai_format,
        OPENAI_AVAILABLE,
    )
except ImportError:
    OpenAIFunctionAgent = None
    openai_agent = None
    tool_to_openai_format = None
    OPENAI_AVAILABLE = False


__all__ = [
    # LangGraph
    "LangGraphAgent",
    "langgraph_agent",
    "LANGGRAPH_AVAILABLE",
    # CrewAI
    "CrewAIAgent",
    "crewai_agent",
    "CREWAI_AVAILABLE",
    # OpenAI
    "OpenAIFunctionAgent",
    "openai_agent",
    "tool_to_openai_format",
    "OPENAI_AVAILABLE",
]


def check_integrations() -> dict[str, bool]:
    """
    Check which integrations are available.

    Returns:
        Dict mapping integration name to availability status
    """
    return {
        "langgraph": LANGGRAPH_AVAILABLE,
        "crewai": CREWAI_AVAILABLE,
        "openai": OPENAI_AVAILABLE,
    }


def get_missing_integrations() -> list[str]:
    """
    Get list of missing integration dependencies.

    Returns:
        List of integration names that are not available
    """
    status = check_integrations()
    return [name for name, available in status.items() if not available]


def print_integration_status() -> None:
    """
    Print the status of all integrations to console.
    """
    status = check_integrations()
    print("Agent Framework Integration Status:")
    print("-" * 40)
    for name, available in status.items():
        status_str = "✓ Available" if available else "✗ Not installed"
        print(f"  {name:.<20} {status_str}")
    print("-" * 40)

    missing = get_missing_integrations()
    if missing:
        print("\nTo install missing integrations:")
        for name in missing:
            print(f"  pip install {name}")

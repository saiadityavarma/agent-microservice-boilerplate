"""
Protocol handler implementations.

This module provides protocol handlers for MCP, A2A, and AGUI protocols,
along with a registry for managing protocol handlers.

Available protocols:
- MCP (Model Context Protocol): For exposing agent tools and resources
- A2A (Agent-to-Agent): For agent communication
- AGUI (Agent UI): For agent user interfaces

Usage:
    from agent_service.protocols import get_protocol_registry

    registry = get_protocol_registry()
    handler = registry.get_handler("mcp")
"""
from agent_service.protocols.registry import (
    ProtocolRegistry,
    get_protocol_registry,
    protocol_registry
)

__all__ = [
    "ProtocolRegistry",
    "get_protocol_registry",
    "protocol_registry"
]

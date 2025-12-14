# src/agent_service/protocols/registry.py
from agent_service.interfaces import IProtocolHandler, ProtocolType
from agent_service.config.settings import get_settings


class ProtocolRegistry:
    """Registry for protocol handlers."""

    def __init__(self):
        self._handlers: dict[ProtocolType, IProtocolHandler] = {}

    def register(self, protocol_name: str, handler: IProtocolHandler) -> None:
        """
        Register a protocol handler.

        Args:
            protocol_name: Name of the protocol (mcp, a2a, agui)
            handler: Protocol handler implementation
        """
        self._handlers[handler.protocol_type] = handler

    def get_handler(self, protocol_name: str) -> IProtocolHandler | None:
        """
        Get handler by protocol name.

        Args:
            protocol_name: Name of the protocol (mcp, a2a, agui)

        Returns:
            Protocol handler or None if not found
        """
        try:
            protocol_type = ProtocolType(protocol_name.lower())
            return self._handlers.get(protocol_type)
        except ValueError:
            return None

    def get(self, protocol: ProtocolType) -> IProtocolHandler | None:
        """Get handler by protocol type (backward compatibility)."""
        return self._handlers.get(protocol)

    def list_protocols(self) -> list[str]:
        """
        List all registered protocol names.

        Returns:
            List of protocol names
        """
        return [protocol.value for protocol in self._handlers.keys()]

    def is_registered(self, protocol_name: str) -> bool:
        """
        Check if a protocol is registered.

        Args:
            protocol_name: Name of the protocol

        Returns:
            True if protocol is registered, False otherwise
        """
        try:
            protocol_type = ProtocolType(protocol_name.lower())
            return protocol_type in self._handlers
        except ValueError:
            return False

    def all(self) -> list[IProtocolHandler]:
        """Get all registered handlers."""
        return list(self._handlers.values())

    def auto_register(self) -> None:
        """
        Auto-register protocol handlers based on settings.

        Registers handlers for enabled protocols (enable_mcp, enable_a2a, enable_agui).
        """
        settings = get_settings()

        if settings.enable_mcp:
            try:
                from agent_service.protocols.mcp.handler import MCPHandler
                handler = MCPHandler()
                self.register("mcp", handler)
                print("MCP protocol handler registered")
            except ImportError as e:
                print(f"Failed to register MCP handler: {e}")

        if settings.enable_a2a:
            try:
                from agent_service.protocols.a2a.handler import A2AHandler
                handler = A2AHandler()
                self.register("a2a", handler)
                print("A2A protocol handler registered")
            except (ImportError, NotImplementedError) as e:
                print(f"Failed to register A2A handler: {e}")

        if settings.enable_agui:
            try:
                from agent_service.protocols.agui.handler import AGUIHandler
                handler = AGUIHandler()
                self.register("agui", handler)
                print("AGUI protocol handler registered")
            except (ImportError, NotImplementedError) as e:
                print(f"Failed to register AGUI handler: {e}")


# Global registry
_protocol_registry: ProtocolRegistry | None = None


def get_protocol_registry() -> ProtocolRegistry:
    """
    Get the global protocol registry instance.

    Returns:
        Global ProtocolRegistry instance
    """
    global _protocol_registry
    if _protocol_registry is None:
        _protocol_registry = ProtocolRegistry()
        _protocol_registry.auto_register()
    return _protocol_registry


# Backward compatibility
protocol_registry = get_protocol_registry()

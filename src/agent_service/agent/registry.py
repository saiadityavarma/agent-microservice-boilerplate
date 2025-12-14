"""
Agent registry for managing agent instances.

Supports both class-based agents (IAgent implementations) and
decorator-based agents created with @agent decorator.
"""
from agent_service.interfaces import IAgent


class AgentRegistry:
    """
    Registry for agent implementations.

    Supports:
    - Class-based agents (implement IAgent)
    - Decorator-based agents (use @agent decorator)

    Example:
        >>> # Class-based registration
        >>> registry.register(MyAgent())
        >>>
        >>> # Decorator-based (auto-registered)
        >>> @agent(name="my_agent")
        >>> async def my_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
        ...     return AgentOutput(content="Hello")
        >>>
        >>> # Retrieve agent
        >>> agent = registry.get("my_agent")
    """

    def __init__(self):
        self._agents: dict[str, IAgent] = {}
        self._default: str | None = None

    def register(self, agent: IAgent, default: bool = False) -> None:
        """
        Register an agent.

        Args:
            agent: Agent instance (IAgent implementation)
            default: Set as default agent (default: False)

        Example:
            >>> registry.register(MyAgent(), default=True)
        """
        self._agents[agent.name] = agent
        if default or self._default is None:
            self._default = agent.name

    def unregister(self, name: str) -> None:
        """
        Unregister an agent by name.

        Args:
            name: Agent name to unregister

        Example:
            >>> registry.unregister("my_agent")
        """
        if name in self._agents:
            del self._agents[name]
            if self._default == name:
                # Reset default to first available agent
                self._default = next(iter(self._agents.keys()), None)

    def get(self, name: str) -> IAgent | None:
        """
        Get an agent by name.

        Args:
            name: Agent name

        Returns:
            Agent instance or None if not found

        Example:
            >>> agent = registry.get("my_agent")
        """
        return self._agents.get(name)

    def get_default(self) -> IAgent | None:
        """
        Get the default agent.

        Returns:
            Default agent instance or None if no agents registered

        Example:
            >>> agent = registry.get_default()
        """
        if self._default:
            return self._agents.get(self._default)
        return None

    def set_default(self, name: str) -> None:
        """
        Set the default agent.

        Args:
            name: Agent name to set as default

        Raises:
            ValueError: If agent not found

        Example:
            >>> registry.set_default("my_agent")
        """
        if name not in self._agents:
            raise ValueError(f"Agent not found: {name}")
        self._default = name

    def list_agents(self) -> list[str]:
        """
        List all registered agent names.

        Returns:
            List of agent names

        Example:
            >>> names = registry.list_agents()
            >>> print(names)
            ['agent1', 'agent2', 'agent3']
        """
        return list(self._agents.keys())

    def list_agents_with_details(self) -> list[dict[str, str]]:
        """
        List all agents with their details.

        Returns:
            List of agent info dictionaries

        Example:
            >>> agents = registry.list_agents_with_details()
            >>> for agent in agents:
            ...     print(f"{agent['name']}: {agent['description']}")
        """
        return [
            {
                "name": agent.name,
                "description": agent.description,
                "is_default": agent.name == self._default,
            }
            for agent in self._agents.values()
        ]

    def clear(self) -> None:
        """
        Clear all registered agents.

        Example:
            >>> registry.clear()
        """
        self._agents.clear()
        self._default = None


# Global registry
agent_registry = AgentRegistry()


def get_default_agent() -> IAgent:
    """
    FastAPI dependency to get default agent.

    Returns:
        Default agent instance

    Raises:
        RuntimeError: If no agent registered

    Example:
        >>> @app.get("/chat")
        >>> async def chat(agent: IAgent = Depends(get_default_agent)):
        ...     result = await agent.invoke(AgentInput(message="Hello"))
    """
    agent = agent_registry.get_default()
    if not agent:
        raise RuntimeError("No agent registered")
    return agent

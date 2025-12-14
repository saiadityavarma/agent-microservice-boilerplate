"""
LangGraph integration adapter.

Wraps LangGraph StateGraph as IAgent with streaming support.
Gracefully handles missing langgraph dependency.
"""

from __future__ import annotations
from typing import Any, AsyncGenerator, Callable, TYPE_CHECKING
from functools import wraps
import warnings

from agent_service.interfaces.agent import IAgent, AgentInput, AgentOutput, StreamChunk
from agent_service.agent.config import AgentConfig, get_config

if TYPE_CHECKING:
    try:
        from langgraph.graph import CompiledGraph
    except ImportError:
        CompiledGraph = Any

# Check if langgraph is available
try:
    from langgraph.graph import CompiledGraph as _CompiledGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    _CompiledGraph = None


class LangGraphAgent(IAgent):
    """
    Adapter that wraps a LangGraph CompiledGraph as an IAgent.

    Handles state mapping between LangGraph and AgentInput/AgentOutput.
    """

    def __init__(
        self,
        graph: Any,  # CompiledGraph
        name: str,
        description: str = "LangGraph agent",
        config: AgentConfig | None = None,
        input_mapper: Callable[[AgentInput], dict[str, Any]] | None = None,
        output_mapper: Callable[[dict[str, Any]], AgentOutput] | None = None,
    ):
        """
        Initialize LangGraph agent adapter.

        Args:
            graph: Compiled LangGraph StateGraph
            name: Agent name
            description: Agent description
            config: Agent configuration
            input_mapper: Function to map AgentInput to LangGraph state
            output_mapper: Function to map LangGraph state to AgentOutput
        """
        if not LANGGRAPH_AVAILABLE:
            raise ImportError(
                "langgraph is not installed. Install it with: pip install langgraph"
            )

        self._graph = graph
        self._name = name
        self._description = description
        self._config = config or get_config(name)
        self._input_mapper = input_mapper or self._default_input_mapper
        self._output_mapper = output_mapper or self._default_output_mapper

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @staticmethod
    def _default_input_mapper(input: AgentInput) -> dict[str, Any]:
        """
        Default mapping from AgentInput to LangGraph state.

        Creates a state with:
        - messages: List containing the user message
        - session_id: Session identifier
        - context: Additional context
        """
        return {
            "messages": [{"role": "user", "content": input.message}],
            "session_id": input.session_id,
            **(input.context or {}),
        }

    @staticmethod
    def _default_output_mapper(state: dict[str, Any]) -> AgentOutput:
        """
        Default mapping from LangGraph state to AgentOutput.

        Extracts:
        - Last message content as output content
        - Tool calls if present
        - Additional state as metadata
        """
        messages = state.get("messages", [])
        if not messages:
            return AgentOutput(content="", metadata=state)

        last_message = messages[-1]
        if isinstance(last_message, dict):
            content = last_message.get("content", "")
            tool_calls = last_message.get("tool_calls")
        else:
            # Handle LangChain message objects
            content = getattr(last_message, "content", str(last_message))
            tool_calls = getattr(last_message, "tool_calls", None)

        # Extract metadata (exclude messages to avoid duplication)
        metadata = {k: v for k, v in state.items() if k != "messages"}

        return AgentOutput(
            content=str(content),
            tool_calls=tool_calls,
            metadata=metadata if metadata else None,
        )

    async def invoke(self, input: AgentInput) -> AgentOutput:
        """
        Execute LangGraph synchronously.

        Args:
            input: Agent input

        Returns:
            Agent output
        """
        state = self._input_mapper(input)

        # Use ainvoke if available, otherwise invoke
        if hasattr(self._graph, "ainvoke"):
            result = await self._graph.ainvoke(
                state,
                config={"recursion_limit": 50},
            )
        else:
            # Fallback to sync invoke (not ideal but supported)
            result = self._graph.invoke(
                state,
                config={"recursion_limit": 50},
            )

        return self._output_mapper(result)

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """
        Execute LangGraph with streaming output.

        Args:
            input: Agent input

        Yields:
            StreamChunk for each state update
        """
        state = self._input_mapper(input)

        # Use astream if available
        if hasattr(self._graph, "astream"):
            stream = self._graph.astream(
                state,
                config={"recursion_limit": 50},
            )

            async for chunk in stream:
                # LangGraph yields state updates
                yield self._process_stream_chunk(chunk)
        else:
            # Fallback to sync stream
            warnings.warn("LangGraph sync streaming not fully supported, using invoke")
            result = await self.invoke(input)
            yield StreamChunk(type="text", content=result.content, metadata=result.metadata)

    def _process_stream_chunk(self, chunk: dict[str, Any]) -> StreamChunk:
        """
        Process a LangGraph stream chunk into StreamChunk.

        Args:
            chunk: LangGraph state update

        Returns:
            StreamChunk
        """
        # Extract the node that was updated
        if len(chunk) == 1:
            node_name = list(chunk.keys())[0]
            node_state = chunk[node_name]

            # Check if this is a message update
            if "messages" in node_state:
                messages = node_state["messages"]
                if messages:
                    last_message = messages[-1]
                    if isinstance(last_message, dict):
                        content = last_message.get("content", "")
                    else:
                        content = getattr(last_message, "content", "")

                    return StreamChunk(
                        type="text",
                        content=str(content),
                        metadata={"node": node_name},
                    )

        # Generic state update
        return StreamChunk(
            type="text",
            content="",
            metadata=chunk,
        )


def langgraph_agent(
    graph: Any,  # CompiledGraph
    name: str,
    description: str = "LangGraph agent",
    config: AgentConfig | None = None,
    input_mapper: Callable[[AgentInput], dict[str, Any]] | None = None,
    output_mapper: Callable[[dict[str, Any]], AgentOutput] | None = None,
):
    """
    Decorator to wrap a LangGraph StateGraph as an IAgent.

    Usage:
        @langgraph_agent(graph=my_compiled_graph, name="lg_agent")
        class MyLangGraphAgent(IAgent):
            pass

    Args:
        graph: Compiled LangGraph StateGraph
        name: Agent name
        description: Agent description
        config: Agent configuration
        input_mapper: Custom AgentInput -> LangGraph state mapper
        output_mapper: Custom LangGraph state -> AgentOutput mapper

    Returns:
        Decorated class that is a LangGraphAgent instance
    """
    def decorator(cls):
        if not LANGGRAPH_AVAILABLE:
            warnings.warn(
                f"LangGraph not available for agent {name}. "
                "Install with: pip install langgraph"
            )
            # Return original class so it doesn't break
            return cls

        @wraps(cls)
        def wrapper(*args, **kwargs):
            # Ignore the class entirely and return our adapter
            return LangGraphAgent(
                graph=graph,
                name=name,
                description=description,
                config=config,
                input_mapper=input_mapper,
                output_mapper=output_mapper,
            )

        # Copy class metadata
        wrapper.__name__ = cls.__name__
        wrapper.__module__ = cls.__module__
        wrapper.__doc__ = cls.__doc__ or description
        wrapper.__qualname__ = cls.__qualname__

        return wrapper

    return decorator


__all__ = [
    "LangGraphAgent",
    "langgraph_agent",
    "LANGGRAPH_AVAILABLE",
]

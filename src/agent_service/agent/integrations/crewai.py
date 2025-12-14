"""
CrewAI integration adapter.

Wraps CrewAI Crew as IAgent with kickoff handling.
Gracefully handles missing crewai dependency.
"""

from __future__ import annotations
from typing import Any, AsyncGenerator, Callable, TYPE_CHECKING
from functools import wraps
import warnings
import asyncio

from agent_service.interfaces.agent import IAgent, AgentInput, AgentOutput, StreamChunk
from agent_service.agent.config import AgentConfig, get_config

if TYPE_CHECKING:
    try:
        from crewai import Crew
    except ImportError:
        Crew = Any

# Check if crewai is available
try:
    from crewai import Crew as _Crew
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    _Crew = None


class CrewAIAgent(IAgent):
    """
    Adapter that wraps a CrewAI Crew as an IAgent.

    Handles kickoff and result mapping between CrewAI and AgentInput/AgentOutput.
    """

    def __init__(
        self,
        crew: Any,  # Crew
        name: str,
        description: str = "CrewAI agent",
        config: AgentConfig | None = None,
        input_mapper: Callable[[AgentInput], dict[str, Any]] | None = None,
        output_mapper: Callable[[Any], AgentOutput] | None = None,
    ):
        """
        Initialize CrewAI agent adapter.

        Args:
            crew: CrewAI Crew instance
            name: Agent name
            description: Agent description
            config: Agent configuration
            input_mapper: Function to map AgentInput to crew kickoff inputs
            output_mapper: Function to map crew result to AgentOutput
        """
        if not CREWAI_AVAILABLE:
            raise ImportError(
                "crewai is not installed. Install it with: pip install crewai"
            )

        self._crew = crew
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
        Default mapping from AgentInput to CrewAI kickoff inputs.

        Creates inputs dict with:
        - message: The user message
        - session_id: Session identifier
        - Additional context fields
        """
        return {
            "message": input.message,
            "session_id": input.session_id,
            **(input.context or {}),
        }

    @staticmethod
    def _default_output_mapper(result: Any) -> AgentOutput:
        """
        Default mapping from CrewAI result to AgentOutput.

        Args:
            result: CrewAI kickoff result (can be string, dict, or CrewOutput)

        Returns:
            AgentOutput with parsed content
        """
        # Handle different CrewAI result types
        if isinstance(result, str):
            return AgentOutput(content=result)

        if isinstance(result, dict):
            # Extract common fields
            content = result.get("output") or result.get("result") or str(result)
            return AgentOutput(
                content=str(content),
                metadata={k: v for k, v in result.items() if k not in ("output", "result")},
            )

        # Handle CrewOutput object
        if hasattr(result, "raw"):
            content = result.raw
        elif hasattr(result, "output"):
            content = result.output
        else:
            content = str(result)

        # Extract metadata from result object
        metadata = {}
        if hasattr(result, "tasks_output"):
            metadata["tasks_output"] = result.tasks_output
        if hasattr(result, "token_usage"):
            metadata["token_usage"] = result.token_usage

        return AgentOutput(
            content=str(content),
            metadata=metadata if metadata else None,
        )

    async def invoke(self, input: AgentInput) -> AgentOutput:
        """
        Execute CrewAI crew synchronously.

        Args:
            input: Agent input

        Returns:
            Agent output
        """
        inputs = self._input_mapper(input)

        # CrewAI kickoff is typically sync, run in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._crew.kickoff(inputs=inputs),
        )

        return self._output_mapper(result)

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """
        Execute CrewAI crew with streaming output.

        Note: CrewAI doesn't natively support streaming, so this yields
        intermediate task results if available, then final result.

        Args:
            input: Agent input

        Yields:
            StreamChunk for crew execution
        """
        inputs = self._input_mapper(input)

        # Check if crew supports streaming kickoff
        if hasattr(self._crew, "kickoff_async"):
            # Async kickoff available (newer CrewAI versions)
            try:
                result = await self._crew.kickoff_async(inputs=inputs)
                output = self._output_mapper(result)
                yield StreamChunk(type="text", content=output.content, metadata=output.metadata)
                return
            except Exception as e:
                warnings.warn(f"CrewAI async kickoff failed: {e}, falling back to sync")

        # Fallback: Run sync kickoff in executor
        yield StreamChunk(type="text", content="", metadata={"status": "starting"})

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._crew.kickoff(inputs=inputs),
        )

        output = self._output_mapper(result)

        # Yield task outputs if available
        if output.metadata and "tasks_output" in output.metadata:
            for i, task_output in enumerate(output.metadata["tasks_output"]):
                yield StreamChunk(
                    type="text",
                    content=str(task_output),
                    metadata={"task_index": i},
                )

        # Yield final output
        yield StreamChunk(type="text", content=output.content, metadata={"status": "complete"})

    async def setup(self) -> None:
        """Initialize crew if needed."""
        # CrewAI crews are typically ready after instantiation
        pass

    async def teardown(self) -> None:
        """Cleanup crew resources."""
        # CrewAI doesn't require explicit cleanup
        pass


def crewai_agent(
    crew: Any,  # Crew
    name: str,
    description: str = "CrewAI agent",
    config: AgentConfig | None = None,
    input_mapper: Callable[[AgentInput], dict[str, Any]] | None = None,
    output_mapper: Callable[[Any], AgentOutput] | None = None,
):
    """
    Decorator to wrap a CrewAI Crew as an IAgent.

    Usage:
        @crewai_agent(crew=my_crew, name="crew_agent")
        class MyCrewAgent(IAgent):
            pass

    Args:
        crew: CrewAI Crew instance
        name: Agent name
        description: Agent description
        config: Agent configuration
        input_mapper: Custom AgentInput -> crew inputs mapper
        output_mapper: Custom crew result -> AgentOutput mapper

    Returns:
        Decorated class that is a CrewAIAgent instance
    """
    def decorator(cls):
        if not CREWAI_AVAILABLE:
            warnings.warn(
                f"CrewAI not available for agent {name}. "
                "Install with: pip install crewai"
            )
            # Return original class so it doesn't break
            return cls

        @wraps(cls)
        def wrapper(*args, **kwargs):
            # Ignore the class entirely and return our adapter
            return CrewAIAgent(
                crew=crew,
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
    "CrewAIAgent",
    "crewai_agent",
    "CREWAI_AVAILABLE",
]

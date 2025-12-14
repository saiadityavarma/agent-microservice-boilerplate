"""
OpenAI function calling integration.

Provides helpers for using OpenAI chat completions with function calling as IAgent.
Gracefully handles missing openai dependency.
"""

from __future__ import annotations
from typing import Any, AsyncGenerator, Callable, TYPE_CHECKING
from functools import wraps
import warnings
import json

from agent_service.interfaces.agent import IAgent, AgentInput, AgentOutput, StreamChunk
from agent_service.agent.config import AgentConfig, get_config

if TYPE_CHECKING:
    try:
        from openai import AsyncOpenAI
    except ImportError:
        AsyncOpenAI = Any

# Check if openai is available
try:
    from openai import AsyncOpenAI as _AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    _AsyncOpenAI = None


class OpenAIFunctionAgent(IAgent):
    """
    Agent implementation using OpenAI chat completions with function calling.

    Handles:
    - Converting tools to OpenAI function format
    - Automatic tool execution loop
    - Streaming responses
    """

    def __init__(
        self,
        name: str,
        model: str = "gpt-4",
        tools: list[dict[str, Any]] | None = None,
        tool_executors: dict[str, Callable] | None = None,
        description: str = "OpenAI function calling agent",
        config: AgentConfig | None = None,
        system_message: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        max_iterations: int = 10,
    ):
        """
        Initialize OpenAI function calling agent.

        Args:
            name: Agent name
            model: OpenAI model identifier (e.g., "gpt-4", "gpt-3.5-turbo")
            tools: List of tool definitions in OpenAI format
            tool_executors: Dict mapping tool names to callable executors
            description: Agent description
            config: Agent configuration
            system_message: System message for the agent
            api_key: OpenAI API key (defaults to env var OPENAI_API_KEY)
            base_url: Custom API base URL
            max_iterations: Maximum tool execution iterations
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai is not installed. Install it with: pip install openai"
            )

        self._name = name
        self._model = model
        self._tools = tools or []
        self._tool_executors = tool_executors or {}
        self._description = description
        self._config = config or get_config(name)
        self._system_message = system_message or "You are a helpful assistant."
        self._max_iterations = max_iterations

        # Initialize OpenAI client
        client_kwargs = {}
        if api_key:
            client_kwargs["api_key"] = api_key
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = _AsyncOpenAI(**client_kwargs)

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def _build_messages(self, input: AgentInput) -> list[dict[str, Any]]:
        """
        Build OpenAI messages from AgentInput.

        Args:
            input: Agent input

        Returns:
            List of OpenAI message dicts
        """
        messages = [
            {"role": "system", "content": self._system_message}
        ]

        # Add context messages if provided
        if input.context and "messages" in input.context:
            messages.extend(input.context["messages"])

        # Add current message
        messages.append({"role": "user", "content": input.message})

        return messages

    async def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if tool_name not in self._tool_executors:
            return {"error": f"Tool {tool_name} not found"}

        try:
            executor = self._tool_executors[tool_name]
            # Support both sync and async executors
            if asyncio.iscoroutinefunction(executor):
                result = await executor(**arguments)
            else:
                result = executor(**arguments)
            return result
        except Exception as e:
            return {"error": str(e)}

    async def invoke(self, input: AgentInput) -> AgentOutput:
        """
        Execute OpenAI agent with function calling.

        Args:
            input: Agent input

        Returns:
            Agent output
        """
        messages = self._build_messages(input)
        tool_calls_made = []

        for iteration in range(self._max_iterations):
            # Prepare API call parameters
            api_params = {
                "model": self._config.model or self._model,
                "messages": messages,
                "temperature": self._config.temperature,
                "max_tokens": self._config.max_tokens,
            }

            if self._tools:
                api_params["tools"] = self._tools
                api_params["tool_choice"] = "auto"

            # Make API call
            response = await self._client.chat.completions.create(**api_params)
            message = response.choices[0].message

            # Add assistant message to history
            messages.append(message.model_dump())

            # Check if tool calls were made
            if not message.tool_calls:
                # No more tool calls, return final response
                return AgentOutput(
                    content=message.content or "",
                    tool_calls=tool_calls_made if tool_calls_made else None,
                    metadata={
                        "model": response.model,
                        "usage": response.usage.model_dump() if response.usage else None,
                        "finish_reason": response.choices[0].finish_reason,
                    },
                )

            # Execute tool calls
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                # Execute tool
                result = await self._execute_tool(tool_name, arguments)

                # Record tool call
                tool_calls_made.append({
                    "name": tool_name,
                    "arguments": arguments,
                    "result": result,
                })

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

        # Max iterations reached
        return AgentOutput(
            content="Maximum iterations reached",
            tool_calls=tool_calls_made if tool_calls_made else None,
            metadata={"max_iterations_reached": True},
        )

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """
        Execute OpenAI agent with streaming.

        Args:
            input: Agent input

        Yields:
            StreamChunk for each piece of output
        """
        messages = self._build_messages(input)

        for iteration in range(self._max_iterations):
            # Prepare API call parameters
            api_params = {
                "model": self._config.model or self._model,
                "messages": messages,
                "temperature": self._config.temperature,
                "max_tokens": self._config.max_tokens,
                "stream": True,
            }

            if self._tools:
                api_params["tools"] = self._tools
                api_params["tool_choice"] = "auto"

            # Stream response
            stream = await self._client.chat.completions.create(**api_params)

            # Accumulate message for tool calls
            accumulated_message = {"role": "assistant", "content": ""}
            tool_calls_accum = []

            async for chunk in stream:
                delta = chunk.choices[0].delta

                # Stream content
                if delta.content:
                    accumulated_message["content"] += delta.content
                    yield StreamChunk(type="text", content=delta.content)

                # Accumulate tool calls
                if delta.tool_calls:
                    for tool_call_delta in delta.tool_calls:
                        idx = tool_call_delta.index

                        # Ensure we have enough slots
                        while len(tool_calls_accum) <= idx:
                            tool_calls_accum.append({
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            })

                        # Accumulate tool call data
                        if tool_call_delta.id:
                            tool_calls_accum[idx]["id"] = tool_call_delta.id
                        if tool_call_delta.function:
                            if tool_call_delta.function.name:
                                tool_calls_accum[idx]["function"]["name"] = tool_call_delta.function.name
                            if tool_call_delta.function.arguments:
                                tool_calls_accum[idx]["function"]["arguments"] += tool_call_delta.function.arguments

            # Add tool calls to accumulated message
            if tool_calls_accum:
                # Convert to proper format
                accumulated_message["tool_calls"] = []
                for tc in tool_calls_accum:
                    from openai.types.chat import ChatCompletionMessageToolCall
                    accumulated_message["tool_calls"].append(
                        ChatCompletionMessageToolCall(
                            id=tc["id"],
                            type=tc["type"],
                            function=tc["function"],
                        )
                    )

            messages.append(accumulated_message)

            # Check if tool calls were made
            if not tool_calls_accum:
                # No tool calls, we're done
                break

            # Execute tool calls
            for tool_call in tool_calls_accum:
                tool_name = tool_call["function"]["name"]
                try:
                    arguments = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    arguments = {}

                yield StreamChunk(
                    type="tool_start",
                    content=f"Calling {tool_name}",
                    metadata={"tool": tool_name, "arguments": arguments},
                )

                # Execute tool
                result = await self._execute_tool(tool_name, arguments)

                yield StreamChunk(
                    type="tool_end",
                    content=f"Completed {tool_name}",
                    metadata={"tool": tool_name, "result": result},
                )

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result),
                })


import asyncio


def openai_agent(
    name: str,
    model: str = "gpt-4",
    tools: list[dict[str, Any]] | None = None,
    tool_executors: dict[str, Callable] | None = None,
    description: str = "OpenAI function calling agent",
    config: AgentConfig | None = None,
    system_message: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    max_iterations: int = 10,
):
    """
    Decorator to create an OpenAI function calling agent.

    Usage:
        @openai_agent(model="gpt-4", tools=[...], name="oai_agent")
        class MyOpenAIAgent(IAgent):
            pass

    Args:
        name: Agent name
        model: OpenAI model identifier
        tools: List of tool definitions in OpenAI format
        tool_executors: Dict mapping tool names to callable executors
        description: Agent description
        config: Agent configuration
        system_message: System message for the agent
        api_key: OpenAI API key
        base_url: Custom API base URL
        max_iterations: Maximum tool execution iterations

    Returns:
        Decorated class that is an OpenAIFunctionAgent instance
    """
    def decorator(cls):
        if not OPENAI_AVAILABLE:
            warnings.warn(
                f"OpenAI not available for agent {name}. "
                "Install with: pip install openai"
            )
            # Return original class so it doesn't break
            return cls

        @wraps(cls)
        def wrapper(*args, **kwargs):
            # Ignore the class entirely and return our adapter
            return OpenAIFunctionAgent(
                name=name,
                model=model,
                tools=tools,
                tool_executors=tool_executors,
                description=description,
                config=config,
                system_message=system_message,
                api_key=api_key,
                base_url=base_url,
                max_iterations=max_iterations,
            )

        # Copy class metadata
        wrapper.__name__ = cls.__name__
        wrapper.__module__ = cls.__module__
        wrapper.__doc__ = cls.__doc__ or description
        wrapper.__qualname__ = cls.__qualname__

        return wrapper

    return decorator


def tool_to_openai_format(
    name: str,
    description: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert a tool definition to OpenAI function format.

    Args:
        name: Tool name
        description: Tool description
        parameters: JSON Schema for parameters

    Returns:
        Tool in OpenAI format
    """
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


__all__ = [
    "OpenAIFunctionAgent",
    "openai_agent",
    "tool_to_openai_format",
    "OPENAI_AVAILABLE",
]

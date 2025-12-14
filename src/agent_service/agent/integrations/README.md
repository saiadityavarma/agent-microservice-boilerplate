# Framework Integrations

This directory provides adapters and decorators for integrating popular agent frameworks with the `IAgent` interface.

## Overview

All integrations:
- Gracefully handle missing dependencies
- Support both `invoke()` and `stream()` methods
- Work with `AgentConfig` for configuration management
- Can be registered in the agent registry
- Provide decorator-based usage for easy setup

## Available Integrations

### 1. LangGraph (`langgraph.py`)

Wraps LangGraph `StateGraph` as an `IAgent`.

**Installation:**
```bash
pip install langgraph
```

**Usage:**
```python
from agent_service.agent.integrations import langgraph_agent
from langgraph.graph import StateGraph, END

# Create your LangGraph
graph = StateGraph(...)
# ... build graph ...
compiled_graph = graph.compile()

# Wrap as IAgent
@langgraph_agent(graph=compiled_graph, name="my_lg_agent")
class MyLangGraphAgent(IAgent):
    pass

# Use it
agent = MyLangGraphAgent()
result = await agent.invoke(AgentInput(message="Hello!"))
```

**Features:**
- Maps `AgentInput` to LangGraph state
- Maps LangGraph state to `AgentOutput`
- Supports streaming with `astream()`
- Custom input/output mappers available

**State Mapping:**

Default input mapping:
```python
{
    "messages": [{"role": "user", "content": input.message}],
    "session_id": input.session_id,
    **input.context
}
```

Default output mapping extracts the last message content and tool calls.

### 2. CrewAI (`crewai.py`)

Wraps CrewAI `Crew` as an `IAgent`.

**Installation:**
```bash
pip install crewai
```

**Usage:**
```python
from agent_service.agent.integrations import crewai_agent
from crewai import Agent, Task, Crew

# Create your Crew
researcher = Agent(role="Researcher", goal="...", ...)
task = Task(description="...", agent=researcher, ...)
crew = Crew(agents=[researcher], tasks=[task])

# Wrap as IAgent
@crewai_agent(crew=crew, name="my_crew_agent")
class MyCrewAgent(IAgent):
    pass

# Use it
agent = MyCrewAgent()
result = await agent.invoke(AgentInput(message="Research topic X"))
```

**Features:**
- Handles crew kickoff and results
- Maps `AgentInput` to crew inputs
- Extracts task outputs and metadata
- Supports async execution in executor
- Streaming support (yields task outputs)

**Input Mapping:**

Default input mapping:
```python
{
    "message": input.message,
    "session_id": input.session_id,
    **input.context
}
```

### 3. OpenAI Function Calling (`openai_functions.py`)

Uses OpenAI chat completions with function calling as an `IAgent`.

**Installation:**
```bash
pip install openai
```

**Usage:**
```python
from agent_service.agent.integrations import openai_agent, tool_to_openai_format

# Define tools
def get_weather(location: str) -> dict:
    return {"location": location, "temp": 72}

# Convert to OpenAI format
tools = [
    tool_to_openai_format(
        name="get_weather",
        description="Get weather for a location",
        parameters={
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"]
        }
    )
]

tool_executors = {"get_weather": get_weather}

# Wrap as IAgent
@openai_agent(
    name="my_oai_agent",
    model="gpt-4",
    tools=tools,
    tool_executors=tool_executors,
)
class MyOpenAIAgent(IAgent):
    pass

# Use it
agent = MyOpenAIAgent()
result = await agent.invoke(AgentInput(message="What's the weather in SF?"))
```

**Features:**
- Automatic tool execution loop
- Streaming support with tool calls
- Support for both sync and async tool executors
- Configurable max iterations
- Custom system messages
- Token usage tracking in metadata

**Configuration:**
```python
@openai_agent(
    name="agent",
    model="gpt-4",
    tools=[...],
    tool_executors={...},
    system_message="Custom system prompt",
    api_key="sk-...",  # Optional, defaults to env var
    base_url="https://...",  # Optional, for proxies
    max_iterations=10,  # Max tool execution loops
)
```

## Agent Configuration

All integrations support `AgentConfig`:

```python
from agent_service.agent.config import AgentConfig

config = AgentConfig(
    timeout=300,
    max_tokens=4096,
    temperature=0.7,
    enabled_tools=["tool1", "tool2"],  # Whitelist
    disabled_tools=["tool3"],  # Blacklist
    rate_limit="100/hour",
    model="gpt-4",  # Override model
    streaming=True,
    retry_attempts=3,
    metadata={"custom": "value"}
)

@langgraph_agent(graph=g, name="agent", config=config)
class MyAgent(IAgent):
    pass
```

### Loading from YAML

```python
from agent_service.agent.config import AgentConfig

# Load from file
config = AgentConfig.from_yaml("configs/my_agent.yaml")

# Save to file
config.to_yaml("configs/my_agent.yaml")
```

**Example YAML:**
```yaml
timeout: 300
max_tokens: 4096
temperature: 0.7
enabled_tools:
  - tool1
  - tool2
rate_limit: "100/hour"
model: "gpt-4"
streaming: true
metadata:
  custom: value
```

### Global Config Directory

```python
from agent_service.agent.config import set_config_dir, get_config

# Set global config directory
set_config_dir("./configs")

# Automatically loads from configs/my_agent.yaml if exists
config = get_config("my_agent")
```

## Custom Mappers

You can provide custom input/output mappers:

```python
def my_input_mapper(input: AgentInput) -> dict:
    return {
        "custom_field": input.message,
        "user_id": input.context.get("user_id")
    }

def my_output_mapper(state: dict) -> AgentOutput:
    return AgentOutput(
        content=state["custom_response"],
        metadata=state["custom_metadata"]
    )

@langgraph_agent(
    graph=graph,
    name="agent",
    input_mapper=my_input_mapper,
    output_mapper=my_output_mapper,
)
class MyAgent(IAgent):
    pass
```

## Checking Integration Status

```python
from agent_service.agent.integrations import (
    check_integrations,
    get_missing_integrations,
    print_integration_status,
)

# Check what's available
status = check_integrations()
# {"langgraph": True, "crewai": False, "openai": True}

# Get missing ones
missing = get_missing_integrations()
# ["crewai"]

# Print status
print_integration_status()
# Agent Framework Integration Status:
# ----------------------------------------
#   langgraph............ ✓ Available
#   crewai............... ✗ Not installed
#   openai............... ✓ Available
# ----------------------------------------
```

## Registering with Agent Registry

All integration-wrapped agents can be registered:

```python
from agent_service.agent.registry import agent_registry

@langgraph_agent(graph=graph, name="lg_agent")
class MyLGAgent(IAgent):
    pass

# Register
agent_registry.register(MyLGAgent())

# Retrieve
agent = agent_registry.get("lg_agent")
result = await agent.invoke(AgentInput(message="Hello!"))
```

## Examples

See `examples.py` for complete working examples of each integration type.

Run examples:
```bash
python -m agent_service.agent.integrations.examples
```

## Error Handling

All integrations handle missing dependencies gracefully:

```python
from agent_service.agent.integrations import LANGGRAPH_AVAILABLE

if not LANGGRAPH_AVAILABLE:
    print("Please install: pip install langgraph")
else:
    # Use LangGraph integration
    ...
```

Decorators will issue warnings if dependencies are missing but won't crash.

## Best Practices

1. **Use Configuration Files**: Store agent configs in YAML for easy management
2. **Custom Mappers**: Provide custom mappers when default behavior doesn't fit
3. **Tool Filtering**: Use `enabled_tools`/`disabled_tools` to control agent capabilities
4. **Error Handling**: Check availability flags before using integrations
5. **Streaming**: Implement streaming for better UX in long-running agents
6. **Metadata**: Use metadata to pass framework-specific config through

## Dependencies

| Integration | Package | Version |
|------------|---------|---------|
| LangGraph | `langgraph` | Latest |
| CrewAI | `crewai` | Latest |
| OpenAI | `openai` | >=1.0.0 |

Install all:
```bash
pip install langgraph crewai openai
```

Or individually as needed.

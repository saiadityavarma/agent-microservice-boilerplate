# Simple Chatbot Agent

A conversational chatbot agent with session-based conversation history.

## Overview

This example demonstrates how to build a simple chatbot agent that:
- Maintains conversation context across messages
- Uses session storage for conversation history
- Streams responses for better UX
- Handles errors gracefully
- Can be easily extended with real LLM integration

## Features

- **Conversation Memory**: Keeps track of conversation history per session
- **Streaming Responses**: Provides word-by-word streaming for real-time feedback
- **Session Management**: Stores up to 20 messages per session with 1-hour TTL
- **Error Handling**: Graceful error handling with user-friendly messages
- **Extensible**: Easy to replace the simulated LLM with real OpenAI/Anthropic API

## Files

- `agent.py` - Main chatbot implementation
- `README.md` - This file
- `test_chatbot.py` - Tests for the chatbot

## Quick Start

### 1. Installation

Make sure you have the base dependencies installed:

```bash
cd /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate
pip install -e .
```

### 2. Run the Example

```python
import asyncio
from agent_service.interfaces import AgentInput
from agent_service.agent import agent_registry

# Import to register agents
from examples.chatbot import agent

async def main():
    # Get the chatbot agent
    chatbot = agent_registry.get("simple_chatbot")

    # Create a session
    session_id = "user_session_123"

    # Send a message
    async for chunk in chatbot.stream(AgentInput(
        message="Hello! How are you?",
        session_id=session_id
    )):
        if chunk.type == "text":
            print(chunk.content, end="", flush=True)
    print()

asyncio.run(main())
```

### 3. Using the Non-Streaming Version

```python
from agent_service.interfaces import AgentInput
from agent_service.agent import agent_registry

async def sync_example():
    # Get the non-streaming chatbot
    chatbot = agent_registry.get("simple_chatbot_sync")

    # Send a message and get complete response
    result = await chatbot.invoke(AgentInput(
        message="Tell me a joke",
        session_id="user_123"
    ))

    print(result.content)
    print(f"Message count: {result.metadata['message_count']}")

asyncio.run(sync_example())
```

## Integrating with OpenAI

To use a real LLM instead of the simulated responses:

### 1. Install OpenAI

```bash
pip install openai
```

### 2. Set API Key

Add to your `.env` file:
```
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. Replace the Simulation Function

Replace the `simulate_llm_response` function in `agent.py`:

```python
import openai

async def get_openai_response(
    system_prompt: str,
    conversation_history: list,
    ctx: AgentContext
) -> str:
    """Get response from OpenAI."""
    # Get API key from secrets
    api_key = await ctx.get_secret("OPENAI_API_KEY")

    # Create client
    client = openai.AsyncOpenAI(api_key=api_key)

    # Build messages
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)

    # Call API
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=0.7,
        max_tokens=500
    )

    return response.choices[0].message.content
```

### 4. For Streaming Responses

```python
async def get_openai_streaming_response(
    system_prompt: str,
    conversation_history: list,
    ctx: AgentContext
) -> AsyncGenerator[str, None]:
    """Get streaming response from OpenAI."""
    api_key = await ctx.get_secret("OPENAI_API_KEY")
    client = openai.AsyncOpenAI(api_key=api_key)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)

    stream = await client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=0.7,
        max_tokens=500,
        stream=True
    )

    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

## Customization

### Change System Prompt

Modify the `system_prompt` in the agent to change the chatbot's personality:

```python
system_prompt = """You are a helpful customer support agent.
You are knowledgeable, professional, and always aim to resolve issues quickly.
Be empathetic and understanding."""
```

### Adjust History Length

Change the maximum number of stored messages:

```python
max_history = 50  # Store up to 50 messages
trimmed_history = conversation_history[-max_history:]
```

### Modify Cache TTL

Change how long conversation history is stored:

```python
await ctx.cache.set(history_key, trimmed_history, ttl=7200)  # 2 hours
```

### Add User Context

Include user information in prompts:

```python
if ctx.user:
    system_prompt += f"\nYou are speaking with {ctx.user.name}."
```

## Session Management

Sessions are identified by `session_id`. Different session IDs maintain separate conversation histories:

```python
# User 1's conversation
await chatbot.stream(AgentInput(
    message="Hello",
    session_id="user_1"
))

# User 2's conversation (separate history)
await chatbot.stream(AgentInput(
    message="Hello",
    session_id="user_2"
))
```

## Error Handling

The chatbot handles errors gracefully:

```python
try:
    # Agent logic
    ...
except Exception as e:
    ctx.logger.error("chatbot_error", error=str(e), exc_info=True)
    yield StreamChunk(
        type="error",
        content=f"I apologize, but I encountered an error: {str(e)}"
    )
```

## Testing

Run the tests:

```bash
pytest examples/chatbot/test_chatbot.py -v
```

## Next Steps

- Add sentiment analysis to detect user mood
- Implement conversation summarization for long histories
- Add multi-language support
- Integrate with real LLM providers (OpenAI, Anthropic, etc.)
- Add conversation analytics and metrics
- Implement conversation export/import

## Related Examples

- `rag-agent/` - For adding knowledge base capabilities
- `multi-agent/` - For coordinating multiple specialized agents
- `tool-use/` - For adding tool capabilities to the chatbot

## Architecture

```
User Input
    |
    v
Agent (simple_chatbot)
    |
    +-- Load conversation history from cache
    |
    +-- Add user message to history
    |
    +-- Generate response (OpenAI/simulated)
    |
    +-- Stream response to user
    |
    +-- Save updated history to cache
    |
    v
Streamed Response
```

## Production Considerations

1. **Rate Limiting**: Add rate limiting to prevent abuse
2. **Content Filtering**: Add content moderation for user inputs
3. **Cost Management**: Monitor and limit LLM API usage
4. **Conversation Cleanup**: Implement background job to clean old sessions
5. **Analytics**: Track conversation metrics and user satisfaction
6. **Backup**: Implement conversation history backup
7. **Privacy**: Add conversation data encryption and retention policies

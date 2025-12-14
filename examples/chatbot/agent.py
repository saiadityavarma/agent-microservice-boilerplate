"""
Simple Chatbot Agent Example

This example demonstrates:
- Basic conversational agent using OpenAI
- Session storage for conversation history
- Simple prompt engineering
- Error handling and logging
"""

from typing import AsyncGenerator
from agent_service.interfaces import AgentInput, AgentOutput, StreamChunk
from agent_service.agent import streaming_agent, AgentContext


# ============================================================================
# Simple Chatbot Agent
# ============================================================================


@streaming_agent(
    name="simple_chatbot",
    description="A simple conversational chatbot with memory"
)
async def simple_chatbot(
    input: AgentInput,
    ctx: AgentContext
) -> AsyncGenerator[StreamChunk, None]:
    """
    Simple chatbot with conversation history stored in session.

    This agent:
    - Maintains conversation history per session
    - Uses OpenAI for responses (simulated in this example)
    - Streams responses back to the user
    - Handles errors gracefully
    """
    session_id = input.session_id or "default"
    user_message = input.message

    ctx.logger.info("chatbot_request", session_id=session_id)

    try:
        # Get conversation history from cache
        history_key = f"history:{session_id}"
        conversation_history = []

        if ctx.cache:
            cached_history = await ctx.cache.get(history_key)
            if cached_history:
                conversation_history = cached_history
                ctx.logger.info(
                    "conversation_history_loaded",
                    message_count=len(conversation_history)
                )

        # Add user message to history
        conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Build prompt with conversation context
        system_prompt = """You are a helpful and friendly AI assistant.
You provide clear, concise, and accurate responses to user questions.
Be conversational and remember the context of the conversation."""

        # Simulate OpenAI API call (replace with actual OpenAI integration)
        response_text = await simulate_llm_response(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            ctx=ctx
        )

        # Stream the response
        words = response_text.split()
        for i, word in enumerate(words):
            # Stream word by word
            chunk_text = word + (" " if i < len(words) - 1 else "")
            yield StreamChunk(type="text", content=chunk_text)

            # Add small delay for streaming effect
            import asyncio
            await asyncio.sleep(0.05)

        # Add assistant response to history
        conversation_history.append({
            "role": "assistant",
            "content": response_text
        })

        # Save conversation history (keep last 20 messages)
        if ctx.cache:
            max_history = 20
            trimmed_history = conversation_history[-max_history:]
            await ctx.cache.set(history_key, trimmed_history, ttl=3600)
            ctx.logger.info("conversation_history_saved")

        ctx.logger.info("chatbot_response_completed", success=True)

    except Exception as e:
        ctx.logger.error("chatbot_error", error=str(e), exc_info=True)
        yield StreamChunk(
            type="error",
            content=f"I apologize, but I encountered an error: {str(e)}"
        )


async def simulate_llm_response(
    system_prompt: str,
    conversation_history: list,
    ctx: AgentContext
) -> str:
    """
    Simulate an LLM response.

    In production, replace this with actual OpenAI API call:

    ```python
    import openai

    async def get_openai_response(system_prompt, conversation_history, ctx):
        # Get API key from secrets
        api_key = await ctx.get_secret("OPENAI_API_KEY")

        # Create OpenAI client
        client = openai.AsyncOpenAI(api_key=api_key)

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)

        # Call OpenAI
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content
    ```
    """
    import asyncio

    # Simulate API delay
    await asyncio.sleep(0.3)

    # Get the last user message
    last_message = conversation_history[-1]["content"].lower()

    # Simple rule-based responses for demonstration
    if "hello" in last_message or "hi" in last_message:
        return "Hello! How can I help you today?"

    elif "how are you" in last_message:
        return "I'm doing great, thank you for asking! How can I assist you?"

    elif "name" in last_message:
        return "I'm a helpful AI assistant. You can call me Chatbot. What's your name?"

    elif "weather" in last_message:
        return "I don't have real-time weather data access in this demo, but I'd be happy to help with other questions!"

    elif "bye" in last_message or "goodbye" in last_message:
        return "Goodbye! Feel free to come back if you need anything else. Have a great day!"

    else:
        # Echo response for demonstration
        return f"I understand you said: '{conversation_history[-1]['content']}'. In a production environment, I would use an LLM to generate a more intelligent response based on our conversation history."


# ============================================================================
# Non-Streaming Version
# ============================================================================


@agent(
    name="simple_chatbot_sync",
    description="Non-streaming version of the chatbot"
)
async def simple_chatbot_sync(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Non-streaming version that returns complete response.

    Use this when you don't need streaming (e.g., for testing or batch processing).
    """
    session_id = input.session_id or "default"
    user_message = input.message

    try:
        # Get conversation history
        history_key = f"history:{session_id}"
        conversation_history = []

        if ctx.cache:
            cached_history = await ctx.cache.get(history_key)
            if cached_history:
                conversation_history = cached_history

        # Add user message
        conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Build prompt
        system_prompt = """You are a helpful and friendly AI assistant.
You provide clear, concise, and accurate responses to user questions.
Be conversational and remember the context of the conversation."""

        # Get response
        response_text = await simulate_llm_response(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            ctx=ctx
        )

        # Add to history
        conversation_history.append({
            "role": "assistant",
            "content": response_text
        })

        # Save history
        if ctx.cache:
            max_history = 20
            trimmed_history = conversation_history[-max_history:]
            await ctx.cache.set(history_key, trimmed_history, ttl=3600)

        return AgentOutput(
            content=response_text,
            metadata={
                "session_id": session_id,
                "message_count": len(conversation_history)
            }
        )

    except Exception as e:
        ctx.logger.error("chatbot_error", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"I apologize, but I encountered an error: {str(e)}",
            metadata={"error": str(e)}
        )


# Import for non-streaming example
from agent_service.agent import agent


# ============================================================================
# Example Usage
# ============================================================================


async def example_usage():
    """Demonstrate how to use the chatbot agent."""
    from agent_service.agent import agent_registry
    from agent_service.interfaces import AgentInput

    # Get the streaming agent
    chatbot = agent_registry.get("simple_chatbot")

    # Create conversation
    session_id = "demo_session_123"

    # First message
    print("User: Hello!")
    print("Bot: ", end="", flush=True)
    async for chunk in chatbot.stream(AgentInput(
        message="Hello!",
        session_id=session_id
    )):
        if chunk.type == "text":
            print(chunk.content, end="", flush=True)
    print("\n")

    # Follow-up message
    print("User: What's your name?")
    print("Bot: ", end="", flush=True)
    async for chunk in chatbot.stream(AgentInput(
        message="What's your name?",
        session_id=session_id
    )):
        if chunk.type == "text":
            print(chunk.content, end="", flush=True)
    print("\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())

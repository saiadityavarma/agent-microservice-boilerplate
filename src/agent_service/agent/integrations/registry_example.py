"""
Example showing how to register framework-integrated agents with the agent registry.

This demonstrates the complete workflow from creating an integrated agent
to registering and using it through the registry.
"""

from agent_service.interfaces.agent import IAgent, AgentInput
from agent_service.agent.registry import agent_registry
from agent_service.agent.config import AgentConfig


async def demo_registry_integration():
    """
    Demonstrate registering and using integrated agents.
    """
    print("=" * 70)
    print("Framework Integration + Agent Registry Demo")
    print("=" * 70)

    # ========================================================================
    # 1. Create and register a LangGraph agent
    # ========================================================================
    print("\n1. LangGraph Agent Registration")
    print("-" * 70)

    try:
        from agent_service.agent.integrations import langgraph_agent, LANGGRAPH_AVAILABLE

        if LANGGRAPH_AVAILABLE:
            from langgraph.graph import StateGraph, END
            from typing import TypedDict

            class State(TypedDict):
                messages: list[dict]

            def responder(state: State) -> State:
                msg = state["messages"][-1]["content"]
                state["messages"].append({
                    "role": "assistant",
                    "content": f"LangGraph response to: {msg}"
                })
                return state

            builder = StateGraph(State)
            builder.add_node("respond", responder)
            builder.set_entry_point("respond")
            builder.add_edge("respond", END)
            lg_graph = builder.compile()

            @langgraph_agent(
                graph=lg_graph,
                name="langgraph_responder",
                description="LangGraph-based responder agent",
                config=AgentConfig(timeout=60, temperature=0.5),
            )
            class LangGraphResponder(IAgent):
                pass

            # Create and register
            lg_agent = LangGraphResponder()
            agent_registry.register(lg_agent)
            print(f"✓ Registered: {lg_agent.name}")
            print(f"  Type: LangGraph")
            print(f"  Description: {lg_agent.description}")

            # Use through registry
            retrieved = agent_registry.get("langgraph_responder")
            result = await retrieved.invoke(AgentInput(message="Test message"))
            print(f"✓ Response: {result.content}")

        else:
            print("⚠ LangGraph not available")

    except Exception as e:
        print(f"✗ Error: {e}")

    # ========================================================================
    # 2. Create and register a CrewAI agent
    # ========================================================================
    print("\n2. CrewAI Agent Registration")
    print("-" * 70)

    try:
        from agent_service.agent.integrations import crewai_agent, CREWAI_AVAILABLE

        if CREWAI_AVAILABLE:
            from crewai import Agent, Task, Crew

            analyst = Agent(
                role="Analyst",
                goal="Analyze and summarize",
                backstory="Expert analyst",
                verbose=False,
            )

            task = Task(
                description="Analyze: {message}",
                agent=analyst,
                expected_output="Analysis summary",
            )

            crew = Crew(
                agents=[analyst],
                tasks=[task],
                verbose=False,
            )

            @crewai_agent(
                crew=crew,
                name="crewai_analyst",
                description="CrewAI-based analyst agent",
                config=AgentConfig(timeout=120),
            )
            class CrewAIAnalyst(IAgent):
                pass

            # Create and register
            crew_agent_instance = CrewAIAnalyst()
            agent_registry.register(crew_agent_instance)
            print(f"✓ Registered: {crew_agent_instance.name}")
            print(f"  Type: CrewAI")
            print(f"  Description: {crew_agent_instance.description}")
            print("  Note: Requires LLM API keys to execute")

        else:
            print("⚠ CrewAI not available")

    except Exception as e:
        print(f"✗ Error: {e}")

    # ========================================================================
    # 3. Create and register an OpenAI agent
    # ========================================================================
    print("\n3. OpenAI Agent Registration")
    print("-" * 70)

    try:
        from agent_service.agent.integrations import (
            openai_agent,
            tool_to_openai_format,
            OPENAI_AVAILABLE,
        )

        if OPENAI_AVAILABLE:
            # Define tools
            def calculate_sum(a: float, b: float) -> dict:
                """Calculate the sum of two numbers."""
                return {"result": a + b}

            def get_length(text: str) -> dict:
                """Get the length of a text string."""
                return {"length": len(text)}

            # Convert to OpenAI format
            tools = [
                tool_to_openai_format(
                    name="calculate_sum",
                    description="Calculate the sum of two numbers",
                    parameters={
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "First number"},
                            "b": {"type": "number", "description": "Second number"},
                        },
                        "required": ["a", "b"],
                    },
                ),
                tool_to_openai_format(
                    name="get_length",
                    description="Get the length of a text string",
                    parameters={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text to measure"},
                        },
                        "required": ["text"],
                    },
                ),
            ]

            @openai_agent(
                name="openai_assistant",
                model="gpt-4",
                tools=tools,
                tool_executors={
                    "calculate_sum": calculate_sum,
                    "get_length": get_length,
                },
                description="OpenAI assistant with calculator and text tools",
                config=AgentConfig(temperature=0.7, max_tokens=500),
                system_message="You are a helpful assistant with calculator and text analysis tools.",
            )
            class OpenAIAssistant(IAgent):
                pass

            # Create and register
            oai_agent = OpenAIAssistant()
            agent_registry.register(oai_agent)
            print(f"✓ Registered: {oai_agent.name}")
            print(f"  Type: OpenAI")
            print(f"  Description: {oai_agent.description}")
            print("  Note: Requires OPENAI_API_KEY environment variable")

        else:
            print("⚠ OpenAI not available")

    except Exception as e:
        print(f"✗ Error: {e}")

    # ========================================================================
    # 4. List all registered agents
    # ========================================================================
    print("\n4. Registry Summary")
    print("-" * 70)

    all_agents = agent_registry.list_agents()
    print(f"Total registered agents: {len(all_agents)}")

    for agent_name in all_agents:
        agent = agent_registry.get(agent_name)
        print(f"\n  • {agent_name}")
        print(f"    Description: {agent.description}")

    # ========================================================================
    # 5. Demonstrate using different agents for different tasks
    # ========================================================================
    print("\n5. Task Routing Example")
    print("-" * 70)

    # Task routing logic
    def route_task(message: str) -> str:
        """Route task to appropriate agent based on content."""
        message_lower = message.lower()

        if "calculate" in message_lower or "sum" in message_lower:
            return "openai_assistant"
        elif "analyze" in message_lower:
            return "crewai_analyst"
        else:
            return "langgraph_responder"

    # Example tasks
    tasks = [
        "Calculate the sum of 5 and 7",
        "Analyze the current market trends",
        "Hello, how are you?",
    ]

    for task in tasks:
        agent_name = route_task(task)
        print(f"\nTask: {task}")
        print(f"Routed to: {agent_name}")

        if agent_name in agent_registry.list_agents():
            print(f"✓ Agent available in registry")
        else:
            print(f"⚠ Agent not registered (dependency missing)")

    print("\n" + "=" * 70)


# ============================================================================
# Advanced: Dynamic agent registration from config
# ============================================================================

async def demo_config_based_registration():
    """
    Demonstrate creating and registering agents from configuration.
    """
    print("\n" + "=" * 70)
    print("Config-Based Agent Registration Demo")
    print("=" * 70)

    from agent_service.agent.config import AgentConfig, set_config_dir
    import tempfile
    import os

    # Create temporary config directory
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\nUsing config directory: {tmpdir}")

        # Set global config directory
        set_config_dir(tmpdir)

        # Create config for an agent
        config = AgentConfig(
            timeout=90,
            max_tokens=2048,
            temperature=0.6,
            enabled_tools=["tool1", "tool2"],
            rate_limit="50/hour",
            model="gpt-4",
            metadata={"team": "research", "version": "1.0"},
        )

        # Save config
        config_path = os.path.join(tmpdir, "my_agent.yaml")
        config.to_yaml(config_path)
        print(f"✓ Saved config to: {config_path}")

        # Load and display config
        loaded_config = AgentConfig.from_yaml(config_path)
        print(f"\n✓ Loaded config:")
        print(f"  - timeout: {loaded_config.timeout}s")
        print(f"  - max_tokens: {loaded_config.max_tokens}")
        print(f"  - temperature: {loaded_config.temperature}")
        print(f"  - model: {loaded_config.model}")
        print(f"  - enabled_tools: {loaded_config.enabled_tools}")
        print(f"  - metadata: {loaded_config.metadata}")

        # Use config with an agent
        try:
            from agent_service.agent.integrations import langgraph_agent, LANGGRAPH_AVAILABLE

            if LANGGRAPH_AVAILABLE:
                from langgraph.graph import StateGraph, END
                from typing import TypedDict

                class State(TypedDict):
                    messages: list[dict]

                def process(state: State) -> State:
                    return state

                builder = StateGraph(State)
                builder.add_node("process", process)
                builder.set_entry_point("process")
                builder.add_edge("process", END)
                graph = builder.compile()

                @langgraph_agent(
                    graph=graph,
                    name="configured_agent",
                    config=loaded_config,
                )
                class ConfiguredAgent(IAgent):
                    pass

                agent = ConfiguredAgent()
                print(f"\n✓ Created agent with loaded config: {agent.name}")

        except Exception as e:
            print(f"\n⚠ Could not create agent: {e}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    import asyncio

    # Run the main demo
    asyncio.run(demo_registry_integration())

    # Run the config-based demo
    asyncio.run(demo_config_based_registration())

    print("\n✓ Registry integration demo complete!")
    print("\nKey Takeaways:")
    print("  1. Framework-integrated agents work seamlessly with agent_registry")
    print("  2. Agents can be retrieved and used through the registry")
    print("  3. Task routing can select agents based on message content")
    print("  4. Configuration can be loaded from YAML files")
    print("  5. Multiple framework types can coexist in the same registry")

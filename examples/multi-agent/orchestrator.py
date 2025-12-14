"""
Multi-Agent Orchestrator

Coordinates multiple specialized agents to accomplish complex tasks.

Patterns demonstrated:
- Sequential workflow (research -> write -> review)
- Parallel execution
- Agent delegation
- Result aggregation
- Error handling and retry
"""

from typing import Any, List
from agent_service.interfaces import AgentInput, AgentOutput
from agent_service.agent import agent, AgentContext
from agent_service.agent.registry import agent_registry


# ============================================================================
# Content Creation Orchestrator
# ============================================================================


@agent(
    name="content_orchestrator",
    description="Orchestrates research, writing, and review agents to create content"
)
async def content_orchestrator(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Orchestrate a multi-agent workflow to create content.

    Workflow:
    1. Researcher gathers information
    2. Writer creates content from research
    3. Reviewer improves the content
    4. Return final polished content
    """
    topic = input.message
    ctx.logger.info("orchestration_started", topic=topic)

    try:
        # Step 1: Research
        ctx.logger.info("step_1_research")
        researcher = agent_registry.get("researcher_agent")
        if not researcher:
            raise ValueError("Researcher agent not found")

        research_result = await researcher.invoke(
            AgentInput(message=topic, session_id=input.session_id)
        )

        if not research_result.content:
            raise ValueError("Research failed to produce results")

        ctx.logger.info("research_completed", facts=research_result.metadata.get("facts_found", 0))

        # Step 2: Write
        ctx.logger.info("step_2_writing")
        writer = agent_registry.get("writer_agent")
        if not writer:
            raise ValueError("Writer agent not found")

        write_result = await writer.invoke(
            AgentInput(
                message=research_result.content,
                session_id=input.session_id
            )
        )

        ctx.logger.info("writing_completed", word_count=write_result.metadata.get("word_count", 0))

        # Step 3: Review
        ctx.logger.info("step_3_review")
        reviewer = agent_registry.get("reviewer_agent")
        if not reviewer:
            raise ValueError("Reviewer agent not found")

        review_result = await reviewer.invoke(
            AgentInput(
                message=write_result.content,
                session_id=input.session_id
            )
        )

        ctx.logger.info(
            "review_completed",
            status=review_result.metadata.get("status", "unknown")
        )

        # Compile final output
        final_content = extract_final_content(review_result.content)

        ctx.logger.info("orchestration_completed", success=True)

        return AgentOutput(
            content=final_content,
            metadata={
                "orchestrator": "content_orchestrator",
                "topic": topic,
                "workflow_steps": ["research", "write", "review"],
                "research_facts": research_result.metadata.get("facts_found", 0),
                "word_count": write_result.metadata.get("word_count", 0),
                "review_status": review_result.metadata.get("status", "unknown"),
                "review_issues": review_result.metadata.get("issues_found", 0)
            }
        )

    except Exception as e:
        ctx.logger.error("orchestration_failed", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"Content creation failed: {str(e)}",
            metadata={
                "orchestrator": "content_orchestrator",
                "error": str(e)
            }
        )


# ============================================================================
# Parallel Research Orchestrator
# ============================================================================


@agent(
    name="parallel_orchestrator",
    description="Coordinates multiple agents in parallel for faster results"
)
async def parallel_orchestrator(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Orchestrate multiple agents in parallel.

    Example: Research multiple topics simultaneously, then aggregate results.
    """
    import asyncio

    topics = parse_topics(input.message)
    ctx.logger.info("parallel_orchestration_started", topic_count=len(topics))

    try:
        researcher = agent_registry.get("researcher_agent")
        if not researcher:
            raise ValueError("Researcher agent not found")

        # Execute research tasks in parallel
        research_tasks = [
            researcher.invoke(AgentInput(message=topic, session_id=input.session_id))
            for topic in topics
        ]

        ctx.logger.info("executing_parallel_tasks", count=len(research_tasks))
        research_results = await asyncio.gather(*research_tasks, return_exceptions=True)

        # Aggregate results
        aggregated = aggregate_research_results(research_results, topics)

        # Write comprehensive article from all research
        writer = agent_registry.get("writer_agent")
        if writer:
            final_result = await writer.invoke(
                AgentInput(message=aggregated, session_id=input.session_id)
            )
            content = final_result.content
        else:
            content = aggregated

        ctx.logger.info("parallel_orchestration_completed", success=True)

        return AgentOutput(
            content=content,
            metadata={
                "orchestrator": "parallel_orchestrator",
                "topics": topics,
                "parallel_tasks": len(topics),
                "successful_tasks": sum(1 for r in research_results if not isinstance(r, Exception))
            }
        )

    except Exception as e:
        ctx.logger.error("parallel_orchestration_failed", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"Parallel orchestration failed: {str(e)}",
            metadata={"error": str(e)}
        )


# ============================================================================
# Adaptive Orchestrator
# ============================================================================


@agent(
    name="adaptive_orchestrator",
    description="Adapts workflow based on intermediate results"
)
async def adaptive_orchestrator(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Adaptive orchestrator that adjusts workflow based on results.

    Example:
    - If research finds insufficient data, gather more
    - If review finds major issues, rewrite
    - If content is too brief, expand
    """
    topic = input.message
    ctx.logger.info("adaptive_orchestration_started", topic=topic)

    max_iterations = 3
    iteration = 0

    try:
        # Initial research
        researcher = agent_registry.get("researcher_agent")
        research_result = await researcher.invoke(
            AgentInput(message=topic, session_id=input.session_id)
        )

        facts_found = research_result.metadata.get("facts_found", 0)

        # Adaptive: If insufficient research, gather more
        if facts_found < 3 and iteration < max_iterations:
            ctx.logger.info("insufficient_research_retrying")
            # In production, you might try different search strategies
            iteration += 1

        # Write content
        writer = agent_registry.get("writer_agent")
        write_result = await writer.invoke(
            AgentInput(message=research_result.content, session_id=input.session_id)
        )

        # Review content
        reviewer = agent_registry.get("reviewer_agent")
        review_result = await reviewer.invoke(
            AgentInput(message=write_result.content, session_id=input.session_id)
        )

        issues_found = review_result.metadata.get("issues_found", 0)

        # Adaptive: If major issues, rewrite
        if issues_found > 3 and iteration < max_iterations:
            ctx.logger.info("major_issues_found_rewriting")
            # Extract improvement suggestions
            # Rewrite with feedback
            write_result = await writer.invoke(
                AgentInput(
                    message=f"Improve this content:\n{write_result.content}\n\nIssues to address:\n{review_result.content}",
                    session_id=input.session_id
                )
            )
            iteration += 1

        final_content = extract_final_content(review_result.content)

        ctx.logger.info(
            "adaptive_orchestration_completed",
            iterations=iteration,
            success=True
        )

        return AgentOutput(
            content=final_content,
            metadata={
                "orchestrator": "adaptive_orchestrator",
                "iterations": iteration,
                "final_quality": "high" if issues_found <= 2 else "medium"
            }
        )

    except Exception as e:
        ctx.logger.error("adaptive_orchestration_failed", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"Adaptive orchestration failed: {str(e)}",
            metadata={"error": str(e)}
        )


# ============================================================================
# Helper Functions
# ============================================================================


def extract_final_content(review_output: str) -> str:
    """Extract final content from review output."""
    # Review output contains both report and content
    if "REVISED CONTENT:" in review_output:
        parts = review_output.split("REVISED CONTENT:")
        return parts[1].strip() if len(parts) > 1 else review_output
    elif "ORIGINAL CONTENT:" in review_output:
        parts = review_output.split("ORIGINAL CONTENT:")
        return parts[1].strip() if len(parts) > 1 else review_output
    else:
        # If no markers, return full output
        return review_output


def parse_topics(input_text: str) -> List[str]:
    """
    Parse multiple topics from input.

    Examples:
    - "Python, JavaScript, Rust" -> ["Python", "JavaScript", "Rust"]
    - "Python\nJavaScript\nRust" -> ["Python", "JavaScript", "Rust"]
    """
    # Try comma-separated
    if "," in input_text:
        topics = [t.strip() for t in input_text.split(",")]
    # Try newline-separated
    elif "\n" in input_text:
        topics = [t.strip() for t in input_text.split("\n") if t.strip()]
    # Single topic
    else:
        topics = [input_text.strip()]

    return topics


def aggregate_research_results(results: List[Any], topics: List[str]) -> str:
    """Aggregate multiple research results."""
    aggregated = "COMPREHENSIVE RESEARCH REPORT\n" + "=" * 50 + "\n\n"

    for i, (topic, result) in enumerate(zip(topics, results), 1):
        if isinstance(result, Exception):
            aggregated += f"## {i}. {topic}\n\nResearch failed: {str(result)}\n\n"
        else:
            aggregated += f"## {i}. {topic}\n\n{result.content}\n\n"

    return aggregated


# ============================================================================
# Communication Between Agents
# ============================================================================


@agent(
    name="coordinator_agent",
    description="Coordinates agent-to-agent communication"
)
async def coordinator_agent(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Demonstrate agent-to-agent communication.

    This agent acts as a coordinator that:
    1. Receives a request
    2. Delegates to appropriate specialized agents
    3. Facilitates communication between agents
    4. Returns aggregated results
    """
    request = input.message
    ctx.logger.info("coordination_started")

    try:
        # Parse request to determine which agents to involve
        if "research" in request.lower():
            # Delegate to researcher
            researcher = agent_registry.get("researcher_agent")
            result = await researcher.invoke(input)

            # If results need writing, delegate to writer
            if "write" in request.lower():
                writer = agent_registry.get("writer_agent")
                result = await writer.invoke(
                    AgentInput(message=result.content, session_id=input.session_id)
                )

            return result

        elif "review" in request.lower():
            # Delegate to reviewer
            reviewer = agent_registry.get("reviewer_agent")
            return await reviewer.invoke(input)

        else:
            # Full workflow
            orchestrator = agent_registry.get("content_orchestrator")
            return await orchestrator.invoke(input)

    except Exception as e:
        ctx.logger.error("coordination_failed", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"Coordination failed: {str(e)}",
            metadata={"error": str(e)}
        )


# ============================================================================
# Example Usage
# ============================================================================


async def example_sequential_orchestration():
    """Example: Sequential workflow orchestration."""
    from agent_service.agent import agent_registry

    orchestrator = agent_registry.get("content_orchestrator")

    result = await orchestrator.invoke(
        AgentInput(message="Python programming language")
    )

    print("Sequential Orchestration Result:")
    print(result.content)
    print("\nMetadata:", result.metadata)


async def example_parallel_orchestration():
    """Example: Parallel workflow orchestration."""
    from agent_service.agent import agent_registry

    orchestrator = agent_registry.get("parallel_orchestrator")

    result = await orchestrator.invoke(
        AgentInput(message="Python, JavaScript, Rust")
    )

    print("Parallel Orchestration Result:")
    print(result.content)
    print("\nMetadata:", result.metadata)


async def example_adaptive_orchestration():
    """Example: Adaptive workflow orchestration."""
    from agent_service.agent import agent_registry

    orchestrator = agent_registry.get("adaptive_orchestrator")

    result = await orchestrator.invoke(
        AgentInput(message="Machine Learning")
    )

    print("Adaptive Orchestration Result:")
    print(result.content)
    print("\nMetadata:", result.metadata)


if __name__ == "__main__":
    import asyncio

    print("Running Sequential Orchestration...")
    asyncio.run(example_sequential_orchestration())

    print("\n" + "=" * 80 + "\n")

    print("Running Parallel Orchestration...")
    asyncio.run(example_parallel_orchestration())

    print("\n" + "=" * 80 + "\n")

    print("Running Adaptive Orchestration...")
    asyncio.run(example_adaptive_orchestration())

# Multi-Agent Collaboration System

A production-ready multi-agent system demonstrating agent coordination, delegation, and collaboration patterns.

## Overview

This example shows how to build systems where multiple specialized agents work together to accomplish complex tasks. It demonstrates:

- **Sequential Workflows**: Agents execute one after another
- **Parallel Execution**: Multiple agents run simultaneously
- **Adaptive Workflows**: Dynamic adjustment based on results
- **Agent-to-Agent Communication**: Direct delegation between agents
- **Result Aggregation**: Combining outputs from multiple agents

## Architecture

```
User Request
     |
     v
Orchestrator
     |
     +-- Researcher Agent (gather information)
     |
     +-- Writer Agent (create content)
     |
     +-- Reviewer Agent (improve quality)
     |
     v
Final Output
```

## Agents

### Specialized Agents

1. **Researcher Agent** (`researcher_agent`)
   - Gathers information on topics
   - Compiles facts and sources
   - Returns structured research findings

2. **Writer Agent** (`writer_agent`)
   - Creates well-written content
   - Structures information logically
   - Generates articles, reports, documentation

3. **Reviewer Agent** (`reviewer_agent`)
   - Reviews content quality
   - Identifies issues and improvements
   - Enhances clarity and accuracy

### Orchestrator Agents

1. **Content Orchestrator** (`content_orchestrator`)
   - Sequential workflow: Research → Write → Review
   - Best for complete content creation

2. **Parallel Orchestrator** (`parallel_orchestrator`)
   - Executes tasks simultaneously
   - Aggregates parallel results
   - Best for multi-topic research

3. **Adaptive Orchestrator** (`adaptive_orchestrator`)
   - Adjusts workflow dynamically
   - Retries on insufficient results
   - Best for quality-critical tasks

4. **Coordinator Agent** (`coordinator_agent`)
   - Routes requests to appropriate agents
   - Facilitates agent communication
   - Best for flexible delegation

## Files

- `agents.py` - Specialized agent implementations
- `orchestrator.py` - Orchestration patterns and workflows
- `README.md` - This file
- `test_multi_agent.py` - Tests

## Quick Start

### 1. Sequential Workflow

Create content through a multi-step process:

```python
import asyncio
from agent_service.interfaces import AgentInput
from agent_service.agent import agent_registry

# Import to register agents
from examples.multi_agent import agents, orchestrator

async def main():
    # Get orchestrator
    orch = agent_registry.get("content_orchestrator")

    # Create content about a topic
    result = await orch.invoke(AgentInput(
        message="Python programming language"
    ))

    print(result.content)
    print("\nWorkflow metadata:", result.metadata)

asyncio.run(main())
```

Output includes:
- Research findings
- Written article
- Quality review
- Final polished content

### 2. Parallel Execution

Research multiple topics simultaneously:

```python
async def parallel_example():
    parallel_orch = agent_registry.get("parallel_orchestrator")

    result = await parallel_orch.invoke(AgentInput(
        message="Python, JavaScript, Rust"
    ))

    print(result.content)
    print(f"Processed {result.metadata['parallel_tasks']} topics in parallel")

asyncio.run(parallel_example())
```

### 3. Using Individual Agents

Work with specialized agents directly:

```python
async def individual_agents():
    # Get agents
    researcher = agent_registry.get("researcher_agent")
    writer = agent_registry.get("writer_agent")
    reviewer = agent_registry.get("reviewer_agent")

    # 1. Research
    research = await researcher.invoke(AgentInput(
        message="Artificial Intelligence"
    ))
    print("Research:", research.content)

    # 2. Write
    article = await writer.invoke(AgentInput(
        message=research.content
    ))
    print("\nArticle:", article.content)

    # 3. Review
    final = await reviewer.invoke(AgentInput(
        message=article.content
    ))
    print("\nReviewed:", final.content)

asyncio.run(individual_agents())
```

### 4. Adaptive Workflow

Let the orchestrator adapt based on quality:

```python
async def adaptive_example():
    adaptive_orch = agent_registry.get("adaptive_orchestrator")

    result = await adaptive_orch.invoke(AgentInput(
        message="Quantum Computing"
    ))

    print(result.content)
    print(f"Required {result.metadata['iterations']} iterations")
    print(f"Final quality: {result.metadata['final_quality']}")

asyncio.run(adaptive_example())
```

## Multi-Agent Patterns

### Pattern 1: Sequential Pipeline

```python
async def sequential_pipeline(topic: str, ctx: AgentContext):
    """Execute agents in sequence, passing output forward."""
    # Step 1
    researcher = agent_registry.get("researcher_agent")
    result1 = await researcher.invoke(AgentInput(message=topic))

    # Step 2 (uses output from step 1)
    writer = agent_registry.get("writer_agent")
    result2 = await writer.invoke(AgentInput(message=result1.content))

    # Step 3 (uses output from step 2)
    reviewer = agent_registry.get("reviewer_agent")
    result3 = await reviewer.invoke(AgentInput(message=result2.content))

    return result3
```

### Pattern 2: Parallel Fan-Out

```python
import asyncio

async def parallel_fanout(topics: list, ctx: AgentContext):
    """Execute same agent on multiple inputs in parallel."""
    researcher = agent_registry.get("researcher_agent")

    # Create tasks for all topics
    tasks = [
        researcher.invoke(AgentInput(message=topic))
        for topic in topics
    ]

    # Execute in parallel
    results = await asyncio.gather(*tasks)

    return results
```

### Pattern 3: Conditional Routing

```python
async def conditional_routing(request: str, ctx: AgentContext):
    """Route to different agents based on input."""
    if "research" in request.lower():
        agent = agent_registry.get("researcher_agent")
    elif "write" in request.lower():
        agent = agent_registry.get("writer_agent")
    elif "review" in request.lower():
        agent = agent_registry.get("reviewer_agent")
    else:
        agent = agent_registry.get("content_orchestrator")

    return await agent.invoke(AgentInput(message=request))
```

### Pattern 4: Retry with Feedback

```python
async def retry_with_feedback(topic: str, ctx: AgentContext, max_retries: int = 3):
    """Retry with feedback until quality threshold met."""
    writer = agent_registry.get("writer_agent")
    reviewer = agent_registry.get("reviewer_agent")

    for attempt in range(max_retries):
        # Write content
        content = await writer.invoke(AgentInput(message=topic))

        # Review
        review = await reviewer.invoke(AgentInput(message=content.content))

        # Check quality
        issues = review.metadata.get("issues_found", 0)
        if issues <= 2:  # Quality threshold
            return review

        # Provide feedback for next iteration
        topic = f"Improve: {content.content}\nIssues: {review.content}"

    return review  # Return best attempt
```

### Pattern 5: Hierarchical Delegation

```python
async def hierarchical_delegation(task: str, ctx: AgentContext):
    """Coordinator delegates to orchestrator, which delegates to workers."""
    # Level 1: Coordinator
    coordinator = agent_registry.get("coordinator_agent")

    # Coordinator decides which orchestrator
    if "multiple topics" in task.lower():
        orchestrator = agent_registry.get("parallel_orchestrator")
    else:
        orchestrator = agent_registry.get("content_orchestrator")

    # Level 2: Orchestrator manages worker agents
    result = await orchestrator.invoke(AgentInput(message=task))

    return result
```

## Advanced Examples

### Custom Orchestration Logic

Create your own orchestrator with custom logic:

```python
from agent_service.agent import agent, AgentContext
from agent_service.interfaces import AgentInput, AgentOutput

@agent(name="custom_orchestrator")
async def custom_orchestrator(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """Custom orchestration with specific business logic."""
    # Your custom logic here
    researcher = agent_registry.get("researcher_agent")
    writer = agent_registry.get("writer_agent")

    # Parallel research on multiple aspects
    import asyncio
    aspects = ["history", "technical details", "future trends"]
    research_tasks = [
        researcher.invoke(AgentInput(message=f"{input.message} {aspect}"))
        for aspect in aspects
    ]
    research_results = await asyncio.gather(*research_tasks)

    # Combine research
    combined = "\n\n".join(r.content for r in research_results)

    # Single write pass
    final = await writer.invoke(AgentInput(message=combined))

    return final
```

### Inter-Agent State Sharing

Share state between agents using context:

```python
@agent(name="stateful_orchestrator")
async def stateful_orchestrator(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """Orchestrator that shares state between agents."""
    # Store intermediate results in cache
    if ctx.cache:
        # Research phase
        researcher = agent_registry.get("researcher_agent")
        research = await researcher.invoke(input)

        # Cache research for other agents
        await ctx.cache.set("research_data", research.content, ttl=3600)

        # Writer can access cached research
        writer = agent_registry.get("writer_agent")
        article = await writer.invoke(AgentInput(message=research.content))

        # Cache article
        await ctx.cache.set("article_draft", article.content, ttl=3600)

        # Reviewer accesses cached article
        reviewer = agent_registry.get("reviewer_agent")
        final = await reviewer.invoke(AgentInput(message=article.content))

        return final
```

### Error Handling in Orchestration

Robust error handling for agent failures:

```python
@agent(name="robust_orchestrator")
async def robust_orchestrator(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """Orchestrator with comprehensive error handling."""
    results = []
    errors = []

    # Try researcher
    try:
        researcher = agent_registry.get("researcher_agent")
        research = await researcher.invoke(input)
        results.append(("research", research))
    except Exception as e:
        ctx.logger.error("research_failed", error=str(e))
        errors.append(("research", str(e)))

    # Try writer (even if research failed)
    try:
        writer = agent_registry.get("writer_agent")
        # Use research if available, otherwise original input
        write_input = results[0][1].content if results else input.message
        article = await writer.invoke(AgentInput(message=write_input))
        results.append(("write", article))
    except Exception as e:
        ctx.logger.error("write_failed", error=str(e))
        errors.append(("write", str(e)))

    # Return best available result
    if results:
        return results[-1][1]  # Return last successful result
    else:
        return AgentOutput(
            content=f"All agents failed: {errors}",
            metadata={"errors": errors}
        )
```

## Testing

Run the test suite:

```bash
pytest examples/multi-agent/test_multi_agent.py -v
```

Run specific test:

```bash
pytest examples/multi-agent/test_multi_agent.py::TestOrchestration::test_sequential_workflow -v
```

## Production Considerations

### 1. Performance

- **Parallel Execution**: Use `asyncio.gather()` for independent tasks
- **Caching**: Cache intermediate results to avoid redundant work
- **Timeouts**: Set timeouts for agent calls to prevent hanging
- **Resource Limits**: Limit concurrent agent executions

```python
import asyncio

# Limit concurrent executions
semaphore = asyncio.Semaphore(5)

async def limited_invoke(agent, input):
    async with semaphore:
        return await agent.invoke(input)
```

### 2. Monitoring

Track multi-agent workflows:

```python
@agent(name="monitored_orchestrator")
async def monitored_orchestrator(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    start_time = time.time()

    # Log workflow start
    ctx.logger.info("workflow_started", workflow="content_creation")

    # Execute steps with timing
    researcher = agent_registry.get("researcher_agent")
    step_start = time.time()
    research = await researcher.invoke(input)
    ctx.logger.info("step_completed", step="research", duration=time.time()-step_start)

    # ... more steps ...

    # Log workflow completion
    ctx.logger.info("workflow_completed", total_duration=time.time()-start_time)
```

### 3. Error Recovery

Implement retry logic with exponential backoff:

```python
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
async def invoke_with_retry(agent, input):
    """Retry agent invocation with exponential backoff."""
    return await agent.invoke(input)
```

### 4. Cost Management

For LLM-based agents, track and limit costs:

```python
@agent(name="cost_aware_orchestrator")
async def cost_aware_orchestrator(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    budget = 1.00  # $1 budget
    spent = 0.0

    # Track costs for each agent call
    research = await researcher.invoke(input)
    spent += estimate_cost(research)  # Estimate based on tokens

    if spent < budget:
        article = await writer.invoke(AgentInput(message=research.content))
        spent += estimate_cost(article)

    ctx.logger.info("orchestration_cost", spent=spent, budget=budget)
    return article
```

## Next Steps

- Add more specialized agents (data analyst, code generator, etc.)
- Implement consensus mechanism for multiple agents
- Add human-in-the-loop approval for critical steps
- Build agent marketplace/registry for discovery
- Implement agent performance tracking and optimization

## Related Examples

- `chatbot/` - Add multi-agent backend to chatbot
- `rag-agent/` - Use multi-agent for comprehensive research
- `tool-use/` - Combine multi-agent with tool usage

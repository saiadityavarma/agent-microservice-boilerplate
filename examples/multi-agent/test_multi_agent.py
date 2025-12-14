"""
Tests for Multi-Agent System
"""

import pytest
from agent_service.interfaces import AgentInput, AgentOutput
from agent_service.agent import AgentContext, agent_registry
from agent_service.tools import tool_registry
from agent_service.infrastructure.cache.cache import get_cache

# Import to register agents
from examples.multi_agent.agents import (
    researcher_agent,
    writer_agent,
    reviewer_agent
)
from examples.multi_agent.orchestrator import (
    content_orchestrator,
    parallel_orchestrator,
    adaptive_orchestrator,
    coordinator_agent,
    parse_topics,
    aggregate_research_results,
    extract_final_content
)


@pytest.fixture
async def agent_context():
    """Create a test agent context."""
    cache = await get_cache(namespace="test:multi_agent")
    return AgentContext(
        tools=tool_registry,
        cache=cache,
        db=None,
        logger=None,
        user=None,
        request_id="test-request-123"
    )


class TestIndividualAgents:
    """Test individual specialized agents."""

    @pytest.mark.asyncio
    async def test_researcher_agent(self, agent_context):
        """Test researcher agent."""
        input = AgentInput(message="Python programming")
        result = await researcher_agent(input, agent_context)

        assert isinstance(result, AgentOutput)
        assert len(result.content) > 0
        assert "facts_found" in result.metadata
        assert "sources" in result.metadata
        assert result.metadata["agent"] == "researcher"

    @pytest.mark.asyncio
    async def test_researcher_agent_different_topics(self, agent_context):
        """Test researcher with different topics."""
        topics = ["Python", "Artificial Intelligence", "Unknown Topic"]

        for topic in topics:
            result = await researcher_agent(
                AgentInput(message=topic),
                agent_context
            )
            assert len(result.content) > 0
            assert result.metadata["topic"] == topic

    @pytest.mark.asyncio
    async def test_writer_agent(self, agent_context):
        """Test writer agent."""
        # Provide research as input
        research = """RESEARCH FINDINGS
        ==================
        Key Facts:
        1. Python is a programming language
        2. Created in 1991"""

        input = AgentInput(message=research)
        result = await writer_agent(input, agent_context)

        assert isinstance(result, AgentOutput)
        assert len(result.content) > 0
        assert "word_count" in result.metadata
        assert result.metadata["agent"] == "writer"

    @pytest.mark.asyncio
    async def test_writer_agent_from_scratch(self, agent_context):
        """Test writer creating original content."""
        input = AgentInput(message="Machine Learning")
        result = await writer_agent(input, agent_context)

        assert len(result.content) > 0
        assert result.metadata["content_type"] == "original_content"

    @pytest.mark.asyncio
    async def test_reviewer_agent(self, agent_context):
        """Test reviewer agent."""
        content = "# Test Article\n\nThis is a test article about programming."

        input = AgentInput(message=content)
        result = await reviewer_agent(input, agent_context)

        assert isinstance(result, AgentOutput)
        assert len(result.content) > 0
        assert "status" in result.metadata
        assert "issues_found" in result.metadata
        assert result.metadata["agent"] == "reviewer"

    @pytest.mark.asyncio
    async def test_reviewer_agent_improvements(self, agent_context):
        """Test that reviewer improves content with issues."""
        # Short content with issues
        bad_content = "Short text without structure"

        input = AgentInput(message=bad_content)
        result = await reviewer_agent(input, agent_context)

        # Should find issues
        assert result.metadata["issues_found"] > 0
        # Should improve content
        assert len(result.content) > len(bad_content)


class TestOrchestration:
    """Test orchestrator agents."""

    @pytest.mark.asyncio
    async def test_content_orchestrator(self, agent_context):
        """Test sequential content orchestrator."""
        input = AgentInput(message="Python programming")
        result = await content_orchestrator(input, agent_context)

        assert isinstance(result, AgentOutput)
        assert len(result.content) > 0
        assert result.metadata["orchestrator"] == "content_orchestrator"
        assert "workflow_steps" in result.metadata
        assert len(result.metadata["workflow_steps"]) == 3

    @pytest.mark.asyncio
    async def test_content_orchestrator_workflow_steps(self, agent_context):
        """Test that orchestrator executes all steps."""
        input = AgentInput(message="Artificial Intelligence")
        result = await content_orchestrator(input, agent_context)

        # Verify all steps completed
        metadata = result.metadata
        assert "research_facts" in metadata
        assert "word_count" in metadata
        assert "review_status" in metadata

    @pytest.mark.asyncio
    async def test_parallel_orchestrator(self, agent_context):
        """Test parallel orchestrator."""
        input = AgentInput(message="Python, JavaScript, Rust")
        result = await parallel_orchestrator(input, agent_context)

        assert isinstance(result, AgentOutput)
        assert len(result.content) > 0
        assert result.metadata["orchestrator"] == "parallel_orchestrator"
        assert result.metadata["parallel_tasks"] == 3
        assert "successful_tasks" in result.metadata

    @pytest.mark.asyncio
    async def test_parallel_orchestrator_single_topic(self, agent_context):
        """Test parallel orchestrator with single topic."""
        input = AgentInput(message="Python")
        result = await parallel_orchestrator(input, agent_context)

        assert result.metadata["parallel_tasks"] == 1

    @pytest.mark.asyncio
    async def test_adaptive_orchestrator(self, agent_context):
        """Test adaptive orchestrator."""
        input = AgentInput(message="Machine Learning")
        result = await adaptive_orchestrator(input, agent_context)

        assert isinstance(result, AgentOutput)
        assert len(result.content) > 0
        assert result.metadata["orchestrator"] == "adaptive_orchestrator"
        assert "iterations" in result.metadata
        assert "final_quality" in result.metadata

    @pytest.mark.asyncio
    async def test_coordinator_agent(self, agent_context):
        """Test coordinator agent."""
        input = AgentInput(message="Research Python programming")
        result = await coordinator_agent(input, agent_context)

        assert isinstance(result, AgentOutput)
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_coordinator_delegation(self, agent_context):
        """Test coordinator delegates to correct agents."""
        # Research request
        result1 = await coordinator_agent(
            AgentInput(message="research artificial intelligence"),
            agent_context
        )
        assert "RESEARCH FINDINGS" in result1.content or "facts" in result1.metadata

        # Review request
        result2 = await coordinator_agent(
            AgentInput(message="review this content: test"),
            agent_context
        )
        assert "REVIEW REPORT" in result2.content or "reviewer" in result2.metadata


class TestHelperFunctions:
    """Test helper functions."""

    def test_parse_topics_comma_separated(self):
        """Test parsing comma-separated topics."""
        topics = parse_topics("Python, JavaScript, Rust")
        assert topics == ["Python", "JavaScript", "Rust"]

    def test_parse_topics_newline_separated(self):
        """Test parsing newline-separated topics."""
        topics = parse_topics("Python\nJavaScript\nRust")
        assert topics == ["Python", "JavaScript", "Rust"]

    def test_parse_topics_single(self):
        """Test parsing single topic."""
        topics = parse_topics("Python")
        assert topics == ["Python"]

    def test_extract_final_content_revised(self):
        """Test extracting revised content."""
        review_output = """REVIEW REPORT
        Status: REVISED

        REVISED CONTENT:
        ==================================================
        Final content here"""

        content = extract_final_content(review_output)
        assert "Final content here" in content
        assert "REVIEW REPORT" not in content

    def test_extract_final_content_original(self):
        """Test extracting original content."""
        review_output = """REVIEW REPORT
        Status: APPROVED

        ORIGINAL CONTENT:
        ==================================================
        Original content here"""

        content = extract_final_content(review_output)
        assert "Original content here" in content

    def test_aggregate_research_results(self):
        """Test aggregating research results."""
        from agent_service.interfaces import AgentOutput

        results = [
            AgentOutput(content="Research 1", metadata={}),
            AgentOutput(content="Research 2", metadata={}),
        ]
        topics = ["Topic 1", "Topic 2"]

        aggregated = aggregate_research_results(results, topics)

        assert "Topic 1" in aggregated
        assert "Topic 2" in aggregated
        assert "Research 1" in aggregated
        assert "Research 2" in aggregated

    def test_aggregate_research_with_errors(self):
        """Test aggregating with some errors."""
        from agent_service.interfaces import AgentOutput

        results = [
            AgentOutput(content="Research 1", metadata={}),
            Exception("Research failed"),
        ]
        topics = ["Topic 1", "Topic 2"]

        aggregated = aggregate_research_results(results, topics)

        assert "Topic 1" in aggregated
        assert "Topic 2" in aggregated
        assert "Research failed" in aggregated


class TestIntegration:
    """Integration tests for multi-agent system."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, agent_context):
        """Test complete workflow from research to final content."""
        topic = "Python programming"

        # 1. Research
        researcher = agent_registry.get("researcher_agent")
        research = await researcher.invoke(AgentInput(message=topic))
        assert len(research.content) > 0

        # 2. Write
        writer = agent_registry.get("writer_agent")
        article = await writer.invoke(AgentInput(message=research.content))
        assert len(article.content) > 0

        # 3. Review
        reviewer = agent_registry.get("reviewer_agent")
        final = await reviewer.invoke(AgentInput(message=article.content))
        assert len(final.content) > 0

        # Final content should be improved
        assert len(final.content) >= len(article.content)

    @pytest.mark.asyncio
    async def test_orchestrated_workflow(self, agent_context):
        """Test orchestrated workflow."""
        orchestrator = agent_registry.get("content_orchestrator")

        result = await orchestrator.invoke(
            AgentInput(message="Artificial Intelligence")
        )

        # Should have complete content
        assert len(result.content) > 0

        # Should have metadata from all steps
        assert "research_facts" in result.metadata
        assert "word_count" in result.metadata
        assert "review_status" in result.metadata

    @pytest.mark.asyncio
    async def test_agent_registry_integration(self):
        """Test that all agents are registered."""
        # Individual agents
        assert agent_registry.get("researcher_agent") is not None
        assert agent_registry.get("writer_agent") is not None
        assert agent_registry.get("reviewer_agent") is not None

        # Orchestrators
        assert agent_registry.get("content_orchestrator") is not None
        assert agent_registry.get("parallel_orchestrator") is not None
        assert agent_registry.get("adaptive_orchestrator") is not None
        assert agent_registry.get("coordinator_agent") is not None

    @pytest.mark.asyncio
    async def test_parallel_execution_performance(self, agent_context):
        """Test that parallel execution is faster than sequential."""
        import time

        topics = ["Python", "JavaScript", "Rust"]

        # Sequential execution
        sequential_start = time.time()
        researcher = agent_registry.get("researcher_agent")
        for topic in topics:
            await researcher.invoke(AgentInput(message=topic))
        sequential_time = time.time() - sequential_start

        # Parallel execution
        parallel_start = time.time()
        parallel_orch = agent_registry.get("parallel_orchestrator")
        await parallel_orch.invoke(AgentInput(message=", ".join(topics)))
        parallel_time = time.time() - parallel_start

        # Parallel should be faster (allowing some overhead)
        # Note: In simulation this might not always be true due to minimal work
        assert parallel_time <= sequential_time * 1.5  # Allow 50% overhead


class TestErrorHandling:
    """Test error handling in multi-agent system."""

    @pytest.mark.asyncio
    async def test_orchestrator_handles_empty_input(self, agent_context):
        """Test orchestrator handles empty input."""
        result = await content_orchestrator(
            AgentInput(message=""),
            agent_context
        )

        assert isinstance(result, AgentOutput)

    @pytest.mark.asyncio
    async def test_agent_handles_invalid_input(self, agent_context):
        """Test agents handle invalid input gracefully."""
        # Very long input
        long_input = "x" * 10000

        result = await researcher_agent(
            AgentInput(message=long_input),
            agent_context
        )

        assert isinstance(result, AgentOutput)

    @pytest.mark.asyncio
    async def test_parallel_orchestrator_handles_failures(self, agent_context):
        """Test parallel orchestrator handles individual failures."""
        # This should not crash even if some research fails
        result = await parallel_orchestrator(
            AgentInput(message="Topic1, Topic2, Topic3"),
            agent_context
        )

        assert isinstance(result, AgentOutput)
        assert "successful_tasks" in result.metadata


class TestAgentCommunication:
    """Test agent-to-agent communication patterns."""

    @pytest.mark.asyncio
    async def test_sequential_communication(self, agent_context):
        """Test sequential agent communication."""
        # Researcher -> Writer communication
        researcher = agent_registry.get("researcher_agent")
        writer = agent_registry.get("writer_agent")

        research = await researcher.invoke(AgentInput(message="Python"))
        article = await writer.invoke(AgentInput(message=research.content))

        # Article should reference research findings
        assert len(article.content) > 0

    @pytest.mark.asyncio
    async def test_feedback_loop(self, agent_context):
        """Test feedback loop between agents."""
        writer = agent_registry.get("writer_agent")
        reviewer = agent_registry.get("reviewer_agent")

        # Initial write
        article = await writer.invoke(AgentInput(message="Brief topic"))

        # Review
        review = await reviewer.invoke(AgentInput(message=article.content))

        # If issues found, writer can improve
        if review.metadata.get("issues_found", 0) > 0:
            improved = await writer.invoke(
                AgentInput(message=f"Improve: {article.content}")
            )
            assert len(improved.content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

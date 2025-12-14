"""
Multi-Agent System: Specialized Agents

This module contains specialized agents for different tasks:
- ResearcherAgent: Gathers information and facts
- WriterAgent: Creates well-written content
- ReviewerAgent: Reviews and improves content
"""

from typing import Any
from agent_service.interfaces import AgentInput, AgentOutput
from agent_service.agent import agent, AgentContext


# ============================================================================
# Researcher Agent
# ============================================================================


@agent(
    name="researcher_agent",
    description="Gathers information and facts about a topic"
)
async def researcher_agent(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Research agent that gathers information.

    In a real implementation, this would:
    - Search the web
    - Query databases
    - Retrieve documents
    - Compile facts and sources
    """
    topic = input.message
    ctx.logger.info("research_started", topic=topic)

    try:
        # Simulate research process
        research_data = await conduct_research(topic, ctx)

        # Compile findings
        findings = compile_research_findings(research_data)

        ctx.logger.info("research_completed", findings_count=len(research_data["facts"]))

        return AgentOutput(
            content=findings,
            metadata={
                "agent": "researcher",
                "topic": topic,
                "facts_found": len(research_data["facts"]),
                "sources": research_data["sources"]
            }
        )

    except Exception as e:
        ctx.logger.error("research_failed", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"Research failed: {str(e)}",
            metadata={"error": str(e), "agent": "researcher"}
        )


async def conduct_research(topic: str, ctx: AgentContext) -> dict[str, Any]:
    """
    Simulate research process.

    In production, replace with:
    - Web search (Google, Bing)
    - Academic databases
    - Internal knowledge bases
    - API calls to data sources
    """
    import asyncio
    await asyncio.sleep(0.5)  # Simulate research time

    topic_lower = topic.lower()

    # Simulated research results
    if "python" in topic_lower:
        return {
            "facts": [
                "Python was created by Guido van Rossum in 1991",
                "Python is known for its simple, readable syntax",
                "Python is widely used in data science, web development, and AI",
                "Python supports multiple programming paradigms",
                "Python has a large ecosystem of libraries and frameworks"
            ],
            "sources": [
                "Python.org - Official Documentation",
                "Wikipedia - Python Programming Language",
                "Real Python - Python Tutorials"
            ]
        }
    elif "ai" in topic_lower or "artificial intelligence" in topic_lower:
        return {
            "facts": [
                "AI enables machines to learn from experience",
                "Machine learning is a subset of artificial intelligence",
                "Deep learning uses neural networks with multiple layers",
                "AI applications include image recognition, NLP, and robotics",
                "AI ethics is an increasingly important consideration"
            ],
            "sources": [
                "Stanford AI Lab",
                "MIT Technology Review",
                "Nature - AI Research"
            ]
        }
    else:
        return {
            "facts": [
                f"Key information about {topic}",
                f"Historical context of {topic}",
                f"Current trends in {topic}",
                f"Future implications of {topic}"
            ],
            "sources": [
                "General Research Database",
                "Academic Journals",
                "Industry Reports"
            ]
        }


def compile_research_findings(research_data: dict) -> str:
    """Compile research findings into a formatted report."""
    findings = "RESEARCH FINDINGS\n" + "=" * 50 + "\n\n"

    findings += "Key Facts:\n"
    for i, fact in enumerate(research_data["facts"], 1):
        findings += f"{i}. {fact}\n"

    findings += "\nSources:\n"
    for source in research_data["sources"]:
        findings += f"- {source}\n"

    return findings


# ============================================================================
# Writer Agent
# ============================================================================


@agent(
    name="writer_agent",
    description="Creates well-written content from research and ideas"
)
async def writer_agent(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Writer agent that creates content.

    Input should be research findings or topic + outline.
    Output is well-structured, engaging content.
    """
    content = input.message
    ctx.logger.info("writing_started")

    try:
        # Extract topic and research if provided
        if "RESEARCH FINDINGS" in content:
            # Writing from research
            written_content = await write_from_research(content, ctx)
            content_type = "research_article"
        else:
            # Writing from scratch
            written_content = await write_original_content(content, ctx)
            content_type = "original_content"

        ctx.logger.info("writing_completed", type=content_type)

        return AgentOutput(
            content=written_content,
            metadata={
                "agent": "writer",
                "content_type": content_type,
                "word_count": len(written_content.split())
            }
        )

    except Exception as e:
        ctx.logger.error("writing_failed", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"Writing failed: {str(e)}",
            metadata={"error": str(e), "agent": "writer"}
        )


async def write_from_research(research: str, ctx: AgentContext) -> str:
    """
    Write article from research findings.

    In production, use LLM:
    ```python
    import openai

    async def write_with_llm(research, ctx):
        api_key = await ctx.get_secret("OPENAI_API_KEY")
        client = openai.AsyncOpenAI(api_key=api_key)

        prompt = f'''Based on the following research, write a comprehensive,
        engaging article. Make it informative yet accessible.

        Research:
        {research}

        Write the article:'''

        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a skilled technical writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        return response.choices[0].message.content
    ```
    """
    import asyncio
    await asyncio.sleep(0.5)

    # Extract facts from research
    facts = []
    for line in research.split("\n"):
        if line.strip() and (line[0].isdigit() or line.startswith("-")):
            facts.append(line.strip())

    # Simulated article writing
    article = "# Introduction\n\n"
    article += "This article explores the key aspects of the topic based on recent research.\n\n"

    article += "## Key Points\n\n"
    for fact in facts[:5]:  # Use top 5 facts
        cleaned_fact = fact.lstrip("0123456789.- ")
        article += f"**{cleaned_fact}**\n\n"
        article += f"This is an important aspect that demonstrates the significance of the topic. "
        article += "Understanding this helps us appreciate the broader context.\n\n"

    article += "## Conclusion\n\n"
    article += "In summary, the research reveals important insights that contribute to our understanding."

    return article


async def write_original_content(topic: str, ctx: AgentContext) -> str:
    """Write original content on a topic."""
    import asyncio
    await asyncio.sleep(0.5)

    content = f"# {topic}\n\n"
    content += "## Introduction\n\n"
    content += f"Let's explore the fascinating topic of {topic}. "
    content += "This subject has significant importance in today's world.\n\n"

    content += "## Main Discussion\n\n"
    content += f"When we examine {topic}, several key aspects emerge. "
    content += "Each of these contributes to our overall understanding.\n\n"

    content += "## Conclusion\n\n"
    content += f"In conclusion, {topic} represents an important area worthy of further exploration."

    return content


# ============================================================================
# Reviewer Agent
# ============================================================================


@agent(
    name="reviewer_agent",
    description="Reviews and improves content quality"
)
async def reviewer_agent(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Reviewer agent that reviews and improves content.

    Checks for:
    - Grammar and spelling
    - Clarity and coherence
    - Structure and organization
    - Factual accuracy
    - Tone and style
    """
    content = input.message
    ctx.logger.info("review_started", content_length=len(content))

    try:
        # Perform review
        review_results = await review_content(content, ctx)

        # Generate improved version if issues found
        if review_results["issues_found"] > 0:
            improved_content = await improve_content(content, review_results, ctx)
            status = "revised"
        else:
            improved_content = content
            status = "approved"

        # Compile review report
        report = compile_review_report(review_results, status)

        ctx.logger.info(
            "review_completed",
            status=status,
            issues=review_results["issues_found"]
        )

        return AgentOutput(
            content=f"{report}\n\n{'REVISED CONTENT' if status == 'revised' else 'ORIGINAL CONTENT'}:\n{'='*50}\n{improved_content}",
            metadata={
                "agent": "reviewer",
                "status": status,
                "issues_found": review_results["issues_found"],
                "improvements": review_results["improvements"]
            }
        )

    except Exception as e:
        ctx.logger.error("review_failed", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"Review failed: {str(e)}",
            metadata={"error": str(e), "agent": "reviewer"}
        )


async def review_content(content: str, ctx: AgentContext) -> dict[str, Any]:
    """
    Review content for quality.

    In production, use:
    - Grammar checking APIs (Grammarly, LanguageTool)
    - Style checkers
    - Plagiarism detection
    - Fact-checking services
    - LLM-based review
    """
    import asyncio
    await asyncio.sleep(0.3)

    issues = []
    improvements = []

    # Check structure
    if "# " not in content:
        issues.append("Missing clear headings/structure")
        improvements.append("Add clear headings and sections")

    # Check length
    word_count = len(content.split())
    if word_count < 50:
        issues.append("Content too brief")
        improvements.append("Expand content with more details")

    # Check for conclusion
    if "conclusion" not in content.lower():
        issues.append("Missing conclusion")
        improvements.append("Add concluding section")

    # Check for sources (if research article)
    if "research" in content.lower() and "source" not in content.lower():
        issues.append("Missing source citations")
        improvements.append("Add source citations")

    return {
        "issues": issues,
        "improvements": improvements,
        "issues_found": len(issues),
        "word_count": word_count,
        "readability_score": 75  # Simulated score
    }


async def improve_content(
    content: str,
    review_results: dict,
    ctx: AgentContext
) -> str:
    """Improve content based on review."""
    import asyncio
    await asyncio.sleep(0.2)

    improved = content

    # Add headings if missing
    if "Missing clear headings" in str(review_results["issues"]):
        if "# " not in improved:
            improved = "# Content\n\n" + improved

    # Add conclusion if missing
    if "Missing conclusion" in str(review_results["issues"]):
        improved += "\n\n## Conclusion\n\nIn summary, this analysis provides valuable insights."

    # Expand if too brief
    if "Content too brief" in str(review_results["issues"]):
        improved += "\n\nAdditional context and details enhance understanding of the topic."

    return improved


def compile_review_report(review_results: dict, status: str) -> str:
    """Compile review report."""
    report = "REVIEW REPORT\n" + "=" * 50 + "\n\n"

    report += f"Status: {status.upper()}\n"
    report += f"Word Count: {review_results['word_count']}\n"
    report += f"Readability Score: {review_results['readability_score']}/100\n"
    report += f"Issues Found: {review_results['issues_found']}\n\n"

    if review_results["issues"]:
        report += "Issues:\n"
        for issue in review_results["issues"]:
            report += f"- {issue}\n"

    if review_results["improvements"]:
        report += "\nImprovements Applied:\n"
        for improvement in review_results["improvements"]:
            report += f"- {improvement}\n"

    return report


# ============================================================================
# Example Usage
# ============================================================================


async def example_usage():
    """Demonstrate individual agent usage."""
    from agent_service.agent import agent_registry

    # Get agents
    researcher = agent_registry.get("researcher_agent")
    writer = agent_registry.get("writer_agent")
    reviewer = agent_registry.get("reviewer_agent")

    # 1. Research
    print("Step 1: Research")
    research_result = await researcher.invoke(
        AgentInput(message="Python programming")
    )
    print(research_result.content)
    print("\n" + "=" * 50 + "\n")

    # 2. Write
    print("Step 2: Write")
    write_result = await writer.invoke(
        AgentInput(message=research_result.content)
    )
    print(write_result.content)
    print("\n" + "=" * 50 + "\n")

    # 3. Review
    print("Step 3: Review")
    review_result = await reviewer.invoke(
        AgentInput(message=write_result.content)
    )
    print(review_result.content)


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())

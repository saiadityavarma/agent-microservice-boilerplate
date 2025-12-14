"""
RAG (Retrieval Augmented Generation) Agent

This example demonstrates:
- Document retrieval using semantic search
- Context-aware response generation
- Integration with vector databases
- Proper citation and source attribution
"""

from typing import AsyncGenerator
from agent_service.interfaces import AgentInput, AgentOutput, StreamChunk
from agent_service.agent import agent, streaming_agent, AgentContext


# ============================================================================
# RAG Agent
# ============================================================================


@agent(
    name="rag_agent",
    description="Retrieval Augmented Generation agent with document search"
)
async def rag_agent(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    RAG agent that retrieves relevant documents and generates responses.

    Process:
    1. Retrieve relevant documents using semantic search
    2. Rank and filter results by relevance
    3. Generate response using retrieved context
    4. Include citations and sources
    """
    query = input.message
    ctx.logger.info("rag_query_started", query=query)

    try:
        # Step 1: Search for relevant documents
        ctx.logger.info("searching_documents")
        search_results = await ctx.call_tool(
            "search_documents",
            query=query,
            top_k=5
        )

        results = search_results.get("results", [])

        if not results:
            ctx.logger.warning("no_documents_found")
            return AgentOutput(
                content="I don't have enough information to answer that question. Please add some documents to the knowledge base first.",
                metadata={"documents_found": 0}
            )

        # Step 2: Filter by relevance threshold
        relevance_threshold = 0.5
        relevant_docs = [
            doc for doc in results
            if doc.get("score", 0) >= relevance_threshold
        ]

        if not relevant_docs:
            ctx.logger.warning("no_relevant_documents")
            return AgentOutput(
                content=f"I found {len(results)} documents, but none were relevant enough to answer your question confidently.",
                metadata={
                    "documents_found": len(results),
                    "relevant_documents": 0
                }
            )

        ctx.logger.info(
            "relevant_documents_found",
            count=len(relevant_docs)
        )

        # Step 3: Build context from retrieved documents
        context = build_context(relevant_docs)

        # Step 4: Generate response with context
        response = await generate_rag_response(
            query=query,
            context=context,
            documents=relevant_docs,
            ctx=ctx
        )

        # Step 5: Add citations
        citations = build_citations(relevant_docs)

        final_response = f"{response}\n\n{citations}"

        ctx.logger.info("rag_query_completed", success=True)

        return AgentOutput(
            content=final_response,
            metadata={
                "query": query,
                "documents_retrieved": len(results),
                "documents_used": len(relevant_docs),
                "sources": [doc["metadata"] for doc in relevant_docs]
            }
        )

    except Exception as e:
        ctx.logger.error("rag_query_failed", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"I encountered an error while searching: {str(e)}",
            metadata={"error": str(e)}
        )


# ============================================================================
# Streaming RAG Agent
# ============================================================================


@streaming_agent(
    name="rag_agent_streaming",
    description="Streaming RAG agent for real-time responses"
)
async def rag_agent_streaming(
    input: AgentInput,
    ctx: AgentContext
) -> AsyncGenerator[StreamChunk, None]:
    """
    Streaming version of RAG agent.

    Streams response generation while still retrieving context first.
    """
    query = input.message
    ctx.logger.info("rag_streaming_started", query=query)

    try:
        # Step 1: Search documents (not streamed)
        yield StreamChunk(
            type="metadata",
            content="",
            metadata={"status": "searching"}
        )

        search_results = await ctx.call_tool(
            "search_documents",
            query=query,
            top_k=5
        )

        results = search_results.get("results", [])

        if not results:
            yield StreamChunk(
                type="text",
                content="I don't have enough information to answer that question."
            )
            return

        # Filter relevant documents
        relevant_docs = [
            doc for doc in results
            if doc.get("score", 0) >= 0.5
        ]

        if not relevant_docs:
            yield StreamChunk(
                type="text",
                content="I found some documents but they don't seem relevant to your question."
            )
            return

        # Build context
        context = build_context(relevant_docs)

        # Step 2: Stream response generation
        yield StreamChunk(
            type="metadata",
            content="",
            metadata={"status": "generating", "sources": len(relevant_docs)}
        )

        # Generate and stream response
        response = await generate_rag_response(
            query=query,
            context=context,
            documents=relevant_docs,
            ctx=ctx
        )

        # Stream response word by word
        words = response.split()
        for i, word in enumerate(words):
            chunk_text = word + (" " if i < len(words) - 1 else "")
            yield StreamChunk(type="text", content=chunk_text)

            import asyncio
            await asyncio.sleep(0.03)

        # Add citations
        yield StreamChunk(type="text", content="\n\n")

        citations = build_citations(relevant_docs)
        yield StreamChunk(type="text", content=citations)

        ctx.logger.info("rag_streaming_completed", success=True)

    except Exception as e:
        ctx.logger.error("rag_streaming_failed", error=str(e), exc_info=True)
        yield StreamChunk(
            type="error",
            content=f"Error: {str(e)}"
        )


# ============================================================================
# Helper Functions
# ============================================================================


def build_context(documents: list) -> str:
    """
    Build context string from retrieved documents.

    Args:
        documents: List of retrieved documents

    Returns:
        Formatted context string
    """
    context_parts = []

    for i, doc in enumerate(documents, 1):
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})
        title = metadata.get("title", f"Document {i}")

        context_parts.append(f"[{i}] {title}:\n{content}")

    return "\n\n".join(context_parts)


def build_citations(documents: list) -> str:
    """
    Build citations section from documents.

    Args:
        documents: List of documents to cite

    Returns:
        Formatted citations string
    """
    if not documents:
        return ""

    citations = ["**Sources:**"]

    for i, doc in enumerate(documents, 1):
        metadata = doc.get("metadata", {})
        title = metadata.get("title", f"Document {i}")
        category = metadata.get("category", "")
        score = doc.get("score", 0)

        citation = f"{i}. {title}"
        if category:
            citation += f" ({category})"
        citation += f" - Relevance: {score:.2f}"

        citations.append(citation)

    return "\n".join(citations)


async def generate_rag_response(
    query: str,
    context: str,
    documents: list,
    ctx: AgentContext
) -> str:
    """
    Generate response using retrieved context.

    In production, this would use an LLM like OpenAI or Anthropic:

    ```python
    import openai

    async def generate_with_openai(query, context, ctx):
        api_key = await ctx.get_secret("OPENAI_API_KEY")
        client = openai.AsyncOpenAI(api_key=api_key)

        prompt = f'''Based on the following context, answer the question.
Only use information from the context. If the context doesn't contain
enough information, say so.

Context:
{context}

Question: {query}

Answer:'''

        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for factual responses
            max_tokens=500
        )

        return response.choices[0].message.content
    ```
    """
    import asyncio
    await asyncio.sleep(0.3)  # Simulate LLM call

    # Simple rule-based response for demonstration
    query_lower = query.lower()

    # Extract key topics from documents
    topics = set()
    for doc in documents:
        content = doc.get("content", "").lower()
        if "python" in content:
            topics.add("Python")
        if "machine learning" in content or "ai" in content:
            topics.add("Machine Learning")
        if "fastapi" in content:
            topics.add("FastAPI")
        if "vector" in content and "database" in content:
            topics.add("Vector Databases")
        if "rag" in content:
            topics.add("RAG")

    # Generate response based on context
    if not topics:
        return "Based on the retrieved documents, I can provide relevant information about your query."

    topics_str = ", ".join(sorted(topics))
    response = f"Based on the retrieved documents, I can tell you about {topics_str}. "

    # Add specific information from top document
    top_doc = documents[0]
    top_content = top_doc.get("content", "")

    # Extract first sentence or up to 200 chars
    excerpt = top_content[:200]
    if len(top_content) > 200:
        excerpt += "..."

    response += f"\n\n{excerpt}"

    return response


# ============================================================================
# Document Management Agent
# ============================================================================


@agent(
    name="document_manager",
    description="Agent for adding and managing documents in the knowledge base"
)
async def document_manager(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Agent for managing documents in the knowledge base.

    Supports commands like:
    - "add: <content>" - Add a new document
    - "search: <query>" - Search documents
    - "list" - List all documents
    """
    message = input.message.strip()

    try:
        # Parse command
        if message.startswith("add:"):
            content = message[4:].strip()

            # Extract metadata if provided (title: <title> | content)
            metadata = {}
            if "|" in content:
                parts = content.split("|", 1)
                meta_part = parts[0].strip()
                content = parts[1].strip()

                # Parse metadata
                for item in meta_part.split(","):
                    if ":" in item:
                        key, value = item.split(":", 1)
                        metadata[key.strip()] = value.strip()

            result = await ctx.call_tool(
                "add_document",
                content=content,
                metadata=metadata
            )

            return AgentOutput(
                content=f"Document added successfully!\n\nDocument ID: {result['document_id']}\nChunks created: {result['chunks_created']}",
                metadata=result
            )

        elif message.startswith("search:"):
            query = message[7:].strip()

            result = await ctx.call_tool(
                "search_documents",
                query=query,
                top_k=5
            )

            # Format results
            output = f"Found {result['count']} documents:\n\n"
            for doc in result["results"]:
                title = doc["metadata"].get("title", "Untitled")
                score = doc.get("score", 0)
                content_preview = doc["content"][:100] + "..."
                output += f"- {title} (relevance: {score:.2f})\n  {content_preview}\n\n"

            return AgentOutput(content=output, metadata=result)

        else:
            return AgentOutput(
                content="""Available commands:
- add: <content> - Add a new document
- add: title: <title>, category: <cat> | <content> - Add with metadata
- search: <query> - Search documents

Example:
  add: title: Python Guide, category: programming | Python is a high-level language..."""
            )

    except Exception as e:
        ctx.logger.error("document_manager_error", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"Error: {str(e)}",
            metadata={"error": str(e)}
        )


# ============================================================================
# Example Usage
# ============================================================================


async def example_usage():
    """Demonstrate RAG agent usage."""
    from agent_service.agent import agent_registry
    from agent_service.interfaces import AgentInput

    # Get agents
    doc_manager = agent_registry.get("document_manager")
    rag = agent_registry.get("rag_agent")

    # Add some documents
    print("Adding documents...")
    await doc_manager.invoke(AgentInput(
        message="add: title: Python Basics, category: programming | Python is a high-level programming language known for its simplicity."
    ))

    # Query the knowledge base
    print("\nQuerying knowledge base...")
    result = await rag.invoke(AgentInput(
        message="What is Python?"
    ))

    print(result.content)
    print("\nMetadata:", result.metadata)


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())

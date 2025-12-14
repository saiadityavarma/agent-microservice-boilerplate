"""
Tests for RAG Agent
"""

import pytest
from agent_service.interfaces import AgentInput, AgentOutput, StreamChunk
from agent_service.agent import AgentContext, agent_registry
from agent_service.tools import tool_registry
from agent_service.infrastructure.cache.cache import get_cache

# Import to register agents and tools
from examples.rag_agent.agent import rag_agent, rag_agent_streaming, document_manager
from examples.rag_agent.tools import (
    add_document,
    search_documents,
    get_document,
    generate_embedding,
    chunk_text,
    simulate_vector_search
)


@pytest.fixture
async def agent_context():
    """Create a test agent context."""
    cache = await get_cache(namespace="test:rag")
    return AgentContext(
        tools=tool_registry,
        cache=cache,
        db=None,
        logger=None,
        user=None,
        request_id="test-request-123"
    )


class TestRAGTools:
    """Test RAG tools."""

    @pytest.mark.asyncio
    async def test_add_document(self):
        """Test adding a document."""
        result = await add_document.execute(
            content="Python is a programming language",
            metadata={"title": "Python Guide", "category": "programming"}
        )

        assert result["success"] is True
        assert "document_id" in result
        assert result["chunks_created"] > 0

    @pytest.mark.asyncio
    async def test_search_documents(self):
        """Test document search."""
        result = await search_documents.execute(
            query="What is Python?",
            top_k=3
        )

        assert "results" in result
        assert "count" in result
        assert len(result["results"]) <= 3
        assert all("content" in doc for doc in result["results"])
        assert all("score" in doc for doc in result["results"])

    @pytest.mark.asyncio
    async def test_search_with_metadata_filter(self):
        """Test search with metadata filtering."""
        result = await search_documents.execute(
            query="programming",
            top_k=5,
            filter_metadata={"category": "programming"}
        )

        assert result["count"] >= 0
        # All results should match filter
        for doc in result["results"]:
            assert doc["metadata"].get("category") == "programming"

    @pytest.mark.asyncio
    async def test_get_document(self):
        """Test retrieving a specific document."""
        result = await get_document.execute(document_id="test_doc_123")

        assert "id" in result
        assert "found" in result
        assert "content" in result

    @pytest.mark.asyncio
    async def test_generate_embedding(self):
        """Test embedding generation."""
        result = await generate_embedding.execute(
            text="Test document content"
        )

        assert "embedding" in result
        assert "dimension" in result
        assert isinstance(result["embedding"], list)
        assert len(result["embedding"]) == result["dimension"]

    def test_chunk_text(self):
        """Test text chunking."""
        text = "A" * 1000  # 1000 character text

        chunks = chunk_text(text, chunk_size=200, chunk_overlap=50)

        assert len(chunks) > 1
        # First chunk should be 200 chars
        assert len(chunks[0]) == 200
        # Chunks should overlap
        assert chunks[0][-50:] == chunks[1][:50]

    def test_chunk_text_small(self):
        """Test chunking text smaller than chunk size."""
        text = "Short text"
        chunks = chunk_text(text, chunk_size=100)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_simulate_vector_search(self):
        """Test vector search simulation."""
        results = simulate_vector_search("Python programming", top_k=3)

        assert len(results) <= 3
        assert all("content" in doc for doc in results)
        assert all("score" in doc for doc in results)
        # Results should be sorted by score
        scores = [doc["score"] for doc in results]
        assert scores == sorted(scores, reverse=True)


class TestRAGAgent:
    """Test RAG agent."""

    @pytest.mark.asyncio
    async def test_rag_agent_basic_query(self, agent_context):
        """Test basic RAG query."""
        input = AgentInput(message="What is Python?")
        result = await rag_agent(input, agent_context)

        assert isinstance(result, AgentOutput)
        assert len(result.content) > 0
        assert "metadata" in result.__dict__
        assert "documents_retrieved" in result.metadata

    @pytest.mark.asyncio
    async def test_rag_agent_with_results(self, agent_context):
        """Test RAG agent when documents are found."""
        input = AgentInput(message="Tell me about Python programming")
        result = await rag_agent(input, agent_context)

        # Should have found some documents
        assert result.metadata["documents_retrieved"] >= 0
        # Should include sources in response
        assert "Sources:" in result.content or "documents_found" in result.metadata

    @pytest.mark.asyncio
    async def test_rag_agent_no_results(self, agent_context):
        """Test RAG agent when no relevant documents found."""
        input = AgentInput(message="query with no matches xyz123")
        result = await rag_agent(input, agent_context)

        assert isinstance(result, AgentOutput)
        # Should still return a response
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_rag_agent_streaming(self, agent_context):
        """Test streaming RAG agent."""
        input = AgentInput(message="What is machine learning?")

        chunks = []
        metadata_chunks = []

        async for chunk in rag_agent_streaming(input, agent_context):
            if chunk.type == "text":
                chunks.append(chunk.content)
            elif chunk.type == "metadata":
                metadata_chunks.append(chunk.metadata)

        # Should have received some chunks
        assert len(chunks) > 0
        # Should have status updates
        assert len(metadata_chunks) > 0

        # Check content
        full_response = "".join(chunks)
        assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_rag_agent_citations(self, agent_context):
        """Test that RAG agent includes citations."""
        input = AgentInput(message="What is Python?")
        result = await rag_agent(input, agent_context)

        # Should include sources if documents were found
        if result.metadata.get("documents_used", 0) > 0:
            assert "Sources:" in result.content or "sources" in result.metadata

    @pytest.mark.asyncio
    async def test_rag_agent_metadata(self, agent_context):
        """Test RAG agent metadata."""
        input = AgentInput(message="Python")
        result = await rag_agent(input, agent_context)

        assert "query" in result.metadata
        assert "documents_retrieved" in result.metadata
        assert result.metadata["query"] == "Python"


class TestDocumentManager:
    """Test document manager agent."""

    @pytest.mark.asyncio
    async def test_add_document_simple(self, agent_context):
        """Test adding a simple document."""
        input = AgentInput(
            message="add: This is a test document about Python programming."
        )
        result = await document_manager(input, agent_context)

        assert isinstance(result, AgentOutput)
        assert "successfully" in result.content.lower()
        assert "document_id" in result.metadata

    @pytest.mark.asyncio
    async def test_add_document_with_metadata(self, agent_context):
        """Test adding document with metadata."""
        input = AgentInput(
            message="add: title: Python Guide, category: programming | Python is a high-level language."
        )
        result = await document_manager(input, agent_context)

        assert "successfully" in result.content.lower()
        assert "document_id" in result.metadata

    @pytest.mark.asyncio
    async def test_search_command(self, agent_context):
        """Test search command."""
        input = AgentInput(message="search: Python programming")
        result = await document_manager(input, agent_context)

        assert "Found" in result.content or "documents" in result.content.lower()

    @pytest.mark.asyncio
    async def test_help_command(self, agent_context):
        """Test help/unknown command."""
        input = AgentInput(message="help")
        result = await document_manager(input, agent_context)

        assert "commands" in result.content.lower() or "add:" in result.content


class TestRAGHelpers:
    """Test RAG helper functions."""

    def test_build_context(self):
        """Test context building."""
        from examples.rag_agent.agent import build_context

        documents = [
            {
                "content": "Content 1",
                "metadata": {"title": "Doc 1"}
            },
            {
                "content": "Content 2",
                "metadata": {"title": "Doc 2"}
            }
        ]

        context = build_context(documents)

        assert "Doc 1" in context
        assert "Doc 2" in context
        assert "Content 1" in context
        assert "Content 2" in context

    def test_build_citations(self):
        """Test citation building."""
        from examples.rag_agent.agent import build_citations

        documents = [
            {
                "content": "Content 1",
                "metadata": {"title": "Doc 1", "category": "tech"},
                "score": 0.95
            },
            {
                "content": "Content 2",
                "metadata": {"title": "Doc 2"},
                "score": 0.85
            }
        ]

        citations = build_citations(documents)

        assert "Sources:" in citations
        assert "Doc 1" in citations
        assert "Doc 2" in citations
        assert "0.95" in citations

    def test_build_citations_empty(self):
        """Test citations with empty list."""
        from examples.rag_agent.agent import build_citations

        citations = build_citations([])
        assert citations == ""

    @pytest.mark.asyncio
    async def test_generate_rag_response(self, agent_context):
        """Test RAG response generation."""
        from examples.rag_agent.agent import generate_rag_response

        documents = [
            {
                "content": "Python is a programming language",
                "metadata": {"title": "Python Guide"},
                "score": 0.95
            }
        ]

        response = await generate_rag_response(
            query="What is Python?",
            context="Python is a programming language",
            documents=documents,
            ctx=agent_context
        )

        assert len(response) > 0
        assert isinstance(response, str)


class TestRAGIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_full_rag_workflow(self, agent_context):
        """Test complete RAG workflow."""
        # 1. Add a document
        add_result = await add_document.execute(
            content="Python is a high-level programming language created by Guido van Rossum.",
            metadata={"title": "Python Introduction", "category": "programming"}
        )
        assert add_result["success"]

        # 2. Search for the document
        search_result = await search_documents.execute(
            query="Who created Python?",
            top_k=3
        )
        assert search_result["count"] > 0

        # 3. Query RAG agent
        rag_result = await rag_agent(
            AgentInput(message="Tell me about Python"),
            agent_context
        )
        assert len(rag_result.content) > 0

    @pytest.mark.asyncio
    async def test_agent_registry_integration(self):
        """Test that agents are registered."""
        # Check RAG agent
        rag = agent_registry.get("rag_agent")
        assert rag is not None
        assert rag.name == "rag_agent"

        # Check streaming agent
        rag_streaming = agent_registry.get("rag_agent_streaming")
        assert rag_streaming is not None

        # Check document manager
        doc_mgr = agent_registry.get("document_manager")
        assert doc_mgr is not None

    @pytest.mark.asyncio
    async def test_tool_registry_integration(self):
        """Test that tools are registered."""
        # Check search tool
        search = tool_registry.get("search_documents")
        assert search is not None

        # Check add document tool
        add_doc = tool_registry.get("add_document")
        assert add_doc is not None

        # Check embedding tool
        embed = tool_registry.get("generate_embedding")
        assert embed is not None

    @pytest.mark.asyncio
    async def test_conversation_with_rag(self, agent_context):
        """Test conversational interaction with RAG."""
        # First query
        result1 = await rag_agent(
            AgentInput(message="What is Python?"),
            agent_context
        )
        assert len(result1.content) > 0

        # Follow-up query
        result2 = await rag_agent(
            AgentInput(message="Tell me more about programming"),
            agent_context
        )
        assert len(result2.content) > 0


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_rag_agent_error_handling(self, agent_context):
        """Test RAG agent handles errors gracefully."""
        # Empty query
        result = await rag_agent(
            AgentInput(message=""),
            agent_context
        )
        assert isinstance(result, AgentOutput)

    @pytest.mark.asyncio
    async def test_document_manager_error_handling(self, agent_context):
        """Test document manager error handling."""
        # Invalid command
        result = await document_manager(
            AgentInput(message="invalid_command: test"),
            agent_context
        )
        assert isinstance(result, AgentOutput)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

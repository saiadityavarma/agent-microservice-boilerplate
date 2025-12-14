"""
RAG (Retrieval Augmented Generation) Agent Example

An agent that retrieves relevant documents and generates context-aware responses.
"""

from examples.rag_agent.agent import rag_agent, rag_agent_streaming, document_manager
from examples.rag_agent import tools

__all__ = ["rag_agent", "rag_agent_streaming", "document_manager", "tools"]

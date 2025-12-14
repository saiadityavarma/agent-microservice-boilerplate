# RAG (Retrieval Augmented Generation) Agent

A production-ready RAG agent with document retrieval and semantic search capabilities.

## Overview

This example demonstrates how to build a RAG agent that:
- Retrieves relevant documents using semantic search
- Generates context-aware responses
- Provides proper source citations
- Integrates with vector databases
- Handles document management

## What is RAG?

RAG (Retrieval Augmented Generation) is a pattern that combines:
1. **Retrieval**: Search a knowledge base for relevant information
2. **Augmentation**: Add retrieved context to the prompt
3. **Generation**: Generate responses using an LLM with the context

This allows agents to provide factual, grounded responses with citations.

## Features

- **Semantic Search**: Find documents by meaning, not just keywords
- **Document Chunking**: Automatically split large documents
- **Relevance Filtering**: Only use high-quality matches
- **Source Citations**: Include references in responses
- **Streaming Support**: Stream responses in real-time
- **Metadata Filtering**: Filter by document attributes
- **Vector Store Ready**: Easy integration with FAISS, Pinecone, Weaviate

## Files

- `agent.py` - RAG agent implementation
- `tools.py` - Document retrieval tools
- `README.md` - This file
- `test_rag_agent.py` - Tests

## Quick Start

### 1. Basic Usage

```python
import asyncio
from agent_service.interfaces import AgentInput
from agent_service.agent import agent_registry

# Import to register agents
from examples.rag_agent import agent, tools

async def main():
    # Get agents
    doc_manager = agent_registry.get("document_manager")
    rag_agent = agent_registry.get("rag_agent")

    # Add a document
    await doc_manager.invoke(AgentInput(
        message="add: title: FastAPI Guide, category: web | FastAPI is a modern Python web framework for building APIs."
    ))

    # Query
    result = await rag_agent.invoke(AgentInput(
        message="What is FastAPI?"
    ))

    print(result.content)

asyncio.run(main())
```

### 2. Streaming Responses

```python
async def streaming_example():
    rag_streaming = agent_registry.get("rag_agent_streaming")

    async for chunk in rag_streaming.stream(AgentInput(
        message="Explain machine learning"
    )):
        if chunk.type == "text":
            print(chunk.content, end="", flush=True)
        elif chunk.type == "metadata":
            print(f"\n[Status: {chunk.metadata.get('status')}]")

asyncio.run(streaming_example())
```

### 3. Adding Documents with Metadata

```python
# Add document with metadata
await doc_manager.invoke(AgentInput(
    message="add: title: ML Guide, category: ai, author: John Doe | Machine learning is a subset of AI..."
))

# Search with metadata filter
from examples.rag_agent.tools import search_documents

result = await search_documents(
    query="machine learning",
    top_k=5,
    filter_metadata={"category": "ai"}
)
```

## Vector Database Integration

### Option 1: FAISS (Local, Free)

FAISS is perfect for development and small-scale deployments.

#### Install

```bash
pip install faiss-cpu sentence-transformers
```

#### Setup

```python
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Initialize embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Create FAISS index
dimension = 384  # Model dimension
index = faiss.IndexFlatL2(dimension)

# Add documents
documents = [
    "Python is a programming language",
    "Machine learning is a subset of AI",
    "FastAPI is a web framework"
]

embeddings = model.encode(documents)
index.add(np.array(embeddings).astype('float32'))

# Save index
faiss.write_index(index, "knowledge_base.index")

# Search
query = "What is Python?"
query_embedding = model.encode([query])
distances, indices = index.search(
    np.array(query_embedding).astype('float32'),
    k=3
)

for idx in indices[0]:
    print(documents[idx])
```

#### Integration with RAG Agent

Replace `search_documents` in `tools.py`:

```python
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Global index and model
model = SentenceTransformer('all-MiniLM-L6-v2')
index = faiss.read_index("knowledge_base.index")
documents = []  # Load your documents

@tool(name="search_documents")
async def search_documents(query: str, top_k: int = 5):
    # Generate query embedding
    query_embedding = model.encode([query])

    # Search
    distances, indices = index.search(
        np.array(query_embedding).astype('float32'),
        k=top_k
    )

    # Format results
    results = []
    for idx, distance in zip(indices[0], distances[0]):
        doc = documents[idx]
        similarity = 1 / (1 + distance)  # Convert distance to similarity
        results.append({
            "content": doc["content"],
            "metadata": doc["metadata"],
            "score": float(similarity)
        })

    return {"results": results, "count": len(results)}
```

### Option 2: Pinecone (Cloud, Managed)

Pinecone is a fully-managed vector database, great for production.

#### Install

```bash
pip install pinecone-client
```

#### Setup

```python
from pinecone import Pinecone, ServerlessSpec

# Initialize
pc = Pinecone(api_key="your-api-key")

# Create index
index_name = "knowledge-base"
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=384,
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-west-2')
    )

# Get index
index = pc.Index(index_name)

# Add documents
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')

documents = [
    {"id": "doc1", "text": "Python is...", "metadata": {"category": "programming"}},
    {"id": "doc2", "text": "ML is...", "metadata": {"category": "ai"}}
]

# Upsert
vectors = []
for doc in documents:
    embedding = model.encode(doc["text"]).tolist()
    vectors.append((doc["id"], embedding, doc["metadata"]))

index.upsert(vectors=vectors)

# Query
query = "What is Python?"
query_embedding = model.encode(query).tolist()
results = index.query(vector=query_embedding, top_k=5, include_metadata=True)
```

### Option 3: Weaviate (Open Source, Self-Hosted)

Weaviate offers both cloud and self-hosted options.

#### Install

```bash
pip install weaviate-client
```

#### Setup with Docker

```bash
docker run -d \
  -p 8080:8080 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  semitechnologies/weaviate:latest
```

#### Usage

```python
import weaviate

# Connect
client = weaviate.Client("http://localhost:8080")

# Create schema
schema = {
    "class": "Document",
    "vectorizer": "text2vec-transformers",
    "properties": [
        {"name": "content", "dataType": ["text"]},
        {"name": "title", "dataType": ["string"]},
        {"name": "category", "dataType": ["string"]}
    ]
}
client.schema.create_class(schema)

# Add documents
client.data_object.create(
    {"content": "Python is...", "title": "Python Guide", "category": "programming"},
    "Document"
)

# Search
result = client.query.get("Document", ["content", "title", "category"]) \
    .with_near_text({"concepts": ["programming language"]}) \
    .with_limit(5) \
    .do()
```

## Embedding Models

### Sentence Transformers (Free, Local)

```bash
pip install sentence-transformers
```

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions
# or
model = SentenceTransformer('all-mpnet-base-v2')  # 768 dimensions

# Generate embeddings
embedding = model.encode("Your text here")
```

### OpenAI Embeddings (Paid, API)

```python
import openai

client = openai.AsyncOpenAI(api_key="sk-...")

response = await client.embeddings.create(
    model="text-embedding-3-small",  # 1536 dimensions
    input="Your text here"
)

embedding = response.data[0].embedding
```

## Document Processing

### Chunking Strategies

```python
# Simple overlap chunking (included)
from examples.rag_agent.tools import chunk_text

chunks = chunk_text(
    text="Long document...",
    chunk_size=500,
    chunk_overlap=50
)

# Sentence-based chunking
def chunk_by_sentences(text, max_chunk_size=500):
    sentences = text.split('. ')
    chunks = []
    current_chunk = []
    current_size = 0

    for sentence in sentences:
        sentence_size = len(sentence)
        if current_size + sentence_size > max_chunk_size and current_chunk:
            chunks.append('. '.join(current_chunk) + '.')
            current_chunk = [sentence]
            current_size = sentence_size
        else:
            current_chunk.append(sentence)
            current_size += sentence_size

    if current_chunk:
        chunks.append('. '.join(current_chunk) + '.')

    return chunks

# Semantic chunking (using sentence similarity)
# Install: pip install sentence-transformers numpy
from sentence_transformers import SentenceTransformer
import numpy as np

def semantic_chunk(text, similarity_threshold=0.7):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    sentences = text.split('. ')
    embeddings = model.encode(sentences)

    chunks = []
    current_chunk = [sentences[0]]

    for i in range(1, len(sentences)):
        similarity = np.dot(embeddings[i-1], embeddings[i])

        if similarity >= similarity_threshold:
            current_chunk.append(sentences[i])
        else:
            chunks.append('. '.join(current_chunk) + '.')
            current_chunk = [sentences[i]]

    if current_chunk:
        chunks.append('. '.join(current_chunk) + '.')

    return chunks
```

## Advanced Features

### Hybrid Search (Keyword + Semantic)

Combine traditional keyword search with semantic search:

```python
async def hybrid_search(query: str, top_k: int = 10):
    # Keyword search (BM25)
    keyword_results = await keyword_search(query, top_k=top_k*2)

    # Semantic search
    semantic_results = await semantic_search(query, top_k=top_k*2)

    # Combine and re-rank
    combined = merge_and_rerank(keyword_results, semantic_results, top_k)
    return combined
```

### Re-ranking

Improve results with a re-ranking model:

```bash
pip install sentence-transformers
```

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def rerank_results(query: str, results: list, top_k: int = 5):
    # Create query-document pairs
    pairs = [[query, doc["content"]] for doc in results]

    # Get scores
    scores = reranker.predict(pairs)

    # Sort by score
    for i, doc in enumerate(results):
        doc["rerank_score"] = scores[i]

    reranked = sorted(results, key=lambda x: x["rerank_score"], reverse=True)
    return reranked[:top_k]
```

## Testing

```bash
pytest examples/rag-agent/test_rag_agent.py -v
```

## Production Considerations

1. **Vector Database Selection**:
   - Small scale (<100K docs): FAISS
   - Medium scale: Weaviate (self-hosted)
   - Large scale/Production: Pinecone, Weaviate Cloud

2. **Embedding Model**:
   - Free/Fast: `all-MiniLM-L6-v2` (384 dim)
   - Better quality: `all-mpnet-base-v2` (768 dim)
   - Best quality: OpenAI `text-embedding-3-large`

3. **Chunk Size**:
   - Smaller (200-300): Better precision, more chunks
   - Larger (500-1000): Better context, fewer chunks
   - Adjust based on your documents and queries

4. **Caching**:
   - Cache embeddings for frequently accessed documents
   - Cache search results for common queries
   - Use Redis for distributed caching

5. **Monitoring**:
   - Track retrieval quality (precision, recall)
   - Monitor response times
   - Log failed retrievals
   - A/B test different chunking strategies

## Next Steps

- Integrate with real LLM (OpenAI, Anthropic)
- Add document upload endpoints
- Implement conversation memory with RAG
- Add query expansion for better retrieval
- Implement feedback loop for relevance tuning

## Related Examples

- `chatbot/` - Combine RAG with conversational interface
- `multi-agent/` - Use RAG in multi-agent systems
- `tool-use/` - Add RAG as a tool for other agents

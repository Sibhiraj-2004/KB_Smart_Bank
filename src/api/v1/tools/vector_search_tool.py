
from langchain_core.tools import tool
from src.core.db import get_vector_store
from typing import List, Dict, Any


def _vector_search_with_scores(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Vector search that returns structured results with similarity scores.
    Returns a list of dicts with rank, chunk_id, cosine_similarity, content, and metadata.
    """
    vector_store = get_vector_store(collection_name="hr_support_desk")
    
    # Try to get similarity scores, fall back to default score if not available
    try:
        vector_results = vector_store.similarity_search_with_relevance_scores(query, k=k)
    except (AttributeError, TypeError):
        # Fallback: use regular similarity search with default score
        docs = vector_store.similarity_search(query, k=k)
        vector_results = [(doc, 0.75) for doc in docs]
    
    results = []
    for rank, (doc, score) in enumerate(vector_results, start=1):
        results.append({
            "rank": rank,
            "chunk_id": doc.metadata.get("chunk_id", hash(doc.page_content) % 100000),
            "cosine_similarity": round(score, 2) if isinstance(score, float) else score,
            "content": doc.page_content,
            "metadata": {
                "page": doc.metadata.get("page", None),
                "title": doc.metadata.get("title", None),
                "source": doc.metadata.get("source", None),
            }
        })
    
    return results


# @tool
# def vector_search_tool(query: str) -> str:
#     """Semantic search using pgvector."""

#     vector_store = get_vector_store()
#     docs = vector_store.similarity_search(query, k=5)

#     if not docs:
#         return "No relevant documents found."

#     results = []
#     for doc in docs:
#         source = doc.metadata.get("source", "unknown")
#         page = doc.metadata.get("page", "unknown")
#         if page is None:
#             page = "unknown"
#         content = doc.page_content
#         results.append(f"Source: {source} - Page: {page}\nContent: {content}")

#     return "\n\n".join(results)



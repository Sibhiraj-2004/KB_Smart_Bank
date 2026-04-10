
from src.api.v1.tools.vector_search_tool import _vector_search_with_scores
from typing import List, Dict, Any


def generate_answer(query: str) -> Dict[str, Any]:
    """
    Generate answer by retrieving relevant chunks using vector search.
    Returns structured response with query and retrieved results.
    """
    
    # Get retrieved results with structured format
    retrieved_results: List[Dict[str, Any]] = _vector_search_with_scores(
        query=query,
        k=5
    )
    
    # Return response in desired format
    return {
        "query": query,
        "retrieved_results": retrieved_results
    }



"""
query_service.py

This is the single bridge between the FastAPI route and the LangGraph pipeline.

Flow:
    FastAPI  →  generate_answer()  →  rag_graph.invoke()  →  all 4 LangGraph nodes
                                        │
                                        ├─ Node 1: retriever_node   (tool selection + search)
                                        ├─ Node 2: rerank_node      (Cohere cross-encoder)
                                        ├─ Node 3: validate_node    (LLM validation + query expansion)
                                        └─ Node 4: generate_answer_node (structured LLM answer)

The full final_state is returned so Streamlit can read:
    - final_state["response"]           → AIResponse dict (answer, citations, etc.)
    - final_state["reranked_docs"]      → LangChain Document objects
    - final_state["rerank_scores"]      → Cohere relevance scores
    - final_state["retrieved_docs"]     → raw retrieval before reranking
    - final_state["retry_count"]        → how many validation retries happened
    - final_state["validation_reason"]  → why LLM passed/failed validation
    - final_state["query"]              → final (possibly expanded) query used
"""

from src.api.v1.agents.agent import rag_graph, RAGState


def run_rag_pipeline(query: str) -> RAGState:
    """
    Invoke the full LangGraph RAG pipeline and return the complete final state.

    The final state contains every intermediate output from all 4 nodes,
    not just the final answer — useful for debugging, logging, and rich UI display.
    """
    initial_state: RAGState = {
        "query": query,
        "retrieved_docs": [],
        "reranked_docs": [],
        "rerank_scores": [],
        "response": {},
        "validation_passed": False,
        "retry_count": 0,
        "validation_reason": "",
    }

    print(f"\n[pipeline] ── Starting LangGraph pipeline ──────────────────────")
    print(f"[pipeline] Query: {query}")

    final_state: RAGState = rag_graph.invoke(initial_state)

    print(f"[pipeline] ── Pipeline complete ────────────────────────────────")
    print(f"[pipeline] Retries:           {final_state['retry_count']}")
    print(f"[pipeline] Validation reason: {final_state['validation_reason']}")
    print(f"[pipeline] Docs retrieved:    {len(final_state['retrieved_docs'])}")
    print(f"[pipeline] Docs reranked:     {len(final_state['reranked_docs'])}")
    print(f"[pipeline] Final query used:  {final_state['query']}")

    return final_state


def generate_answer(query: str) -> dict:
    """
    Called by the FastAPI /query route.
    Runs the full LangGraph pipeline and returns the complete pipeline state
    including response, metrics, query expansion info, and validation details.
    """
    final_state = run_rag_pipeline(query)
    
    # Build debug response with pipeline metrics + response
    return {
        "response": final_state["response"],
        "retrieved_doc_count": len(final_state["retrieved_docs"]),
        "reranked_doc_count": len(final_state["reranked_docs"]),
        "retry_count": final_state["retry_count"],
        "validation_reason": final_state["validation_reason"],
        "original_query": query,  # Original query before any expansion
        "final_query_used": final_state["query"],  # Query after validation expansion
    }

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
        "route": "document",  
        "generated_sql": "",
        "sql_result": "",
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
    including response, metrics, query expansion info, validation details, and route.
    """
    final_state = run_rag_pipeline(query)
    
    # Build debug response with pipeline metrics + response
    return {
         "route": final_state["route"],  # Pipeline route: 'document' or 'product'
        "response": final_state["response"],
        "retrieved_doc_count": len(final_state["retrieved_docs"]),
        "reranked_doc_count": len(final_state["reranked_docs"]),
        "retry_count": final_state["retry_count"],
        "validation_reason": final_state["validation_reason"],
        "original_query": query,  # Original query before any expansion
        "final_query_used": final_state["query"],  # Query after validation expansion
       
    }
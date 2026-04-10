
import os
from typing import TypedDict, List

import cohere
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END


from src.api.v1.schemas.query_schema import AIResponse
from src.core.db import get_vector_store
os.environ["PYPPETEER_CHROMIUM_REVISION"] = "1263111"


load_dotenv(override=True)


# ── 1. State ───────────────────────────────────────────────────────────────────
# The state is the shared data that flows through the entire graph.
# Each node reads from state and returns updated state.


class RAGState(TypedDict):
   query: str
   retrieved_docs: List[Document]   # Output of Node 1 — wide retrieval (k=10)
   reranked_docs: List[Document]    # Output of Node 2 — narrowed by reranker (top_n=5)
   response: dict                   # Output of Node 5 — final structured answer
   validation_passed: bool          # Track if LLM validation succeeded
   retry_count: int                 # Track number of retries
   validation_reason: str           # LLM's reason for validation decision




# ── 2. Node 1: Vector Search ───────────────────────────────────────────────────
# Uses a bi-encoder (Google Gemini embeddings) to find semantically similar chunks.
# We retrieve k=10 to cast a wide net — the reranker will narrow this down.


def vector_search_node(state: RAGState) -> RAGState:
   vector_store = get_vector_store(collection_name="hr_support_desk")
   results = vector_store.similarity_search_with_relevance_scores(state["query"], k=10)
   # Extract documents from (doc, score) tuples
   docs = [doc for doc, score in results]
   print(f"[vector_search_node] Retrieved {len(docs)} chunks from PGVector")
   return {**state, "retrieved_docs": docs}




# ── 3. Node 2: Rerank ──────────────────────────────────────────────────────────
# Uses Cohere's cross-encoder reranker.
# Unlike bi-encoders (which embed query and doc separately),
# a cross-encoder sees query + doc TOGETHER → more accurate relevance scoring.


def rerank_node(state: RAGState) -> RAGState:
   co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))
   docs = state["retrieved_docs"]

   # Guard: Skip Cohere rerank if no documents were retrieved
   if not docs:
       print("[rerank_node] No documents retrieved; skipping rerank.")
       return {**state, "reranked_docs": []}

   rerank_response = co.rerank(
       model="rerank-english-v3.0",
       query=state["query"],
       documents=[doc.page_content for doc in docs],
       top_n=5
   )


   # Map Cohere result indices back to LangChain Document objects
   reranked_docs = [docs[r.index] for r in rerank_response.results]


   print(f"[rerank_node] Top {len(reranked_docs)} chunks after reranking:")
   for i, r in enumerate(rerank_response.results):
       print(f"  Rank {i+1} | Cohere score: {r.relevance_score:.4f} | original index: {r.index}")


   return {**state, "reranked_docs": reranked_docs}




# ── 4. Node 3: Validate Reranked Chunks with LLM & Retry Logic ────────────────
# Uses LLM to assess if retrieved documents are sufficient to answer the query.
# If validation fails and retries < max, expands query for next search iteration.


def validate_node(state: RAGState) -> RAGState:
    """Validate docs and expand query if validation fails (retry logic merged here)."""
    docs = state["reranked_docs"]
    retry_count = state.get("retry_count", 0)
    max_retries = 3

    # Guard: If no docs, validation fails
    if not docs:
        print("[validate_node] No reranked docs to validate — marking as failed.")
        validation_passed = False
        reason = "No documents retrieved"
        updated_query = state["query"]
    else:
        # Instantiate LLM once
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_LLM_MODEL"),
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

        # Prepare document summary for validation
        docs_summary = "\n---\n".join([
            f"Doc {i+1}: {doc.page_content[:200]}..." if len(doc.page_content) > 200 else f"Doc {i+1}: {doc.page_content}"
            for i, doc in enumerate(docs)
        ])

        # Validation prompt
        validation_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a document relevance validator. Assess if the provided documents are sufficient "
                "to answer the user's question. Consider: relevance, coverage, completeness, and specificity. "
                "Respond with PASS or FAIL on the first line, followed by a brief reason on the next line."
            ),
            ("human", "Question: {query}\n\nDocuments:\n{docs_summary}")
        ])
        chain = validation_prompt | llm
        response = chain.invoke({"query": state["query"], "docs_summary": docs_summary}).content.strip()

        lines = response.split("\n")
        decision = lines[0].upper().strip()
        reason = lines[1].strip() if len(lines) > 1 else decision
        validation_passed = "PASS" in decision

        print(f"[validate_node] LLM Validation: {decision}")
        print(f"[validate_node] Reason: {reason}")

        updated_query = state["query"]

        # If validation fails and retries available, expand query
        if not validation_passed and retry_count < max_retries:
            print(f"[validate_node] Retry {retry_count + 1}/{max_retries} — Expanding query...")

            expand_prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a query expansion expert. Given why the search failed, expand the query with related terms, "
                    "synonyms, and alternative phrasings. Return ONLY the expanded query, nothing else."
                ),
                ("human", "Original query: {query}\n\nValidation feedback: {feedback}")
            ])
            chain = expand_prompt | llm
            updated_query = chain.invoke({
                "query": state["query"],
                "feedback": reason
            }).content.strip()

            print(f"[validate_node] Original: {state['query']}")
            print(f"[validate_node] Expanded: {updated_query}")
        elif not validation_passed and retry_count >= max_retries:
            print(f"[validate_node] Max retries ({max_retries}) reached. Forcing validation pass.")
            validation_passed = True

    return {
        **state,
        "validation_passed": validation_passed,
        "validation_reason": reason,
        "query": updated_query,
        "retry_count": retry_count + 1
    }



# ── 5. Node 4: Generate Answer ─────────────────────────────────────────────────
# Formats the validated reranked chunks as context and calls Gemini LLM.
# Uses structured output to enforce the AIResponse schema.


def generate_answer_node(state: RAGState) -> RAGState:
   llm = ChatGoogleGenerativeAI(
       model=os.getenv("GOOGLE_LLM_MODEL"),
       google_api_key=os.getenv("GOOGLE_API_KEY")
   )
   structured_llm = llm.with_structured_output(AIResponse)

   # Guard: Return graceful empty response if no reranked docs available
   if not state.get("reranked_docs"):
       print("[generate_answer_node] No reranked docs available — returning empty answer.")
       return {**state, "response": {
           "query": state["query"],
           "answer": "No relevant documents found for the given query.",
           "policy_citations": "",
           "page_no": "",
           "document_name": ""
       }}

   context = "\n\n".join([
       f"[Source: {doc.metadata.get('source', 'unknown')} | Page: {doc.metadata.get('page', '?')}]\n{doc.page_content}"
       for doc in state["reranked_docs"]
   ])


   prompt = ChatPromptTemplate.from_messages([
       (
           "system",
           "You are a helpful assistant. Answer the user's question using only the "
           "provided context. Be precise and always cite the source document and page number."
       ),
       ("human", "Context:\n{context}\n\nQuestion: {query}")
   ])


   chain = prompt | structured_llm
   result = chain.invoke({"context": context, "query": state["query"]})


   print(f"[generate_answer_node] Answer generated.")
   return {**state, "response": result.model_dump()}







# ── 6. Router for Conditional Routing ──────────────────────────────────────────
def route_validation(state: RAGState) -> str:
   """Route to vector_search or generate based on LLM validation result."""
   if state.get("validation_passed", False):
       return "generate_answer"
   else:
       return "vector_search"


# ── 7. Build the LangGraph ────────────────────────────────────────────────────
# Simple graph with validation loop and conditional routing:
#   vector_search → rerank → validate → (if pass) generate_answer → END
#                                    → (if fail) vector_search (loop with expanded query)


def build_rag_graph():
   graph = StateGraph(RAGState)

   graph.add_node("vector_search", vector_search_node)
   graph.add_node("rerank", rerank_node)
   graph.add_node("validate", validate_node)
   graph.add_node("generate_answer", generate_answer_node)

   graph.set_entry_point("vector_search")
   graph.add_edge("vector_search", "rerank")
   graph.add_edge("rerank", "validate")
   
   # Conditional routing from validate: PASS → generate_answer, FAIL → vector_search (loop)
   graph.add_conditional_edges(
       "validate",
       route_validation,
       {"generate_answer": "generate_answer", "vector_search": "vector_search"}
   )
   
   # Generate answer leads to END
   graph.add_edge("generate_answer", END)

   return graph.compile()




# Compile once at module load — reused across all requests
rag_graph = build_rag_graph()






# ── 8. Public entrypoint (called by query_service.py) ────────────────────────
def run_vector_search_agent(query: str) -> dict:
   initial_state: RAGState = {
       "query": query,
       "retrieved_docs": [],
       "reranked_docs": [],
       "response": {},
       "validation_passed": False,
       "retry_count": 0,
       "validation_reason": ""
   }
   final_state = rag_graph.invoke(initial_state)
    

   return final_state["response"]


# ── 9. Export Mermaid Diagram ─────────────────────────────────────────────────
def export_rag_graph_as_mermaid_png(output_path: str = "src/api/v1/agents/rag_graph.png"):
   """Export the RAG graph as a Mermaid PNG diagram.
   
   Uses draw_mermaid_png() from the compiled graph. If rendering fails due to
   missing dependencies, the Mermaid source will be saved instead.
   
   Args:
       output_path: Path where the PNG will be saved (default: src/api/v1/agents/rag_graph.png)
   """
   os.makedirs(os.path.dirname(output_path), exist_ok=True)
   
   try:
       # Try to render as PNG using the graph's built-in method
       graph_image = rag_graph.get_graph().draw_mermaid_png()
       with open(output_path, "wb") as f:
           f.write(graph_image)
       print(f"Mermaid diagram PNG saved to {output_path}")
   except Exception as e:
       # Fallback: save Mermaid source code instead
       mmd_path = output_path.replace(".png", ".mmd")
       mermaid_source = rag_graph.get_graph().draw_mermaid()
       with open(mmd_path, "w", encoding="utf-8") as f:
           f.write(mermaid_source)
  


























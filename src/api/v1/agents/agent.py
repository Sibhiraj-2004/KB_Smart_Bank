
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


load_dotenv(override=True)




# ── 1. State ───────────────────────────────────────────────────────────────────
# The state is the shared data that flows through the entire graph.
# Each node reads from state and returns updated state.


class RAGState(TypedDict):
   query: str
   retrieved_docs: List[Document]   # Output of Node 1 — wide retrieval (k=10)
   reranked_docs: List[Document]    # Output of Node 2 — narrowed by reranker (top_n=3)
   response: dict                   # Output of Node 3 — final structured answer




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




# ── 4. Node 3: Generate Answer ─────────────────────────────────────────────────
# Formats the top 3 reranked chunks as context and calls Gemini LLM.
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




# ── 5. Build the LangGraph ─────────────────────────────────────────────────────
# Three nodes wired in a simple linear sequence.
#   vector_search → rerank → generate_answer → END


def build_rag_graph():
   graph = StateGraph(RAGState)


   graph.add_node("vector_search", vector_search_node)
   graph.add_node("rerank", rerank_node)
   graph.add_node("generate_answer", generate_answer_node)


   graph.set_entry_point("vector_search")
   graph.add_edge("vector_search", "rerank")
   graph.add_edge("rerank", "generate_answer")
   graph.add_edge("generate_answer", END)


   return graph.compile()




# Compile once at module load — reused across all requests
rag_graph = build_rag_graph()




# ── 6. Public entrypoint (called by query_service.py) ─────────────────────────
def run_vector_search_agent(query: str) -> dict:
   initial_state: RAGState = {
       "query": query,
       "retrieved_docs": [],
       "reranked_docs": [],
       "response": {}
   }
   final_state = rag_graph.invoke(initial_state)
   return final_state["response"]



























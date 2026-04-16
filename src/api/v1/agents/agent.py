import os
from typing import TypedDict, List, Literal, Optional

import cohere
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field as PField

from src.api.v1.schemas.query_schema import AIResponse, RerankedChunk
from src.api.v1.tools.fts_search_tool import fts_search_tool, fts_search
from src.api.v1.tools.hybrid_search_tool import hybrid_search_tool
from src.api.v1.tools.vector_search_tool import vector_search_tool
from src.core.db import get_sql_database

load_dotenv(override=True)

_TOOLS = {
    "fts_search_tool": fts_search_tool,
    "vector_search_tool": vector_search_tool,
    "hybrid_search_tool": hybrid_search_tool,
}


class RAGState(TypedDict):
    query: str
    
    sql_query: str
    rag_query: str
   
    retrieved_docs: List[Document]
    reranked_docs: List[Document]
    rerank_scores: List[float]
    # SQL branch
    generated_sql: str
    sql_result: str
    # Final output
    response: dict
    # Validation / retry
    validation_passed: bool
    retry_count: int
    validation_reason: str
    # Routing
    route: str           # "document" | "product" | "both"
    # Safety flag — set True when the query is out of scope
    out_of_scope: bool


# ── helpers ───────────────────────────────────────────────────────────────────
def _make_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=os.getenv("GOOGLE_LLM_MODEL", "gemini-3-flash-preview"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0,
    )


# ── Node 0: Router ────────────────────────────────────────────────────────────
class _RouteDecision(BaseModel):
    route: Literal["product", "document", "both", "out_of_scope"]
    reason: str
    sql_query: str = PField(
        default="",
        description=(
            "Only populated when route='both'. "
            "The sub-query that targets structured/tabular data (SQL backend)."
        ),
    )
    rag_query: str = PField(
        default="",
        description=(
            "Only populated when route='both'. "
            "The sub-query that targets unstructured/document knowledge base (RAG backend)."
        ),
    )


def router_node(state: RAGState) -> RAGState:
    """
    Classify the user query into one of four routes:

    • "product"      — targets structured/relational data only (SQL backend)
    • "document"     — targets unstructured document knowledge base only (RAG backend)
    • "both"         — requires information from BOTH sources; splits into
                       sql_query and rag_query sub-questions
    • "out_of_scope" — query is completely unrelated to any available data source
    """
    llm = _make_llm()
    structured_llm = llm.with_structured_output(_RouteDecision)

    # Retrieve a short description of what data each backend holds so the
    # prompt stays generic even when the knowledge base changes.
    sql_backend_description = os.getenv(
        "SQL_BACKEND_DESCRIPTION",
        "structured relational tables (e.g. products, orders, inventory, categories, prices)",
    )
    doc_backend_description = os.getenv(
        "DOC_BACKEND_DESCRIPTION",
        "unstructured document knowledge base (e.g. reports, policies, announcements, FAQs, manuals)",
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are a query router for an agentic RAG system that has two data backends.

SQL BACKEND  (route → "product")
─────────────────────────────────
Covers: {sql_backend_description}
Route here when the query is ENTIRELY answered by structured/tabular data —
counts, prices, stock levels, order history, aggregations, availability checks.

DOCUMENT BACKEND  (route → "document")
──────────────────────────────────────
Covers: {doc_backend_description}
Route here when the query is ENTIRELY answered by unstructured documents —
explanations, summaries, policies, narrative content, definitions.

BOTH BACKENDS  (route → "both")
────────────────────────────────
Route here ONLY when the query genuinely requires data from BOTH backends
to give a complete answer.
When you choose "both":
  • Set sql_query  = the specific sub-question targeting the SQL backend.
  • Set rag_query  = the specific sub-question targeting the document backend.
  Both sub-questions together must fully cover the original query intent.

OUT OF SCOPE  (route → "out_of_scope")
──────────────────────────────────────
Route here when the query is completely unrelated to any available data source
(e.g. general knowledge questions, personal advice, coding help, off-topic chat).

Rules
─────
• Choose EXACTLY ONE route.
• Prefer the single-backend routes ("product" or "document") unless BOTH backends
  are clearly needed.
• When in doubt between "document" and "both", prefer "document".
• Provide a one-sentence reason.
""",
        ),
        ("human", "Query: {query}"),
    ])

    decision = (prompt | structured_llm).invoke({
        "query": state["query"],
        "sql_backend_description": sql_backend_description,
        "doc_backend_description": doc_backend_description,
    })

    print(
        f"[router_node] Route='{decision.route}' | Reason: {decision.reason}"
        + (
            f"\n  sql_query : {decision.sql_query}"
            f"\n  rag_query : {decision.rag_query}"
            if decision.route == "both"
            else ""
        )
    )

    # Derive effective sub-queries (fall back to the original query when empty)
    sql_q = decision.sql_query.strip() if decision.sql_query.strip() else state["query"]
    rag_q = decision.rag_query.strip() if decision.rag_query.strip() else state["query"]

    return {
        **state,
        "route": decision.route,
        "sql_query": sql_q,
        "rag_query": rag_q,
        "out_of_scope": decision.route == "out_of_scope",
    }


def out_of_scope_node(state: RAGState) -> RAGState:
    """Return a polite refusal for queries outside the system's knowledge domain."""
    print("[out_of_scope_node] Query is out of scope — returning refusal.")
    response = {
        "query": state["query"],
        "answer": (
            "I'm sorry, I can only answer questions related to the information available "
            "in this system. Your question appears to be outside my knowledge domain. "
            "Please ask something relevant to the available data sources."
        ),
        "policy_citations": "",
        "page_no": "",
        "document_name": "",
        "reranked_chunks": [],
        "sql_query_executed": "",
    }
    return {**state, "response": response}



def nl2sql_node(state: RAGState) -> RAGState:
    """
    Translate the SQL sub-query (or the full query for product-only routes)
    into a SELECT statement, execute it, and store the raw result.

    For route == "both", the result is stored in sql_result and forwarded
    to generate_answer_node for merging with the RAG answer.
    For route == "product", a full structured answer is generated here.
    """
    # Use the dedicated sql_query when available (route == "both"),
    # otherwise fall back to the full user query (route == "product").
    effective_query = state.get("sql_query") or state["query"]

    llm = _make_llm()
    db = get_sql_database()
    schema_info = db.get_table_info()

    sql_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are a SQL expert. Given the database schema below, write a single valid
SELECT query that answers the user's question.

Rules:
- Return ONLY the raw SQL — no explanation, no markdown fences, no backticks.
- Use ONLY the tables and columns present in the schema.
- Do NOT generate INSERT, UPDATE, DELETE, DROP, or any DML/DDL statements.
- Always add LIMIT 50 unless the question explicitly asks for aggregates.
- For free-text searches, split multi-word phrases into individual keywords
  and OR them across all relevant text columns.

Database schema:
{schema}""",
        ),
        ("human", "Question: {question}"),
    ])

    raw_sql = (sql_prompt | llm).invoke({
        "schema": schema_info,
        "question": effective_query,
    })

    content = raw_sql.content
    if isinstance(content, list):
        content = "".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in content
        )
    generated_sql = content.strip().strip("```").strip()
    if generated_sql.lower().startswith("sql"):
        generated_sql = generated_sql[3:].strip()
    print(f"[nl2sql_node] Generated SQL:\n{generated_sql}")

    try:
        sql_result: str = db.run(generated_sql)
    except Exception as exc:
        sql_result = f"SQL execution error: {exc}"
    print(f"[nl2sql_node] Result : {str(sql_result)[:200]}")

    # ── "product"-only route: generate the final answer right here ──────────
    if state["route"] == "product":
        class _SQLAnswer(BaseModel):
            query: str = PField(description="The query submitted by the user")
            answer: str = PField(description="Answer based on SQL results")
            policy_citations: str = PField(description="Leave empty for SQL results")
            page_no: str = PField(description="Set to N/A for SQL results")
            document_name: str = PField(description="Name of the database or table used")

        structured_llm = llm.with_structured_output(_SQLAnswer)

        answer_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a helpful data analyst. Answer the user's question using the
SQL query results provided. Be concise and format numbers/lists clearly.
If the SQL result is an error, inform the user politely.

Safety rule: if the question has nothing to do with the data returned,
respond with "This question is outside my knowledge domain."

Set policy_citations to empty string, page_no to 'N/A',
and document_name to the main table name used in the query.""",
            ),
            (
                "human",
                "Question: {query}\n\nSQL Used:\n{sql}\n\nQuery Results:\n{result}",
            ),
        ])

        answer = (answer_prompt | structured_llm).invoke({
            "query": state["query"],
            "sql": generated_sql,
            "result": sql_result,
        })

        response = answer.model_dump()
        response["reranked_chunks"] = []
        response["sql_query_executed"] = generated_sql

        print("[nl2sql_node] Product-only answer generated.")
        return {
            **state,
            "generated_sql": generated_sql,
            "sql_result": str(sql_result),
            "response": response,
        }

    # ── "both" route: just stash the SQL result; answer generated later ──────
    print("[nl2sql_node] 'both' route — stashing SQL result for merge step.")
    return {
        **state,
        "generated_sql": generated_sql,
        "sql_result": str(sql_result),
    }



# ── Node: Retriever ───────────────────────────────────────────────────────────
def retriever_node(state: RAGState) -> RAGState:
    """
    Select the best retrieval tool for the query and return raw documents.
    All domain-specific knowledge lives in environment variables / tool
    descriptions, keeping this node fully generic.
    """
    # For "both" route use the dedicated RAG sub-query; otherwise full query.
    effective_query = (
        state.get("rag_query") or state["query"]
        if state.get("route") == "both"
        else state["query"]
    )

    llm = _make_llm()
    tools_list = [fts_search_tool, vector_search_tool, hybrid_search_tool]
    bound_llm = llm.bind_tools(tools_list)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are a retrieval assistant for a document knowledge base.
You have three search tools available. Choose EXACTLY ONE based on the query type:

- fts_search_tool    → use for exact term matches, specific identifiers, codes,
                       named entities, precise figures, or known labels.
- vector_search_tool → use for broad conceptual questions, summaries, explanations,
                       or when the user asks "what is", "describe", "how does X work".
- hybrid_search_tool → use for queries that combine specific terms with conceptual
                       context, or when both precision and semantic coverage matter.

Call exactly ONE tool with the user's query as the argument.""",
        ),
        ("human", "{query}"),
    ])

    docs: List[Document] = []

    try:
        ai_message = (prompt | bound_llm).invoke({"query": effective_query})

        if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
            for tc in ai_message.tool_calls:
                tool_name = tc["name"]
                tool_args = tc.get("args", {})
                tool_fn = _TOOLS.get(tool_name)

                if tool_fn is None:
                    print(f"[retriever_node] Unknown tool '{tool_name}'; skipping.")
                    continue

                print(f"[retriever_node] LLM chose tool: {tool_name}")
                result = tool_fn.invoke(tool_args)

                if isinstance(result, list):
                    for item in result:
                        if isinstance(item, Document):
                            docs.append(item)
                        elif isinstance(item, dict):
                            docs.append(Document(
                                page_content=item.get("content", ""),
                                metadata=item.get("metadata", {}),
                            ))
                break
        else:
            print("[retriever_node] No tool_calls returned; using fallback.")

    except Exception as e:
        print(f"[retriever_node] Tool-binding failed: {e}")

    if not docs:
        print("[retriever_node] Fallback → vector_search_tool")
        docs = vector_search_tool.invoke({"query": effective_query})

    print(f"[retriever_node] Retrieved {len(docs)} documents")
    return {**state, "retrieved_docs": docs}


# ── Node: Rerank ──────────────────────────────────────────────────────────────
def rerank_node(state: RAGState) -> RAGState:
    docs = state["retrieved_docs"]

    if not docs:
        print("[rerank_node] No documents to rerank.")
        return {**state, "reranked_docs": [], "rerank_scores": []}

    effective_query = (
        state.get("rag_query") or state["query"]
        if state.get("route") == "both"
        else state["query"]
    )

    co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))
    rerank_response = co.rerank(
        model="rerank-english-v3.0",
        query=effective_query,
        documents=[doc.page_content for doc in docs],
        top_n=5,
    )

    reranked_docs: List[Document] = []
    rerank_scores: List[float] = []

    print(f"[rerank_node] Top {len(rerank_response.results)} chunks after reranking:")
    for i, r in enumerate(rerank_response.results):
        reranked_docs.append(docs[r.index])
        rerank_scores.append(float(r.relevance_score))
        print(f"  Rank {i+1} | score={r.relevance_score:.4f} | original_idx={r.index}")

    return {**state, "reranked_docs": reranked_docs, "rerank_scores": rerank_scores}


# ── Node: Validate ────────────────────────────────────────────────────────────
def validate_node(state: RAGState) -> RAGState:
    docs = state["reranked_docs"]
    retry_count = state.get("retry_count", 0)
    max_retries = 3

    if not docs:
        if retry_count >= max_retries:
            print(f"[validate_node] No docs after {max_retries} retries — forcing PASS.")
            return {
                **state,
                "validation_passed": True,
                "validation_reason": f"No documents found after {max_retries} retries",
                "retry_count": retry_count + 1,
            }
        print(f"[validate_node] No docs (retry {retry_count}/{max_retries}) — retrying.")
        return {
            **state,
            "validation_passed": False,
            "validation_reason": "No documents retrieved",
            "retry_count": retry_count + 1,
        }

    llm = _make_llm()

    docs_summary = "\n---\n".join([
        f"Doc {i+1}: {doc.page_content[:200]}{'...' if len(doc.page_content) > 200 else ''}"
        for i, doc in enumerate(docs)
    ])

    effective_query = (
        state.get("rag_query") or state["query"]
        if state.get("route") == "both"
        else state["query"]
    )

    validation_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are a document relevance validator.
Assess whether the retrieved document chunks contain enough information
to answer the user's question.

Respond with:
  First line : PASS  (sufficient) or FAIL  (insufficient)
  Second line: one-sentence reason explaining your decision.""",
        ),
        ("human", "Question: {query}\n\nRetrieved Documents:\n{docs_summary}"),
    ])

    raw = (validation_prompt | llm).invoke({
        "query": effective_query,
        "docs_summary": docs_summary,
    }).content

    if isinstance(raw, list):
        raw = raw[0].get("text", "FAIL\nUnexpected format")
    raw = raw.strip()
    lines = raw.split("\n")
    decision = lines[0].upper().strip()
    reason = lines[1].strip() if len(lines) > 1 else decision
    validation_passed = "PASS" in decision

    print(f"[validate_node] Decision={decision} | Reason={reason}")

    updated_query = effective_query

    if not validation_passed:
        if retry_count < max_retries:
            print(f"[validate_node] Retry {retry_count + 1}/{max_retries} — expanding query…")
            expand_prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    """You are a query expansion expert.
Rewrite the query using alternative terminology, synonyms, related concepts,
and broader or narrower phrasing to improve document retrieval coverage.
Return ONLY the expanded query text — nothing else.""",
                ),
                ("human", "Original query: {query}\n\nValidation feedback: {feedback}"),
            ])
            expanded = (expand_prompt | llm).invoke({
                "query": effective_query,
                "feedback": reason,
            }).content
            if isinstance(expanded, list):
                updated_query = expanded[0].get("text", effective_query).strip()
            else:
                updated_query = expanded.strip()
            print(f"[validate_node] Expanded: {updated_query}")
            # Persist expanded query back to the correct sub-query field
            if state.get("route") == "both":
                return {
                    **state,
                    "validation_passed": False,
                    "validation_reason": reason,
                    "rag_query": updated_query,
                    "retry_count": retry_count + 1,
                }
        else:
            print(f"[validate_node] Max retries reached — forcing PASS.")
            validation_passed = True

    return {
        **state,
        "validation_passed": validation_passed,
        "validation_reason": reason,
        "query": updated_query if state.get("route") != "both" else state["query"],
        "retry_count": retry_count + 1,
    }


# ── Node: Generate Answer ─────────────────────────────────────────────────────
def generate_answer_node(state: RAGState) -> RAGState:
    """
    Unified answer generator.

    • route == "document" : synthesise answer from reranked document chunks only.
    • route == "both"     : merge SQL result + reranked document chunks into one
                            coherent answer.
    Both paths produce the same response schema.
    """
    reranked_docs: List[Document] = state.get("reranked_docs", [])
    rerank_scores: List[float] = state.get("rerank_scores", [])
    sql_result: str = state.get("sql_result", "")
    generated_sql: str = state.get("generated_sql", "")
    route: str = state.get("route", "document")

    llm = _make_llm()

    # ── Safety: nothing to work with ─────────────────────────────────────────
    if not reranked_docs and not sql_result:
        print("[generate_answer_node] No data available — returning empty answer.")
        return {
            **state,
            "response": {
                "query": state["query"],
                "answer": "I'm sorry, I was unable to find relevant information to answer your question.",
                "policy_citations": "",
                "page_no": "",
                "document_name": "",
                "reranked_chunks": [],
                "sql_query_executed": generated_sql,
            },
        }

    # ── Build context string ──────────────────────────────────────────────────
    doc_context = ""
    if reranked_docs:
        doc_context = "\n\n".join([
            f"[Source: {doc.metadata.get('source_file') or doc.metadata.get('source', 'unknown')} "
            f"| Page: {doc.metadata.get('page_number') or doc.metadata.get('page', '?')}]\n"
            f"{doc.page_content}"
            for doc in reranked_docs
        ])

    sql_context = ""
    if sql_result and route == "both":
        sql_context = (
            f"\n\n[Structured Data — SQL Result]\n"
            f"Sub-query: {state.get('sql_query', '')}\n"
            f"SQL Executed: {generated_sql}\n"
            f"Result:\n{sql_result}"
        )

    full_context = doc_context + sql_context

    # ── Structured output schema ──────────────────────────────────────────────
    class _CoreAnswer(BaseModel):
        query: str = PField(description="The query submitted by the user")
        answer: str = PField(
            description=(
                "Comprehensive answer that integrates all available context. "
                "When both document and SQL data are present, synthesise them "
                "into a single coherent response."
            )
        )
        policy_citations: str = PField(
            description=(
                "Specific references cited: section names, table rows, figures, "
                "or data points drawn from the context."
            )
        )
        page_no: str = PField(
            description="Page number(s) from source documents; 'N/A' if SQL only."
        )
        document_name: str = PField(
            description=(
                "Name(s) of source documents or tables used. "
                "List both document and table name when route is 'both'."
            )
        )

    structured_llm = llm.with_structured_output(_CoreAnswer)

    # Adjust system instruction based on what data is available
    if route == "both":
        system_instruction = (
            "You are a knowledgeable assistant with access to both structured database "
            "results and unstructured document excerpts. Answer the user's question by "
            "intelligently combining information from BOTH sources into one coherent, "
            "precise response. Clearly attribute figures and facts to their source. "
            "If any part of the question cannot be answered, say so explicitly. "
            "Do NOT answer questions that are unrelated to the provided context — "
            "respond with 'This is outside my knowledge domain.' instead."
        )
    else:
        system_instruction = (
            "You are a knowledgeable assistant. Answer the user's question using ONLY "
            "the provided document context. Be precise — include specific figures, "
            "dates, and identifiers when present. Always cite the source document "
            "name and page number. "
            "Do NOT answer questions that are unrelated to the provided context — "
            "respond with 'This is outside my knowledge domain.' instead."
        )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_instruction),
        ("human", "Context:\n{context}\n\nQuestion: {query}"),
    ])

    core: _CoreAnswer = (prompt | structured_llm).invoke({
        "context": full_context,
        "query": state["query"],
    })

    # ── Build reranked chunk list for response ────────────────────────────────
    reranked_chunks = []
    for i, (doc, score) in enumerate(zip(reranked_docs, rerank_scores), start=1):
        reranked_chunks.append(RerankedChunk(
            rank=i,
            content=doc.page_content,
            source_file=doc.metadata.get("source_file") or doc.metadata.get("source"),
            page_number=doc.metadata.get("page_number") or doc.metadata.get("page"),
            relevance_score=round(score, 4),
        ).model_dump())

    response = {
        **core.model_dump(),
        "reranked_chunks": reranked_chunks,
        "sql_query_executed": generated_sql,
    }

    print(f"[generate_answer_node] Done. Route='{route}' | Chunks: {len(reranked_chunks)}")
    return {**state, "response": response}


# ── Routing functions ─────────────────────────────────────────────────────────
def route_after_router(state: RAGState) -> str:
    """
    After the router node, direct traffic to:
      "out_of_scope" → out_of_scope_node → END
      "product"      → nl2sql_node       → END
      "document"     → retriever_node    → rerank → validate → generate_answer → END
      "both"         → nl2sql_node (stash SQL result)
                       then retriever_node → rerank → validate → generate_answer → END
    """
    return state["route"]  # "product" | "document" | "both" | "out_of_scope"


def route_after_nl2sql(state: RAGState) -> str:
    """
    After nl2sql:
    • route == "product" → answer already built → "end_direct"
    • route == "both"    → still need RAG branch → "retriever"
    """
    return "end_direct" if state["route"] == "product" else "retriever"


def route_validation(state: RAGState) -> str:
    return "generate_answer" if state.get("validation_passed", False) else "retriever"



def build_rag_graph():
    graph = StateGraph(RAGState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("router",          router_node)
    graph.add_node("out_of_scope",    out_of_scope_node)
    graph.add_node("nl2sql",          nl2sql_node)
    graph.add_node("retriever",       retriever_node)
    graph.add_node("rerank",          rerank_node)
    graph.add_node("validate",        validate_node)
    graph.add_node("generate_answer", generate_answer_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    graph.set_entry_point("router")

    # ── router → branch ───────────────────────────────────────────────────────
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "out_of_scope": "out_of_scope",
            "product":      "nl2sql",
            "document":     "retriever",
            "both":         "nl2sql",   # SQL first, then RAG
        },
    )

    # ── nl2sql → either finish (product) or continue to RAG (both) ───────────
    graph.add_conditional_edges(
        "nl2sql",
        route_after_nl2sql,
        {
            "end_direct": "generate_answer",  # product-only: answer already in state,
                                              # but we still pass through generate_answer
                                              # to keep a single END node.
            "retriever":  "retriever",        # both: proceed to RAG branch
        },
    )

    # ── RAG pipeline ──────────────────────────────────────────────────────────
    graph.add_edge("retriever", "rerank")
    graph.add_edge("rerank",    "validate")
    graph.add_conditional_edges(
        "validate",
        route_validation,
        {
            "generate_answer": "generate_answer",
            "retriever":       "retriever",
        },
    )

    # ── Single END node ───────────────────────────────────────────────────────
    graph.add_edge("out_of_scope",    END)
    graph.add_edge("generate_answer", END)

    return graph.compile()


# Compiled once at import
rag_graph = build_rag_graph()


# ── Public entrypoint ─────────────────────────────────────────────────────────
def run_vector_search_agent(query: str) -> dict:
    initial_state: RAGState = {
        "query":            query,
        "sql_query":        "",
        "rag_query":        "",
        "retrieved_docs":   [],
        "reranked_docs":    [],
        "rerank_scores":    [],
        "response":         {},
        "validation_passed": False,
        "retry_count":      0,
        "validation_reason": "",
        "route":            "",
        "generated_sql":    "",
        "sql_result":       "",
        "out_of_scope":     False,
    }
    final_state = rag_graph.invoke(initial_state)
    return final_state["response"]


# ── Export Mermaid diagram ────────────────────────────────────────────────────
def export_rag_graph_as_mermaid_png(
    output_path: str = "src/api/v1/agents/rag_graph.png",
) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        graph_image = rag_graph.get_graph().draw_mermaid_png()
        with open(output_path, "wb") as f:
            f.write(graph_image)
        print(f"[export] Mermaid PNG saved → {output_path}")
    except Exception as e:
        mmd_path = output_path.replace(".png", ".mmd")
        mermaid_source = rag_graph.get_graph().draw_mermaid()
        with open(mmd_path, "w", encoding="utf-8") as f:
            f.write(mermaid_source)
        print(f"[export] PNG render failed ({e}); Mermaid source → {mmd_path}")

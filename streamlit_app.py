"""
Multimodal Reranking Agentic RAG — Streamlit UI
Run with:  streamlit run streamlit_app.py
"""

import os
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="Regulatory Compliance RAG",
    page_icon="⚖️",
    layout="wide",
)
is_admin = st.sidebar.toggle("Admin Mode")

if is_admin:

    # ── Sidebar: Upload ────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("⚖️ Compliance RAG")
        st.caption("Multimodal · Reranking · Agentic · LangGraph")
        st.divider()

        st.subheader("📤 Upload Document")
        uploaded_file = st.file_uploader(
            "PDF or TXT only",
            type=["pdf", "txt"],
            help="Document will be parsed by Docling, chunked, embedded, and stored.",
        )

        if uploaded_file:
            if st.button("Ingest Document", type="primary", use_container_width=True):
                with st.spinner("Parsing & embedding — this may take a minute…"):
                    try:
                        resp = requests.post(
                            f"{API_BASE}/admin/upload",
                            files={"file": (uploaded_file.name, uploaded_file, uploaded_file.type)},
                            timeout=300,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            st.success(
                                f"✅ Ingested **{data['filename']}**\n\n"
                                f"- Doc ID: `{data['doc_id']}`\n"
                                f"- Chunks stored: **{data['chunks_ingested']}**"
                            )
                        else:
                            st.error(f"❌ Error {resp.status_code}: {resp.text}")
                    except requests.exceptions.ConnectionError:
                        st.error("Cannot reach the API. Is the FastAPI server running?")

        st.divider()
        if st.button("🔍 API Health Check", use_container_width=True):
            try:
                r = requests.get(f"{API_BASE}/admin/health", timeout=5)
                st.success("API online ✅") if r.status_code == 200 else st.warning(f"Status: {r.status_code}")
            except Exception:
                st.error("API unreachable")


    # ── Main Panel ────────────────────────────────────────────────────────────────
    st.title("🔎 Multimodal Reranking Agentic RAG")
    st.caption(
        "LangGraph pipeline · Cohere reranking · BM25 + vector hybrid · Docling multimodal parsing"
    )
    st.divider()

    query = st.text_area(
        "Ask a compliance question",
        placeholder="e.g. What are the capital adequacy requirements under Basel III?",
        height=100,
    )

    search_btn = st.button("🚀 Search", type="primary")

    if search_btn:
        if not query.strip():
            st.warning("Please enter a query.")
            st.stop()

        with st.spinner("Running..."):
            try:
                # Call /query/debug — returns full pipeline state + answer
                resp = requests.post(
                    f"{API_BASE}/query",
                    json={"query": query.strip()},
                    timeout=120,
                )
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach the API. Is the FastAPI server running?")
                st.stop()

        if resp.status_code != 200:
            st.error(f"API error {resp.status_code}: {resp.text}")
            st.stop()

        state = resp.json()          # PipelineDebugResponse
        data  = state["response"]    # AIResponse dict

        # ── Pipeline Mode Indicator ────────────────────────────────────────────
        pipeline_route = state.get("route", "document")
        
        if pipeline_route == "product":
            st.success("📊 SQL Mode: Answer generated from database")
        elif pipeline_route == "document":
            st.info("📄 RAG Mode: Answer generated from documents")
        
        st.divider()

        # ── Pipeline Journey Banner (Document pipeline only) ───────────────────
        if pipeline_route == "document":
            st.subheader("🗺️ Pipeline Run Summary")
            j1, j2, j3, j4 = st.columns(4)
            j1.metric("📥 Docs Retrieved", state["retrieved_doc_count"])
            j2.metric("🎯 Docs Reranked", state["reranked_doc_count"])
            j3.metric("🔁 Validation Retries", state["retry_count"])
            j4.metric("✅ Validation", "Passed")

            # Show if query was expanded during retries
            if state["final_query_used"] != state["original_query"]:
                st.info(
                    f"🔄 **Query was expanded** after validation failure:\n\n"
                    f"- **Original:** {state['original_query']}\n"
                    f"- **Expanded:** {state['final_query_used']}"
                )

            if state["validation_reason"]:
                st.caption(f"💬 Validation reason: _{state['validation_reason']}_")

            st.divider()

        # ── Answer ─────────────────────────────────────────────────────────────
        st.subheader("📋 Answer")
        st.markdown(data.get("answer", "_No answer generated._"))

        c1, c2, c3 = st.columns(3)
        c1.metric("📄 Document", data.get("document_name") or "—")
        c2.metric("📑 Page", data.get("page_no") or "—")
        c3.metric("🔖 Citation", (data.get("policy_citations") or "—")[:40])

        # ── Reranked Chunks ────────────────────────────────────────────────────
        reranked_chunks = data.get("reranked_chunks", [])
        if reranked_chunks:
            st.divider()
            st.subheader(f"🎯 Top {len(reranked_chunks)} Reranked Chunks (Cohere)")
            st.caption("Passages ranked by Cohere cross-encoder — most relevant first.")

            for chunk in reranked_chunks:
                rank    = chunk.get("rank", "?")
                score   = chunk.get("relevance_score")
                source  = chunk.get("source_file") or "unknown"
                page    = chunk.get("page_number") or "?"
                content = chunk.get("content", "")
                score_label = f"{score:.4f}" if score is not None else "N/A"

                with st.expander(
                    f"Rank #{rank}  ·  {source}  ·  Page {page}  ·  Score {score_label}",
                    expanded=(rank == 1),
                ):
                    st.progress(min(int((score or 0) * 100), 100), text=f"Relevance: {score_label}")
                    st.markdown(content)
        else:
            st.info("No reranked chunks were returned.")

        # ── Raw Debug ──────────────────────────────────────────────────────────
        with st.expander("🛠 Full Pipeline State (debug)"):
            st.json(state)
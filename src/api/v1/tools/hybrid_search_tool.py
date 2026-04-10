from langchain_core.tools import tool
from src.core.db import get_vector_store
from src.api.v1.tools.fts_search_tool import fts_search


@tool
def hybrid_search_tool(query: str) -> str:
    """Use for complex queries requiring both semantic and keyword understanding."""

    results = _hybrid_search(query)

    if not results:
        return "No hybrid results found."

    return "\n\n".join([f"{doc['content']}\nMetadata: {doc['metadata']}" for doc in results])


def _hybrid_search(query: str, k: int = 5) -> list[dict]:
   """
   Merge vector and FTS results using Reciprocal Rank Fusion (RRF).


   RRF score for a chunk = sum of 1/(rank + 60) across both result lists.
   Chunks appearing in both lists score higher than those in only one.
   The constant 60 prevents top-ranked outliers from dominating.
   """
   vector_store = get_vector_store()
   vector_docs = vector_store.similarity_search(query, k=k)
   fts_docs    = fts_search(query, k=k)

   rrf_scores: dict[str, float] = {}
   chunk_map:  dict[str, dict]  = {}

   for rank, doc in enumerate(vector_docs):
       key = doc.page_content[:120]
       rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (60 + rank + 1)
       chunk_map[key]  = {"content": doc.page_content, "metadata": doc.metadata}


   for rank, item in enumerate(fts_docs):
       key = item["content"][:120]
       rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (60 + rank + 1)
       chunk_map[key]  = {"content": item["content"], "metadata": item["metadata"]}


   ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
   return [chunk_map[key] for key, _ in ranked[:k]]




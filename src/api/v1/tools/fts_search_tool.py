from langchain_core.tools import tool
import psycopg
from psycopg.rows import dict_row

import os


_raw_conn = os.getenv("RAW_PG_CONNECTION")

@tool
def fts_search_tool(query: str) -> str:
    """Use for keyword-based search (short queries, exact terms)."""

    results = fts_search(query)

    if not results:
        return "No keyword matches found."

    return "\n\n".join([f"{doc['content']}\nMetadata: {doc['metadata']}" for doc in results])




def fts_search(query: str, k: int = 5, collection_name: str = "regulatory-compilance"):

    sql =  """
       SELECT
           e.document AS content,
           e.cmetadata AS metadata,
           ts_rank(
               to_tsvector('english', e.document),
               plainto_tsquery('english', %(query)s)
           ) AS fts_rank
       FROM  langchain_pg_embedding  e
       JOIN  langchain_pg_collection c ON c.uuid = e.collection_id
       WHERE c.name = %(collection)s
         AND to_tsvector('english', e.document)
             @@ plainto_tsquery('english', %(query)s)
       ORDER BY fts_rank DESC
       LIMIT %(k)s;
   """

    with psycopg.connect(_raw_conn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {
                "query": query,
                "collection": collection_name,
                "k": k
            })
            rows = cur.fetchall()

    return [
        {
            "content": row["content"],
            "metadata": row["metadata"],
            "fts_rank": float(row["fts_rank"]),
        }
        for row in rows
    ]
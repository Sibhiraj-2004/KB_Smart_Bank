"""
Run this to diagnose why vector_search returns 0 chunks.

    python check_db.py

It will print:
  - All collection names in langchain_pg_collection
  - Row counts per collection in langchain_pg_embedding
  - Row counts in multimodal_chunks (Docling ingestion table)
  - The value of COLLECTION_NAME env var currently set
"""

import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()

raw_conn = os.getenv("RAW_PG_CONNECTION") or os.getenv(
    "PG_CONNECTION_STRING", ""
).replace("postgresql+psycopg://", "postgresql://")

collection_env = os.getenv("COLLECTION_NAME", "regulatory_compliance")

print(f"\n{'='*60}")
print(f"  COLLECTION_NAME in .env  →  '{collection_env}'")
print(f"{'='*60}\n")

with psycopg.connect(raw_conn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:

        # 1. All collections
        cur.execute("SELECT name, uuid FROM langchain_pg_collection ORDER BY name;")
        collections = cur.fetchall()
        print(f"[langchain_pg_collection]  {len(collections)} collection(s) found:")
        for c in collections:
            print(f"    name='{c['name']}'   uuid={c['uuid']}")

        print()

        # 2. Chunk counts per collection
        cur.execute("""
            SELECT c.name, COUNT(e.id) AS chunk_count
            FROM langchain_pg_collection c
            LEFT JOIN langchain_pg_embedding e ON e.collection_id = c.uuid
            GROUP BY c.name
            ORDER BY c.name;
        """)
        counts = cur.fetchall()
        print(f"[langchain_pg_embedding]  Chunks per collection:")
        for row in counts:
            print(f"    '{row['name']}'  →  {row['chunk_count']} chunks")

        print()

        # 3. multimodal_chunks table
        try:
            cur.execute("SELECT COUNT(*) AS total FROM multimodal_chunks;")
            mc = cur.fetchone()
            print(f"[multimodal_chunks]  Total rows: {mc['total']}")
        except Exception as e:
            print(f"[multimodal_chunks]  Table not found or error: {e}")

print()
print("ACTION: Set COLLECTION_NAME in your .env to match one of the names above.")
print(f"        Currently set to: '{collection_env}'")
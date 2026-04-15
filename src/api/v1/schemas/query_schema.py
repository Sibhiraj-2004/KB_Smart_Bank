from pydantic import BaseModel, Field
from typing import Optional, List, Any


class QueryRequest(BaseModel):
    query: str = Field(..., description="User question", min_length=3)


class ChunkMetadata(BaseModel):
    page: Optional[int | str] = Field(None, description="Page number")
    title: Optional[str] = Field(None, description="Document title")
    source: Optional[str] = Field(None, description="Source file")


class RetrievedChunk(BaseModel):
    rank: int = Field(..., description="Rank of the result")
    chunk_id: int | str = Field(..., description="Unique chunk identifier")
    cosine_similarity: float = Field(..., description="Similarity score")
    content: str = Field(..., description="Chunk content")
    metadata: ChunkMetadata = Field(..., description="Chunk metadata")


class QueryResponse(BaseModel):
    query: str = Field(..., description="The user query")
    retrieved_results: List[RetrievedChunk] = Field(..., description="Retrieved and ranked results")


# ── Reranked chunk shown in final response ──────────────────────────────────
class RerankedChunk(BaseModel):
    rank: int = Field(..., description="Rerank position (1 = most relevant)")
    content: str = Field(..., description="Chunk text")
    source_file: Optional[str] = Field(None, description="Source document filename")
    page_number: Optional[int | str] = Field(None, description="Page number in source doc")
    relevance_score: Optional[float] = Field(None, description="Cohere rerank relevance score")


# ── Final answer returned by the agent ─────────────────────────────────────
class AIResponse(BaseModel):
    query: str = Field(description="The query submitted by the user")
    answer: str = Field(description="Generated answer from the LLM")
    policy_citations: str = Field(description="Cited policy or regulation reference")
    page_no: str = Field(description="Page number(s) referenced in the answer")
    document_name: str = Field(description="Name of the source document used")
    reranked_chunks: List[RerankedChunk] = Field(
        default_factory=list,
        description="Top reranked document chunks used to generate the answer"
    )


# ── Pipeline debug response with all intermediate state ─────────────────────
class PipelineDebugResponse(BaseModel):
    response: AIResponse = Field(description="Final AI-generated response")
    route: str =Field(description="Pipeline route: 'document' (RAG) or 'product' (NL2SQL)")
    retrieved_doc_count: int = Field(description="Number of documents retrieved")
    reranked_doc_count: int = Field(description="Number of documents reranked")
    retry_count: int = Field(description="Number of validation retries")
    validation_reason: str = Field(description="Reason from validation step")
    original_query: str = Field(description="Original user query")
    final_query_used: str = Field(description="Final query after expansion (if any)")
   
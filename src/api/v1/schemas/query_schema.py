from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        description="User question",
        min_length=3
    )

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
    retrieved_results: List[RetrievedChunk] = Field(
        ..., 
        description="Retrieved and ranked results"
    )
    

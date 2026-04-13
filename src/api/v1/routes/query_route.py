from fastapi import APIRouter, HTTPException

from src.api.v1.schemas.query_schema import PipelineDebugResponse, QueryRequest
from src.api.v1.services.query_service import generate_answer

router = APIRouter()


@router.post("/query", response_model=PipelineDebugResponse)
def query_endpoint(request: QueryRequest):
    """Run the agentic RAG pipeline and return full pipeline state with metrics + answer."""
    try:
        return generate_answer(query=request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
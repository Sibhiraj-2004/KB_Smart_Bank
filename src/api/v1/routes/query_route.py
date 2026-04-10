from fastapi import APIRouter
from src.api.v1.services.query_service import generate_answer
from src.api.v1.schemas.query_schema import QueryRequest, QueryResponse

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def query_endpoint(request: QueryRequest):
    return generate_answer(
        query=request.query
    )






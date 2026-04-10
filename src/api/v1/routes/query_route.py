from fastapi import APIRouter
from src.api.v1.services.query_service import generate_answer
from src.api.v1.schemas.query_schema import QueryRequest, AIResponse

router = APIRouter()

@router.post("/query", response_model=AIResponse)
def query_endpoint(request: QueryRequest):
    return generate_answer(
        query=request.query
    )






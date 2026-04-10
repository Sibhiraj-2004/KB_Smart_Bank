from fastapi import FastAPI
from src.api.v1.routes.query_route import router as query_router
app = FastAPI()


@app.get("/")
def read_root():
    return {
        "message":"reranking rag system implementation"
    }


@app.get("/health")
def health_check():
    return {
        "status":"ok"
    }



app.include_router(query_router, prefix="/api/v1")

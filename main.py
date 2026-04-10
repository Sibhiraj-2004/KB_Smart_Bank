from fastapi import FastAPI
from src.api.v1.agents.agent import export_rag_graph_as_mermaid_png
from src.api.v1.routes.query_route import router as query_router
app = FastAPI()



export_rag_graph_as_mermaid_png()

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

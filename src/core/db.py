import os
from dotenv import load_dotenv
from langchain_postgres import PGVector
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()
PG_CONNECTION = os.getenv("PG_CONNECTION_STRING")

from langchain_openai import OpenAIEmbeddings,ChatOpenAI

def get_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model=os.getenv("GOOGLE_EMBEDDING_MODEl"),  
        api_key=os.getenv("GOOGLE_API_KEY"),
        output_dimensionality=1536
    )


def get_vector_store(collection_name : str = "regulatory_compliance"):
    return  PGVector(
        collection_name=collection_name,
        connection=PG_CONNECTION,
        embeddings=get_embeddings(),
        use_jsonb=True

    )


def get_llm():
    return ChatGoogleGenerativeAI(
        model="google_genai:gemini-3.1-flash-lite-preview", 
        api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.3
    )




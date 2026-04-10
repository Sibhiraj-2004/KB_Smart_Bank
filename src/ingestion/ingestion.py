from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.core.db import get_vector_store

import os
load_dotenv()


def ingest_file(file_path: str, filename: str, regulation_type: str | None = None):
    """Ingest PDF/TXT and store in pgvector."""

  
    if filename.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    else:
        loader = TextLoader(file_path)

    docs = loader.load()

    print("pages:", len(docs))

   
    for doc in docs:
        page = doc.metadata.get("page")
        doc.metadata.update({
            "source": filename,
            "document_extension": filename.split(".")[-1],
            "page": (page if page is not None else 0) + 1,
            "created_at": os.path.getctime(file_path),
            "last_updated": os.path.getmtime(file_path),
             
        })


    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = splitter.split_documents(docs)

    print("chunks:", len(chunks))


    vector_store = get_vector_store(collection_name="hr_support_desk")
    vector_store.add_documents(chunks)


if __name__ == "__main__":
    # ingest_file("data\RIL-Media-Release-RIL-Q2-FY2024-25-mini.pdf", "RIL-Media-Release-RIL-Q2-FY2024-25-mini.pdf")
    ingest_file("data\HR_Knowledge_Base_2025.pdf", "HR_Knowledge_Base_2025.pdf")
    ingest_file("data\HR_Knowledge_Base_2026.pdf", "HR_Knowledge_Base_2026.pdf")
    
    print("ingestion completed successfully!")


   
# 🤖 Reranking RAG System - Multimodal Regulatory Compliance AI

A powerful **Retrieval-Augmented Generation (RAG)** system that uses AI agents, semantic search, and intelligent reranking to answer questions about regulatory compliance documents. This system combines multiple search techniques with LangGraph orchestration and Cohere reranking to deliver accurate, well-cited answers.

---

## 📋 Table of Contents

1. [What is This Project?](#what-is-this-project)
2. [Quick Start](#quick-start)
3. [Architecture & How It Works](#architecture--how-it-works)
4. [Project Structure](#project-structure)
5. [Installation](#installation)
6. [Usage](#usage)
7. [API Endpoints](#api-endpoints)
8. [Key Components Explained](#key-components-explained)
9. [Technologies Used](#technologies-used)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 What is This Project?

### The Problem We Solve
Imagine you have thousands of pages of regulatory documents (PDFs, compliance manuals, legal documents). You want to ask questions like:
- *"What are the penalties for non-compliance?"*
- *"What documents do I need to submit?"*
- *"What are the requirements for category X?"*

Manually searching through all documents would take forever. This project **automates that process** using AI.

### The Solution
This is a **smart document search and answer system** that:
1. 📄 **Ingests documents** (PDFs, TXT) and breaks them into chunks
2. 🔍 **Stores them intelligently** in a PostgreSQL database with multiple search indexes
3. 🧠 **Uses an AI agent** to decide which search method to use (keyword, semantic, or hybrid)
4. 🔄 **Reranks results** using Cohere's AI to find the MOST relevant chunks
5. ✍️ **Generates answers** using Google's Gemini AI with proper citations

---

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- PostgreSQL database
- Google API key (for Gemini LLM)
- Cohere API key (for reranking)

### Setup (5 minutes)

```bash
# 1. Clone and navigate to project
cd reranking-rag-system

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -e .

# 4. Create .env file with your API keys
echo "GOOGLE_API_KEY=your_key_here" > .env
echo "COHERE_API_KEY=your_key_here" >> .env
echo "PG_CONNECTION_STRING=postgresql://user:pass@localhost/rag_db" >> .env

# 5. Start the API server
uvicorn main:app --reload

# 6. In another terminal, start the Streamlit UI
streamlit run streamlit_app.py
```

Visit:
- 🌐 **UI**: http://localhost:8501
- 🔌 **API**: http://localhost:8000/docs

---

## 🏗️ Architecture & How It Works

### The Flow (Step-by-Step)

```
┌─────────────────────────────────────────────────────────────┐
│  1. USER UPLOADS A DOCUMENT                                  │
│     (PDF or TXT file)                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  2. DOCUMENT PARSING (Docling Parser)                       │
│  ├─ Extract text from PDF                                    │
│  ├─ Preserve structure (headings, tables, images)           │
│  ├─ Split into chunks (300-500 words each)                  │
│  └─ Extract tables and images as base64                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  3. VECTOR EMBEDDING & STORAGE                              │
│  ├─ Convert text chunks to embeddings (Google's model)      │
│  ├─ Store in PostgreSQL with pgvector                       │
│  ├─ Create full-text search index                           │
│  └─ Metadata: source, page number, content type            │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┴──────────────┐
         │                            │
         ▼                            ▼
    DATA STORED                 READY FOR QUERIES
```

### Query Processing (The Main Flow)

```
┌────────────────────────────────────┐
│  USER ASKS A QUESTION              │
│  "What are the penalties?"         │
└────────────┬───────────────────────┘
             │
             ▼
    ┌─────────────────────────┐
    │ NODE 1: RETRIEVER       │ ⭐ Key Insight:
    │ ─────────────────────── │ The AI agent CHOOSES which
    │ LLM decides which       │ search method to use based
    │ search tool to use:     │ on the question type
    │ • FTS (keyword search)  │
    │ • Vector (semantic)     │ Example:
    │ • Hybrid (both)         │ - "penalties" → FTS
    │                         │ - "What does X mean?" → Vector
    │ Retrieves k=10 docs     │ - Complex → Hybrid
    └────────┬────────────────┘
             │
             ▼
    ┌─────────────────────────┐
    │ NODE 2: RERANKER        │ ⭐ Key Insight:
    │ ─────────────────────── │ Not all top 10 results are
    │ Cohere reranks docs:    │ equally relevant. Cohere's
    │ • Scores relevance      │ AI cross-encoder re-ranks
    │   (0-1 scale)           │ them to find the BEST 5
    │ • Keeps top 5           │
    │ • Returns relevance     │ This is what makes the
    │   scores                │ answers better!
    └────────┬────────────────┘
             │
             ▼
    ┌─────────────────────────┐
    │ NODE 3: VALIDATOR       │ ⭐ Key Insight:
    │ ─────────────────────── │ Double-check if the answer
    │ LLM validates results:  │ makes sense. If not, try
    │ • Do we have enough     │ again with expanded query
    │   context to answer?    │
    │ • Is query too vague?   │ Retries up to 3 times
    │ • Expands query if      │ to find better results
    │   needed                │
    └────────┬────────────────┘
             │
             ▼
    ┌─────────────────────────┐
    │ NODE 4: ANSWER GEN      │ ⭐ Key Insight:
    │ ─────────────────────── │ Generate a structured
    │ Gemini generates:       │ answer with citations
    │ • Direct answer         │
    │ • Reasoning/context     │ Users know WHERE the
    │ • Source citations      │ info came from
    │ • JSON structure        │
    └────────┬────────────────┘
             │
             ▼
    ┌────────────────────────────────────┐
    │  RETURN RESULT TO USER             │
    │  ├─ Answer text                     │
    │  ├─ Source documents (with scores)  │
    │  ├─ Confidence/validation status    │
    │  └─ Reranking scores                │
    └────────────────────────────────────┘
```

---

## 📁 Project Structure

```
reranking-rag-system/
│
├── main.py                          # FastAPI application entry point
├── streamlit_app.py                 # Web UI for users
├── pyproject.toml                   # Python dependencies
├── README.md                        # This file
│
├── src/
│   │
│   ├── api/v1/                      # FastAPI API layer
│   │   │
│   │   ├── agents/
│   │   │   ├── agent.py             # 🧠 LangGraph RAG pipeline (4 nodes)
│   │   │   └── rag_graph.mmd        # Visual diagram of RAG flow
│   │   │
│   │   ├── routes/
│   │   │   ├── query_route.py       # API endpoint: /query
│   │   │   └── upload_route.py      # API endpoint: /upload
│   │   │
│   │   ├── services/
│   │   │   └── query_service.py     # Bridge between API and RAG pipeline
│   │   │
│   │   ├── schemas/
│   │   │   └── query_schema.py      # Data structures (AIResponse, etc.)
│   │   │
│   │   └── tools/
│   │       ├── fts_search_tool.py   # 🔍 Full-text search (keyword-based)
│   │       ├── vector_search_tool.py # 🧠 Semantic search (meaning-based)
│   │       └── hybrid_search_tool.py # 🔄 Hybrid search (both methods)
│   │
│   ├── core/
│   │   ├── db.py                    # Database connection & models
│   │   └── check_db.py              # Utility to verify DB setup
│   │
│   └── ingestion/
│       ├── docling_parser.py        # PDF/TXT parser (Docling)
│       └── ingestion.py             # Document upload & storage pipeline
│
├── data/
│   ├── images/                      # Profile/asset images
│   └── uploads/                     # Temporary upload storage
```

### What Each File Does (Beginner Guide)

| File | Purpose | What You Need to Know |
|------|---------|----------------------|
| `main.py` | FastAPI setup | Starts the API server |
| `streamlit_app.py` | User interface | Pretty web interface |
| `agent.py` | 🧠 The brain | Orchestrates the 4-step process |
| `query_service.py` | 🌉 Bridge | Connects FastAPI to RAG pipeline |
| `*_search_tool.py` | 🔍 Search methods | Different ways to find docs |
| `docling_parser.py` | 📄 Document reader | Extracts text from PDFs |
| `db.py` | 💾 Database | Stores and retrieves data |

---

## 💾 Installation

### Step 1: Clone Repository
```bash
git clone <repo-url>
cd reranking-rag-system
```

### Step 2: Python Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\activate

# Or on Mac/Linux
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
# Install from pyproject.toml
pip install -e .

# Or manually:
# pip install fastapi uvicorn langchain cohere docling streamlit
```

### Step 4: Environment Variables
Create `.env` file in project root:

```env
# Google Gemini LLM
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_LLM_MODEL=gemini-1.5-flash

# Cohere Reranking
COHERE_API_KEY=your_cohere_api_key_here

# PostgreSQL Database
PG_CONNECTION_STRING=postgresql+psycopg://user:password@localhost:5432/rag_db
# Alternative (raw connection):
RAW_PG_CONNECTION=postgresql://user:password@localhost:5432/rag_db

# API Configuration
API_BASE_URL=http://localhost:8000/api/v1
```

### Step 5: PostgreSQL Setup
```bash
# Create database
createdb rag_db

# Verify connection
psql -U user -d rag_db -c "SELECT version();"
```

---

## 📖 Usage

### Method 1: Streamlit Web UI (Easiest for Users)

```bash
# Terminal 1: Start API
uvicorn main:app --reload

# Terminal 2: Start UI
streamlit run streamlit_app.py

# Visit: http://localhost:8501
```

**How to use:**
1. Click "Upload Document" sidebar
2. Select PDF or TXT file
3. Click "Ingest Document" button
4. Wait for processing
5. Type your question in the main area
6. Get answer with sources!

### Method 2: FastAPI REST API

#### Upload a Document
```bash
curl -X POST "http://localhost:8000/api/v1/admin/upload" \
  -F "file=@compliance_guide.pdf"
```

**Response:**
```json
{
  "filename": "compliance_guide.pdf",
  "doc_id": "doc_123abc",
  "chunks_ingested": 47,
  "status": "success"
}
```

#### Query for Answers
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the penalties for non-compliance?"}'
```

**Response:**
```json
{
  "query": "What are the penalties for non-compliance?",
  "answer": "According to Section 2.3...",
  "confidence": 0.92,
  "sources": [
    {
      "content": "Penalties include fines up to...",
      "page": 5,
      "score": 0.95
    }
  ]
}
```

### Method 3: Python Script
```python
from src.api.v1.services.query_service import run_rag_pipeline

# Run the pipeline
result = run_rag_pipeline("What are the requirements?")

# Access results
print(f"Answer: {result['response']['answer']}")
print(f"Sources: {result['reranked_docs']}")
print(f"Confidence scores: {result['rerank_scores']}")
```

---

## 🔌 API Endpoints

### Base URL
```
http://localhost:8000/api/v1
```

### Endpoints

#### 1. Health Check
```http
GET /health
```
Returns: `{"status": "ok"}`

#### 2. Upload Document
```http
POST /admin/upload
Content-Type: multipart/form-data

Body:
  file: <binary PDF or TXT>
```

Returns:
```json
{
  "filename": "string",
  "doc_id": "string",
  "chunks_ingested": "integer",
  "status": "success|error"
}
```

#### 3. Query for Answers
```http
POST /query
Content-Type: application/json

Body:
{
  "query": "Your question here",
  "top_n": 5  (optional, default=5)
}
```

Returns:
```json
{
  "query": "Your question here",
  "answer": "Generated answer...",
  "confidence": 0.85,
  "reasoning": "Why this answer...",
  "sources": [
    {
      "content": "Relevant text...",
      "source_file": "document.pdf",
      "page": 3,
      "score": 0.92
    }
  ],
  "validation_passed": true,
  "retry_count": 0
}
```

---

## 🔧 Key Components Explained

### 1️⃣ **Document Ingestion Pipeline** (`src/ingestion/`)

```
What happens when you upload a PDF?

PDF File
   │
   ▼
Docling Parser ─────────────────────────
   │ • Read PDF content
   │ • Extract tables
   │ • Extract images
   │ • Detect headings/structure
   │
   ▼
Chunk Text (300-500 words per chunk)
   │ • Break into manageable pieces
   │ • Keep together: heading + content
   │ • Preserve: page number, section
   │
   ▼
Generate Embeddings (Google API)
   │ • Convert text to 768-dim vector
   │ • Same model for consistency
   │ • Enables semantic search
   │
   ▼
Store in PostgreSQL
   ├─ Vector embedding (pgvector type)
   ├─ Full-text search index (tsvector)
   ├─ Metadata (source, page, type)
   └─ Ready for queries!
```

**Key File: `docling_parser.py`**
- `parse_document(file_path)` → Returns list of dicts with chunks
- Each chunk has: `content`, `metadata`, `embedding`

### 2️⃣ **Three Search Methods** (`src/api/v1/tools/`)

#### Option A: Full-Text Search (FTS)
```
Query: "penalties for violation"
       │
       ▼
PostgreSQL FTS (tsvector)
       │
       ├─ Find: "penalties"
       ├─ Find: "violation"
       ├─ Find: variations/stemming
       │
       ▼
Return: Exact matches (documents containing these words)

BEST FOR:
✓ Specific terms, codes, acronyms
✓ Regulatory numbers
✗ Conceptual questions
```

**Example:**
```python
from src.api.v1.tools.fts_search_tool import fts_search_tool

# This searches for exact keywords
results = fts_search_tool.invoke({
    "query": "Section 2.3 penalties"
})
# Returns: 10 documents ranked by keyword relevance
```

#### Option B: Vector/Semantic Search
```
Query: "What does X mean?"
       │
       ▼
Embed query to vector (768 dimensions)
       │
       ▼
PostgreSQL pgvector (cosine similarity)
       │
       ├─ Find similar vectors
       ├─ Using: vector1 <=> vector2
       │
       ▼
Return: Semantically similar documents

BEST FOR:
✓ Conceptual questions
✓ Paraphrasing
✓ "Explain X"
✗ Specific numeric values
```

**Example:**
```python
from src.api.v1.tools.vector_search_tool import vector_search_tool

# This searches for meaning
results = vector_search_tool.invoke({
    "query": "What are the main requirements?"
})
# Returns: 10 semantically similar documents
```

#### Option C: Hybrid Search
```
Query: "Complex question about specific penalties"
       │
       ▼
BOTH FTS AND VECTOR SEARCH
       │
       ├─ FTS score: matches keywords
       ├─ Vector score: semantic match
       │
       ▼
Combine scores (weights 0.5 FTS + 0.5 vector)
       │
       ▼
Return: Best of both worlds

BEST FOR:
✓ Complex questions
✓ Needs precision + understanding
✓ Most questions!
```

### 3️⃣ **The LangGraph Agent** (`src/api/v1/agents/agent.py`)

This is the **brain** of the system. It orchestrates 4 steps:

#### Node 1: RETRIEVER (Smart Tool Selection)
```python
# The LLM reads the question and decides:
if "exact code" in query:
    use_tool = fts_search_tool
elif "what does" in query or "explain" in query:
    use_tool = vector_search_tool
else:
    use_tool = hybrid_search_tool

# Then retrieves k=10 documents
retrieved_docs = use_tool.invoke(query)
```

**Why?** Different questions need different search methods!

**Example:**
- Q: "What is code A234?" → FTS (specific code)
- Q: "How do penalties work?" → Vector (understanding)
- Q: "Explain code A234 and its penalties" → Hybrid (both)

#### Node 2: RERANKER (AI Quality Filter)
```python
# Cohere AI reranks the 10 docs
# Scores each: 0 (bad) ← → 1 (perfect)

Before reranking:
[doc1=0.45, doc2=0.42, doc3=0.98, ..., doc10=0.15]

After reranking:
[doc3=0.98, doc1=0.45, doc2=0.42, ..., doc10=0.15]

# Keeps only top_n=5
reranked = [doc3, doc1, doc2, doc7, doc8]
```

**Why?** Just because a document has keywords doesn't mean it's the BEST answer.

**Analogy:** Imagine searching Google:
- Before reranking: All pages with your keywords
- After reranking: Most relevant pages first

#### Node 3: VALIDATOR (Quality Check)
```python
# LLM checks: "Is this enough to answer?"

If reranked_docs are good:
    validation_passed = True
    go to answer generation
Else:
    # Expand the query, try again
    expanded_query = llm.expand_query(query)
    retry_count += 1
    if retry_count < 3:
        go back to Node 1 with expanded query
    else:
        validation_passed = False
```

**Why?** Sometimes all docs are bad. Try again with modified query.

#### Node 4: ANSWER GENERATION (Structured Response)
```python
# Gemini LLM generates answer using:
# 1. Original query
# 2. Top 5 reranked documents
# 3. System prompt with instructions

Generated response includes:
{
  "answer": "Direct answer to the question",
  "reasoning": "Why this answer",
  "confidence": 0.85,
  "sources": ["book page 5", "section 2.3"],
  "citations": [{"text": "...", "source": "...", "score": 0.92}]
}
```

**Why?** Structured, cited answers are:
- Traceable (users see WHERE info came from)
- Verifiable (sources can be checked)
- Professional (structured format)

---

## 🛠️ Technologies Used

### Core AI/ML
| Tech | Purpose | Why It's Good |
|------|---------|--------------|
| **LangGraph** | Orchestrate pipeline | State machines for AI workflows |
| **LangChain** | LLM integrations | Abstracts different AI models |
| **Google Gemini** | LLM for answers | Powerful, fast, reliable |
| **Cohere** | Reranking | Specialized in doc relevance |
| **Docling** | PDF parsing | Preserves structure + tables |

### Data Storage
| Tech | Purpose | Why It's Good |
|------|---------|--------------|
| **PostgreSQL** | Main database | Reliable, open-source |
| **pgvector** | Vector storage | Performs cosine similarity search |
| **Full-text search** | Keyword indexing | Fast keyword matching |

### Web Framework
| Tech | Purpose | Why It's Good |
|------|---------|--------------|
| **FastAPI** | REST API | Modern, fast, auto-docs |
| **Streamlit** | Web UI | No frontend coding needed |
| **Uvicorn** | ASGI server | Async support |

### Python Libraries
```
cohere>=6.0.0              # Reranking
docling>=2.86.0            # PDF parsing
fastapi>=0.135.3           # Web framework
langchain>=1.2.15          # LLM tools
langchain-google-genai>=4.2.1  # Gemini integration
langchain-postgres>=0.0.17 # PostgreSQL integration
langchain-openai>=1.1.12   # OpenAI support
streamlit>=1.56.0          # Web UI
uvicorn>=0.44.0            # Server
```

---

## 🐛 Troubleshooting

### "Cannot reach the API"
**Problem:** Streamlit can't connect to FastAPI

**Solution:**
```bash
# Terminal 1: Start API
uvicorn main:app --reload --host 0.0.0.0

# Check if running
curl http://localhost:8000/health
```

### "No documents found"
**Problem:** Query returns empty results

**Reasons & fixes:**
1. **No documents uploaded yet**
   - Upload at least one document via Streamlit UI
   
2. **Wrong database connection**
   - ✅ Check `.env` file has `PG_CONNECTION_STRING`
   - ✅ Verify database exists: `psql -l`
   
3. **Query too specific**
   - Try simpler terms
   - The system will retry with expanded query

### "API Key error"
**Problem:** `Missing API key for GOOGLE_API_KEY`

**Solution:**
```bash
# 1. Get API key from https://ai.google.dev
# 2. Add to .env
echo "GOOGLE_API_KEY=your_key_here" >> .env

# 3. Restart API
# Ctrl+C to stop, then run again
uvicorn main:app --reload
```

### "PostgreSQL connection failed"
**Problem:** `Connection refused` error

**Solution:**
```bash
# 1. Is PostgreSQL running?
# Windows: Check Services app
# Mac: brew services list
# Linux: sudo systemctl status postgres

# 2. Create database if missing
createdb rag_db

# 3. Test connection
psql -U postgres -d rag_db -c "SELECT 1;"

# 4. Update .env with correct credentials
# Format: postgresql://username:password@host:port/dbname
```

### "Docling/PDF parsing error"
**Problem:** PDF upload fails

**Solution:**
```bash
# Reinstall docling with OCR support
pip install --upgrade docling pdf2image pytesseract

# Make sure you're using .pdf or .txt files
# Other formats not supported
```

### Performance is slow
**Problem:** Queries take >30 seconds

**Reasons & fixes:**
1. **Database indexes missing**
   ```bash
   # Check database indexes
   python src/core/check_db.py
   ```

2. **Large embeddings**
   - Reduce chunk size in `docling_parser.py`
   
3. **LLM is slow**
   - Use `gemini-1.5-flash` (faster, cheaper)
   - Not `gemini-2.0-pro` (slower)

---

## 📚 Learning Path for Trainees

### Week 1: Understanding the Basics
1. Read this README ✓
2. Run the quick start
3. Upload a test document
4. Ask simple questions
5. Check the generated sources

### Week 2: Explore the Code
1. Open `main.py` → understand FastAPI setup
2. Open `streamlit_app.py` → understand UI
3. Open `agent.py` → understand 4-node pipeline
4. Run in debug mode

### Week 3: Modify & Experiment
1. Change system prompts in `agent.py`
2. Try different search parameters
3. Experiment with chunk sizes
4. Add logging to debug

### Week 4: Deploy & Optimize
1. Set up PostgreSQL properly
2. Optimize database indexes
3. Try different embedding models
4. Deploy to production

---

## 📝 Example Questions to Try

### 1. Specific Information
**Q:** "What is section 4.2.1?"
- Best with: **FTS Search**
- Why: Looks for exact section numbers

### 2. Conceptual Questions
**Q:** "How does penalty structure work?"
- Best with: **Vector Search**
- Why: Needs semantic understanding

### 3. Complex Queries
**Q:** "What penalties apply to violations in section 2, and what's the appeals process?"
- Best with: **Hybrid Search**
- Why: Needs both keywords + understanding

### 4. Paraphrasing
**Q:** "Tell me about the fees"
**Document has:** "The cost shall be..."
- Best with: **Vector Search**
- Why: Different words, same meaning

---

## 🤝 Contributing

To add new features:

1. **Add a new search tool**
   - Create `src/api/v1/tools/new_search.py`
   - Register in `_TOOLS` dict in `agent.py`

2. **Modify LLM behavior**
   - Edit system prompts in `agent.py`
   - Adjust temperature/parameters in `_make_llm()`

3. **Optimize performance**
   - Check `db.py` for queries
   - Add database indexes
   - Profile slow functions

---

## 📞 Support

If stuck:
1. Check `.env` file is set up
2. Run `python src/core/check_db.py` to verify DB
3. Check terminal logs for errors
4. Try simpler questions first
5. Upload test documents first

---

## 📄 License

This project is part of the Agentic AI Course.

---

## 🎓 Key Takeaways

### For Trainees:
✅ **What this system teaches you:**
1. How RAG systems work end-to-end
2. Using AI agents (LangGraph) for orchestration
3. Multiple search strategies (FTS, Vector, Hybrid)
4. Reranking for quality improvement
5. Building production AI systems
6. REST APIs with FastAPI
7. Database integration with PostgreSQL

✅ **Real-world applications:**
- Customer support chatbots
- Medical document Q&A
- Legal research systems
- Internal knowledge bases
- compliance training systems

✅ **Skills you'll gain:**
- AI/LLM integration
- Database design
- API development
- System architecture
- Debugging AI systems

---

**Happy learning! 🚀**

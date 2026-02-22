# ClearPath RAG Chatbot

A **Retrieval-Augmented Generation (RAG)** customer support chatbot for ClearPath, a project management platform. Built with FastAPI, FAISS, sentence-transformers, and Groq LLM API.

## Architecture

```
User Query → Router (classify) → Retriever (FAISS search) → LLM (Groq) → Evaluator → Response
```

### Three-Layer Pipeline

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Layer 1: Model Router** | Deterministic Rule-Based Classifier | Routes queries using a custom 6-signal complexity scorer heuristics. Simple queries (score < 2) → 8B, Complex queries (score ≥ 2) → 70B. No LLMs used for decision-making. |
| **Layer 2: RAG Retriever** | `PyPDF2` + Recursive Chunking + FAISS | Custom-built extraction and chunking pipeline (no external RAG services). FAISS vector search retrieves relevant context. |
| **Layer 3: Output Evaluator** | Flagged Validations | Evaluates LLM output post-generation for `no_context`, `refusal` (non-answers), and `conflicting_info` (domain-specific check). Flags trigger a low-confidence UI warning. |

### Note on Chunking Strategy (Assignment Requirement)
Chunks are generated using a manual **Recursive Character Text Splitter**.
- **Chunk Size:** 500 characters
- **Overlap:** 100 characters
- **Strategy:** Sentences are kept whole. If a sentence exceeds the chunk boundary, it breaks cleanly on a space. This size was chosen because the provided PDFs often contain brief, bulleted steps (like setting up SSO) where 500 characters captures the full instructional thought without diluting the embedding vector with unrelated surrounding text, while the 100-character overlap prevents cutting a critical step or code snippet in half.

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Uvicorn |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Vector Store | FAISS (IndexFlatIP, cosine similarity) |
| LLM | Groq API (Llama 3.1 8B + Llama 3.3 70B) |
| Frontend | Vanilla HTML/CSS/JS |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Groq API key ([get one here](https://console.groq.com/keys))

### 1. Clone & Install

```bash
git clone <repo-url>
cd AI_System_Assignment

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Create .env file
echo GROQ_API_KEY=your_api_key_here > .env
echo PORT=8000 >> .env
```

### 3. Build the Index (first time only)

```bash
python -c "
from backend.rag.pdf_parser import extract_all_pdfs
from backend.rag.chunker import chunk_pages
from backend.rag.embeddings import EmbeddingIndex
import json, os

pages = extract_all_pdfs('docs')
chunks = chunk_pages(pages)
os.makedirs('data', exist_ok=True)
with open('data/chunks.json', 'w') as f:
    json.dump(chunks, f, indent=2)

idx = EmbeddingIndex()
idx.build_index(chunks)
idx.save('data/faiss_index')
print(f'Index built: {len(chunks)} chunks')
"
```

### 4. Run the Server

```bash
python -m backend.main
```

Open **http://localhost:8000** in your browser.

---

## API Endpoint

### `POST /query`

**Request:**
```json
{
    "question": "What is the Pro plan price?",
    "conversation_id": "optional-id"
}
```

**Response:**
```json
{
    "answer": "The Pro plan costs $49/month...",
    "metadata": {
        "model_used": "llama-3.1-8b-instant",
        "classification": "simple",
        "tokens": { "input": 716, "output": 63 },
        "latency_ms": 340,
        "chunks_retrieved": 5,
        "evaluator_flags": []
    },
    "sources": [
        { "document": "14_Pricing_Sheet_2024.pdf", "page": 1, "relevance_score": 0.72 }
    ],
    "conversation_id": "conv_abc123"
}
```

### `GET /health`
Returns `{ "status": "ok" }`.

---

## Project Structure

```
AI_System_Assignment/
├── backend/
│   ├── main.py                 # FastAPI app, /query endpoint
│   ├── config.py               # Centralized configuration
│   ├── rag/
│   │   ├── pdf_parser.py       # PDF text extraction (PyPDF2)
│   │   ├── chunker.py          # Recursive text chunking (500 chars, 100 overlap)
│   │   ├── embeddings.py       # Embedding generation + FAISS index
│   │   └── retriever.py        # Similarity search + context builder
│   ├── router/
│   │   └── classifier.py       # Deterministic rule-based query classifier (6 signals)
│   ├── llm/
│   │   └── groq_client.py      # Groq API wrapper with token tracking
│   ├── evaluator/
│   │   └── evaluator.py        # Output evaluation (3 flags including custom check)
│   └── models/
│       └── schemas.py          # Pydantic request/response models
├── frontend/
│   ├── index.html              # Chat interface
│   ├── style.css               # Black & white theme
│   └── script.js               # Chat logic + debug panel
├── docs/                       # 30 source PDFs
├── data/                       # Generated chunks + FAISS index
├── requirements.txt
├── written_answers.md
└── README.md
```

---

## Model Routing Strategy

The router relies entirely on a deterministic, rule-based classifier. Calling an LLM simply to classify a query is too expensive and slow for the first hop of a support bot. The router instead scores the input on 6 signals (greetings, query length, complex keywords, multi-part questions, complaints, and subordinate clauses). See `written_answers.md` Q1 for the exact scoring breakdown.

| Classification | Model | Trigger |
|---------------|-------|---------|
| **Simple** (Score < 2) | `llama-3.1-8b-instant` | Greetings, short factual queries, single-keyword lookups |
| **Complex** (Score ≥ 2)| `llama-3.3-70b-versatile` | Multi-part questions, comparisons, troubleshooting, long queries |

---

## Evaluator Flags

| Flag | Triggers When |
|------|--------------|
| `no_context` | LLM answered but 0 relevant chunks were retrieved |
| `refusal` | LLM response contains hedging phrases ("I don't have", "not enough information") |
| `conflicting_info` | Response references contradicting sources or uses conflict language |

When any flag is raised, the response is prefixed with: *"⚠️ Low confidence — please verify with support."*

---

## Testing

```bash
# Test individual layers
python test_retriever.py    # Retriever + context + LLM
python test_router.py       # Query classifier (10/10)
python test_evaluator.py    # Evaluator flags (5/5)
python test_api.py          # API endpoint (5/5)

# Full E2E suite (11 queries, 5 categories)
python test_e2e.py
```

---

## Known Issues

1. **Greeting false positives**: Short messages starting with "Hi/Hello" AND containing a question (≤5 words total) may be routed as greetings. Messages >5 words go through the full RAG pipeline.
2. **Poisoned document**: `22_Q4_2023_Team_Retrospective.pdf` contains prompt injection text. The system prompt provides partial defense, but sophisticated injection may bypass it.
3. **Cross-document queries**: Questions spanning multiple topics (e.g., "keyboard shortcuts for mobile app") may retrieve chunks biased toward one topic.

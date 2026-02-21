import os
from dotenv import load_dotenv

load_dotenv()

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Server
PORT = int(os.getenv("PORT", 8000))

# LLM Models
MODEL_SIMPLE = "llama-3.1-8b-instant"
MODEL_COMPLEX = "llama-3.3-70b-versatile"

# RAG Configuration
CHUNK_SIZE = 500          # Target chunk size in characters
CHUNK_OVERLAP = 100       # Overlap between chunks in characters
TOP_K = 5                 # Number of chunks to retrieve
SIMILARITY_THRESHOLD = 0.3  # Minimum similarity score to consider relevant

# Paths
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CHUNKS_FILE = os.path.join(DATA_DIR, "chunks.json")
FAISS_INDEX_PATH = os.path.join(DATA_DIR, "faiss_index")

# Embedding Model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

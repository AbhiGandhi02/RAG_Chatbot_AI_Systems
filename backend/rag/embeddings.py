"""
Embeddings — Generates vector embeddings and manages the FAISS index.

Uses sentence-transformers/all-MiniLM-L6-v2 for local embedding generation
and FAISS for efficient similarity search.
"""

import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple


class EmbeddingIndex:
    """Manages document embeddings and FAISS index for similarity search."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the embedding model."""
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.chunks = []
        print("Embedding model loaded.")
    
    def build_index(self, chunks: List[Dict]):
        """
        Build a FAISS index from document chunks.
        
        Args:
            chunks: List of chunk dicts with 'text' field
        """
        self.chunks = chunks
        texts = [chunk["text"] for chunk in chunks]
        
        print(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
        embeddings = np.array(embeddings, dtype=np.float32)
        
        # Build FAISS index using inner product (cosine similarity since vectors are normalized)
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)
        
        print(f"FAISS index built with {self.index.ntotal} vectors (dim={dim})")
    
    def save(self, index_dir: str):
        """Save FAISS index and chunk metadata to disk."""
        os.makedirs(index_dir, exist_ok=True)
        
        # Save FAISS index
        index_path = os.path.join(index_dir, "index.faiss")
        faiss.write_index(self.index, index_path)
        
        # Save chunk metadata
        meta_path = os.path.join(index_dir, "chunks_meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, indent=2, ensure_ascii=False)
        
        print(f"Index saved to {index_dir}")
    
    def load(self, index_dir: str):
        """Load FAISS index and chunk metadata from disk."""
        index_path = os.path.join(index_dir, "index.faiss")
        meta_path = os.path.join(index_dir, "chunks_meta.json")
        
        self.index = faiss.read_index(index_path)
        
        with open(meta_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)
        
        print(f"Index loaded: {self.index.ntotal} vectors, {len(self.chunks)} chunks")
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """
        Search for the most similar chunks to a query.
        
        Args:
            query: The search query
            top_k: Number of top results to return
        
        Returns:
            List of (chunk_dict, similarity_score) tuples, sorted by relevance
        """
        if self.index is None:
            raise ValueError("Index not built or loaded. Call build_index() or load() first.")
        
        # Embed the query
        query_embedding = self.model.encode([query], normalize_embeddings=True)
        query_embedding = np.array(query_embedding, dtype=np.float32)
        
        # Search FAISS
        scores, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.chunks) and idx >= 0:
                results.append((self.chunks[idx], float(score)))
        
        return results


# Singleton instance for reuse
_embedding_index = None


def get_embedding_index() -> EmbeddingIndex:
    """Get or create the singleton embedding index."""
    global _embedding_index
    if _embedding_index is None:
        from backend.config import EMBEDDING_MODEL
        _embedding_index = EmbeddingIndex(EMBEDDING_MODEL)
    return _embedding_index


if __name__ == "__main__":
    from backend.config import DOCS_DIR, CHUNKS_FILE, FAISS_INDEX_PATH, CHUNK_SIZE, CHUNK_OVERLAP
    from backend.rag.pdf_parser import extract_all_pdfs
    from backend.rag.chunker import chunk_pages, save_chunks
    
    # Step 1: Parse PDFs
    pages = extract_all_pdfs(DOCS_DIR)
    
    # Step 2: Chunk pages
    chunks = chunk_pages(pages, CHUNK_SIZE, CHUNK_OVERLAP)
    save_chunks(chunks, CHUNKS_FILE)
    
    # Step 3: Build embeddings and FAISS index
    idx = EmbeddingIndex()
    idx.build_index(chunks)
    idx.save(FAISS_INDEX_PATH)
    
    # Step 4: Test search
    print("\n--- Test Search ---")
    results = idx.search("What is the pricing for Pro plan?", top_k=3)
    for chunk, score in results:
        print(f"  Score: {score:.4f} | {chunk['document']} (p{chunk['page']}): {chunk['text'][:100]}...")

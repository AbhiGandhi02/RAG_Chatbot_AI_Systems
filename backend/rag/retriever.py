"""
Retriever — Handles query-to-relevant-chunks retrieval.

Given a query string, embeds it, searches the FAISS index, 
and returns the top-k most relevant chunks above a similarity threshold.
"""

from typing import List, Dict, Tuple
from backend.rag.embeddings import EmbeddingIndex, get_embedding_index
from backend.config import TOP_K, SIMILARITY_THRESHOLD, FAISS_INDEX_PATH


class Retriever:
    """Retrieves relevant document chunks for a given query."""
    
    def __init__(self, embedding_index: EmbeddingIndex = None):
        """
        Initialize retriever with an embedding index.
        
        If no index is provided, uses the singleton and loads from disk.
        """
        if embedding_index:
            self.index = embedding_index
        else:
            self.index = get_embedding_index()
            self.index.load(FAISS_INDEX_PATH)
    
    def retrieve(self, query: str, top_k: int = None, threshold: float = None) -> List[Dict]:
        """
        Retrieve the most relevant chunks for a query.
        
        Args:
            query: The user's question
            top_k: Number of chunks to retrieve (default from config)
            threshold: Minimum similarity score (default from config)
        
        Returns:
            List of chunk dicts with added 'relevance_score' field,
            sorted by relevance (highest first).
            Only includes chunks above the similarity threshold.
        """
        top_k = top_k or TOP_K
        threshold = threshold or SIMILARITY_THRESHOLD
        
        # Search the index
        results = self.index.search(query, top_k=top_k)
        
        # Filter by threshold and add relevance score
        relevant_chunks = []
        for chunk, score in results:
            if score >= threshold:
                chunk_with_score = {
                    **chunk,
                    "relevance_score": round(score, 4)
                }
                relevant_chunks.append(chunk_with_score)
        
        return relevant_chunks
    
    def build_context(self, chunks: List[Dict]) -> str:
        """
        Build context string from retrieved chunks for the LLM prompt.
        
        Args:
            chunks: List of retrieved chunk dicts
        
        Returns:
            Formatted context string with source attribution
        """
        if not chunks:
            return "No relevant documentation found for this query."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source = f"[Source: {chunk['document']}, Page {chunk['page']}]"
            context_parts.append(f"--- Context {i} {source} ---\n{chunk['text']}")
        
        return "\n\n".join(context_parts)

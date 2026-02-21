import logging
from typing import List, Dict
from sqlalchemy.future import select
from sqlalchemy import text
from sentence_transformers import SentenceTransformer

from backend.db.database import AsyncSessionLocal
from backend.db.models import DocumentChunk
from backend.config import TOP_K, SIMILARITY_THRESHOLD, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

class Retriever:
    """Retrieves relevant document chunks from PostgreSQL using pgvector."""
    
    def __init__(self, model_name: str = None):
        """Initialize retriever with the sentence-transformer model."""
        model_name = model_name or EMBEDDING_MODEL
        logger.info(f"Retriever loading model: {model_name}...")
        self.model = SentenceTransformer(model_name)
    
    def embed_query(self, query: str) -> List[float]:
        """Embed a query string into a vector."""
        embedding = self.model.encode([query], normalize_embeddings=True)
        return embedding[0].tolist()
        
    async def retrieve_async(self, query: str, top_k: int = None, threshold: float = None) -> List[Dict]:
        """
        Asynchronously retrieve the most relevant chunks.
        
        Uses inner product (<#>) which is equivalent to cosine similarity for normalized vectors.
        Because distance = 1 - similarity, inner product distance works where lower is more similar.
        For pgvector inner product (<#>), lower distance means higher similarity.
        We want to return chunks where similarity >= threshold.
        """
        top_k = top_k or TOP_K
        threshold = threshold or SIMILARITY_THRESHOLD
        
        query_embedding = self.embed_query(query)
        
        relevant_chunks = []
        async with AsyncSessionLocal() as db:
            # For cosine similarity in pgvector, `<=>` returns the cosine distance (1 - cosine_similarity).
            # So if we want similarity >= 0.3, it means distance <= 0.7
            
            # Using SQLAlchemy pgvector integration:
            result = await db.execute(
                select(DocumentChunk, DocumentChunk.embedding.cosine_distance(query_embedding).label("cos_dist"))
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            )
            
            rows = result.all()
            for chunk_obj, dist in rows:
                # Recover original cosine similarity from the pgvector distance
                # Cosine Similarity = 1.0 - cosine_distance
                # E.g., if dist is 0.15, similarity is 0.85
                similarity = 1.0 - float(dist)
                
                if similarity >= threshold:
                    chunk_dict = {
                        "document": chunk_obj.document_name,
                        "page": chunk_obj.page,
                        "text": chunk_obj.text_content,
                        "relevance_score": round(similarity, 4)
                    }
                    relevant_chunks.append(chunk_dict)
                    
        return relevant_chunks
        
    def retrieve(self, query: str, top_k: int = None, threshold: float = None) -> List[Dict]:
        """Synchronous wrapper for retrieve_async."""
        import asyncio
        
        # Check if an event loop is already running
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        if loop and loop.is_running():
            # If we're already in an async context, we can't run asyncio.run()
            # This is a temporary bridging if main.py caller is not awaited
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self.retrieve_async(query, top_k, threshold))
        else:
            return asyncio.run(self.retrieve_async(query, top_k, threshold))
            
    def build_context(self, chunks: List[Dict]) -> str:
        """Build context string from retrieved chunks for the LLM prompt."""
        if not chunks:
            return "No relevant documentation found for this query."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source = f"[Source: {chunk['document']}, Page {chunk['page']}]"
            context_parts.append(f"--- Context {i} {source} ---\n{chunk['text']}")
        
        return "\n\n".join(context_parts)

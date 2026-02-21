"""
Pydantic schemas — Request and response models matching the API contract.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class QueryRequest(BaseModel):
    """Request body for POST /query."""
    question: str
    conversation_id: Optional[str] = None


class ConversationUpdate(BaseModel):
    """Request body to rename a conversation."""
    title: str

class TokenUsage(BaseModel):
    """Token usage breakdown."""
    input: int
    output: int


class Metadata(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    """Metadata about query processing."""
    model_used: str
    classification: str
    tokens: TokenUsage
    latency_ms: int
    chunks_retrieved: int
    evaluator_flags: List[str]


class Source(BaseModel):
    """Source document reference."""
    document: str
    page: int
    relevance_score: Optional[float] = None


class QueryResponse(BaseModel):
    """Response body for POST /query."""
    answer: str
    metadata: Metadata
    sources: List[Source]
    conversation_id: str

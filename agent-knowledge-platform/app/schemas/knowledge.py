"""Knowledge base request/response schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    """Create knowledge base request."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    embedding_model: str = "text-embedding-v3"


class KnowledgeBaseUpdate(BaseModel):
    """Update knowledge base request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class KnowledgeBaseResponse(BaseModel):
    """Knowledge base response."""
    id: UUID
    name: str
    description: Optional[str]
    embedding_model: str
    document_count: int
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """Document response."""
    id: UUID
    filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    """Knowledge base search request."""
    query: str = Field(..., min_length=1)
    knowledge_base_id: UUID
    top_k: int = Field(5, ge=1, le=20)


class SearchResultItem(BaseModel):
    """Single search result."""
    content: str
    source: str
    score: float
    metadata: dict = {}


class SearchResponse(BaseModel):
    """Knowledge base search response."""
    results: List[SearchResultItem]
    query: str
    knowledge_base_id: UUID

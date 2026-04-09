from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.knowledge import DocumentStatus

class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    embedding_provider: str = "local_hf"
    embedding_model: str = "/models/snowflake-arctic-embed-l-v2.0-ko"
    embedding_dim: int = 1024
    chunk_size: int = 1000
    chunk_overlap: int = 200

class KnowledgeBaseRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    embedding_provider: str
    embedding_model: str
    embedding_dim: int
    qdrant_collection: str
    chunk_size: int
    chunk_overlap: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class DocumentRead(BaseModel):
    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    filename: str
    file_size: int
    file_type: str
    status: DocumentStatus
    error: str | None
    chunk_count: int
    created_at: datetime
    model_config = {"from_attributes": True}

class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = 5
    score_threshold: float | None = None

class SearchHit(BaseModel):
    score: float
    text: str
    filename: str
    chunk_index: int

class SearchResponse(BaseModel):
    hits: list[SearchHit]

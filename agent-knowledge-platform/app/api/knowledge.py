"""Knowledge base API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    DocumentResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter()


# --- Knowledge Base CRUD ---

@router.post("/bases", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    request: KnowledgeBaseCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new knowledge base."""
    service = KnowledgeService(db)
    kb = await service.create_knowledge_base(
        user_id=user_id,
        name=request.name,
        description=request.description,
        embedding_model=request.embedding_model,
    )
    return kb


@router.get("/bases", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all knowledge bases for the current user."""
    service = KnowledgeService(db)
    bases = await service.list_knowledge_bases(user_id)
    return bases


@router.get("/bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific knowledge base."""
    service = KnowledgeService(db)
    kb = await service.get_knowledge_base(kb_id, user_id)
    return kb


@router.delete("/bases/{kb_id}", status_code=204)
async def delete_knowledge_base(
    kb_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a knowledge base and all its documents."""
    service = KnowledgeService(db)
    await service.delete_knowledge_base(kb_id, user_id)


# --- Document Management ---

@router.post("/bases/{kb_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    kb_id: UUID,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document to a knowledge base."""
    service = KnowledgeService(db)
    doc = await service.upload_document(
        kb_id=kb_id,
        user_id=user_id,
        file=file,
    )
    return doc


@router.get("/bases/{kb_id}/documents", response_model=List[DocumentResponse])
async def list_documents(
    kb_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all documents in a knowledge base."""
    service = KnowledgeService(db)
    docs = await service.list_documents(kb_id, user_id)
    return docs


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document from a knowledge base."""
    service = KnowledgeService(db)
    await service.delete_document(doc_id, user_id)


# --- Search ---

@router.post("/search", response_model=SearchResponse)
async def search_knowledge_base(
    request: SearchRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Search a knowledge base with a text query."""
    service = KnowledgeService(db)
    results = await service.search(
        user_id=user_id,
        knowledge_base_id=request.knowledge_base_id,
        query=request.query,
        top_k=request.top_k,
    )
    return results

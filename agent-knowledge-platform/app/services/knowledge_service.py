"""Knowledge base service: document management, vectorization, search."""

import os
import uuid
from pathlib import Path
from typing import List

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    NotFoundError,
    FileSizeError,
    UnsupportedFileType,
    KnowledgeBaseError,
)
from app.models.knowledge import KnowledgeBase, Document
from app.schemas.knowledge import (
    KnowledgeBaseResponse,
    DocumentResponse,
    SearchResponse,
    SearchResultItem,
)

# Supported file types
SUPPORTED_TYPES = {".pdf", ".txt", ".md", ".docx"}


def _generate_collection_name(user_id: uuid.UUID, name: str) -> str:
    """Generate a unique Qdrant collection name."""
    slug = name.lower().replace(" ", "_")[:30]
    return f"kb_{str(user_id)[:8]}_{slug}"


class KnowledgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_knowledge_base(
        self,
        user_id: uuid.UUID,
        name: str,
        description: str = None,
        embedding_model: str = "text-embedding-v3",
    ) -> KnowledgeBase:
        """Create a new knowledge base."""
        collection_name = _generate_collection_name(user_id, name)

        kb = KnowledgeBase(
            user_id=user_id,
            name=name,
            description=description,
            embedding_model=embedding_model,
            qdrant_collection=collection_name,
        )
        self.db.add(kb)
        await self.db.flush()
        await self.db.refresh(kb)

        # Create Qdrant collection
        try:
            from app.knowledge.vector_store import VectorStoreManager
            from app.config import settings as cfg
            vs = VectorStoreManager(cfg.QDRANT_HOST, cfg.QDRANT_PORT)
            vs.create_collection(collection_name, vector_size=cfg.EMBEDDING_DIMENSION)
        except Exception as e:
            raise KnowledgeBaseError(f"Failed to create vector collection: {e}")

        return kb

    async def list_knowledge_bases(self, user_id: uuid.UUID) -> List[KnowledgeBase]:
        """List all knowledge bases for a user."""
        result = await self.db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.user_id == user_id)
            .order_by(KnowledgeBase.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_knowledge_base(self, kb_id: uuid.UUID, user_id: uuid.UUID) -> KnowledgeBase:
        """Get a knowledge base by ID, verifying ownership."""
        result = await self.db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.user_id == user_id,
            )
        )
        kb = result.scalar_one_or_none()
        if not kb:
            raise NotFoundError("KnowledgeBase", str(kb_id))
        return kb

    async def delete_knowledge_base(self, kb_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete a knowledge base and all its vectors."""
        kb = await self.get_knowledge_base(kb_id, user_id)

        # Delete Qdrant collection
        try:
            from app.knowledge.vector_store import VectorStoreManager
            from app.config import settings as cfg
            vs = VectorStoreManager(cfg.QDRANT_HOST, cfg.QDRANT_PORT)
            vs.client.delete_collection(kb.qdrant_collection)
        except Exception:
            pass  # Collection might not exist

        await self.db.delete(kb)

    async def upload_document(
        self,
        kb_id: uuid.UUID,
        user_id: uuid.UUID,
        file: UploadFile,
    ) -> Document:
        """Upload and process a document."""
        # Verify knowledge base ownership
        kb = await self.get_knowledge_base(kb_id, user_id)

        # Validate file type
        suffix = Path(file.filename).suffix.lower()
        if suffix not in SUPPORTED_TYPES:
            raise UnsupportedFileType(suffix)

        # Validate file size
        content = await file.read()
        file_size = len(content)
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise FileSizeError(settings.MAX_FILE_SIZE_MB)

        # Save file to disk
        user_dir = Path(settings.UPLOAD_DIR) / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        file_path = user_dir / f"{uuid.uuid4()}{suffix}"

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Create document record
        doc = Document(
            knowledge_base_id=kb_id,
            filename=file.filename,
            file_type=suffix,
            file_size=file_size,
            file_path=str(file_path),
            status="pending",
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)

        # Process document asynchronously (in background)
        # For MVP, process synchronously
        try:
            await self._process_document(doc, kb)
            doc.status = "completed"
        except Exception as e:
            doc.status = "failed"
            doc.error_message = str(e)[:500]

        # Update knowledge base counts
        result = await self.db.execute(
            select(Document).where(Document.knowledge_base_id == kb_id)
        )
        docs = list(result.scalars().all())
        kb.document_count = len(docs)
        kb.chunk_count = sum(d.chunk_count for d in docs)

        return doc

    async def _process_document(self, doc: Document, kb: KnowledgeBase) -> None:
        """Process a document: load, split, embed, store in Qdrant."""
        from app.knowledge.document_loader import DocumentLoader
        from app.knowledge.text_splitter import SmartTextSplitter
        from app.knowledge.embeddings import get_embeddings
        from app.knowledge.vector_store import VectorStoreManager
        from app.config import settings as cfg

        # 1. Load document
        documents = DocumentLoader.load(doc.file_path)

        # 2. Split into chunks
        strategy = "code" if doc.file_type in (".py", ".js", ".ts", ".java") else "recursive"
        chunks = SmartTextSplitter.split(documents, strategy=strategy)
        doc.chunk_count = len(chunks)

        # 3. Generate embeddings
        texts = [chunk.page_content for chunk in chunks]
        embeddings = await get_embeddings(texts)

        # 4. Store in Qdrant
        metadata = [
            {
                "user_id": str(kb.user_id),
                "knowledge_base_id": str(kb.id),
                "document_id": str(doc.id),
                "chunk_index": i,
                "content": chunk.page_content,
                "source": doc.filename,
                "page": chunk.metadata.get("page", 0),
            }
            for i, chunk in enumerate(chunks)
        ]

        vs = VectorStoreManager(cfg.QDRANT_HOST, cfg.QDRANT_PORT)
        await vs.upsert(kb.qdrant_collection, chunks, embeddings, metadata)

    async def list_documents(self, kb_id: uuid.UUID, user_id: uuid.UUID) -> List[Document]:
        """List all documents in a knowledge base."""
        # Verify ownership
        await self.get_knowledge_base(kb_id, user_id)

        result = await self.db.execute(
            select(Document)
            .where(Document.knowledge_base_id == kb_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_document(self, doc_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete a document and its vectors."""
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError("Document", str(doc_id))

        # Verify ownership through knowledge base
        await self.get_knowledge_base(doc.knowledge_base_id, user_id)

        # Delete vectors from Qdrant
        try:
            from app.knowledge.vector_store import VectorStoreManager
            from app.config import settings as cfg
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            vs = VectorStoreManager(cfg.QDRANT_HOST, cfg.QDRANT_PORT)
            kb_result = await self.db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == doc.knowledge_base_id)
            )
            kb = kb_result.scalar_one()
            vs.client.delete(
                collection_name=kb.qdrant_collection,
                points_selector=Filter(must=[
                    FieldCondition(key="document_id", match=MatchValue(value=str(doc_id)))
                ]),
            )
        except Exception:
            pass

        # Delete file from disk
        try:
            os.remove(doc.file_path)
        except OSError:
            pass

        await self.db.delete(doc)

    async def search(
        self,
        user_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        query: str,
        top_k: int = 5,
    ) -> SearchResponse:
        """Search a knowledge base."""
        kb = await self.get_knowledge_base(knowledge_base_id, user_id)

        from app.knowledge.embeddings import get_embeddings
        from app.knowledge.vector_store import VectorStoreManager
        from app.config import settings as cfg

        # Generate query embedding
        query_embedding = (await get_embeddings([query]))[0]

        # Search Qdrant
        vs = VectorStoreManager(cfg.QDRANT_HOST, cfg.QDRANT_PORT)
        results = await vs.search(
            collection=kb.qdrant_collection,
            query_vector=query_embedding,
            top_k=top_k,
            user_id=str(user_id),
        )

        items = [
            SearchResultItem(
                content=hit.payload.get("content", ""),
                source=hit.payload.get("source", ""),
                score=hit.score,
                metadata=hit.payload,
            )
            for hit in results
        ]

        return SearchResponse(
            results=items,
            query=query,
            knowledge_base_id=knowledge_base_id,
        )

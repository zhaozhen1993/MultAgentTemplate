"""RAG retriever: combines embedding search with context formatting."""

import logging
from typing import List, Optional

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class RAGRetriever:
    """Retrieval-Augmented Generation retriever.

    Combines vector search with context formatting for LLM consumption.
    """

    def __init__(
        self,
        collection: str,
        user_id: str = None,
        top_k: int = 5,
        score_threshold: float = 0.3,
    ):
        self.collection = collection
        self.user_id = user_id
        self.top_k = top_k
        self.score_threshold = score_threshold

    async def retrieve(self, query: str) -> List[Document]:
        """Retrieve relevant documents for a query.

        Args:
            query: The search query text

        Returns:
            List of LangChain Document objects with relevant content
        """
        from app.knowledge.embeddings import get_embeddings
        from app.knowledge.vector_store import VectorStoreManager
        from app.config import settings

        # Generate query embedding
        query_embeddings = await get_embeddings([query])
        query_vector = query_embeddings[0]

        # Search Qdrant
        vs = VectorStoreManager(settings.QDRANT_HOST, settings.QDRANT_PORT)
        results = await vs.search(
            collection=self.collection,
            query_vector=query_vector,
            top_k=self.top_k,
            user_id=self.user_id,
        )

        # Convert to LangChain Documents
        documents = []
        for hit in results:
            if hit.score >= self.score_threshold:
                doc = Document(
                    page_content=hit.payload.get("content", ""),
                    metadata={
                        "source": hit.payload.get("source", "unknown"),
                        "score": hit.score,
                        "chunk_index": hit.payload.get("chunk_index", 0),
                        "page": hit.payload.get("page", 0),
                    },
                )
                documents.append(doc)

        logger.info(
            f"Retrieved {len(documents)} documents for query "
            f"(threshold={self.score_threshold})"
        )

        return documents

    async def retrieve_and_format(self, query: str) -> str:
        """Retrieve documents and format them as context for the LLM.

        Args:
            query: The search query text

        Returns:
            Formatted context string ready for LLM consumption
        """
        docs = await self.retrieve(query)

        if not docs:
            return "未在知识库中找到相关信息。"

        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "unknown")
            score = doc.metadata.get("score", 0)
            context_parts.append(
                f"[参考 {i}] (来源: {source}, 相关度: {score:.2f})\n{doc.page_content}"
            )

        return "\n\n".join(context_parts)


class HybridRetriever:
    """Hybrid retriever combining vector search with keyword search.

    Uses Reciprocal Rank Fusion (RRF) to combine results.
    """

    def __init__(
        self,
        collection: str,
        user_id: str = None,
        top_k: int = 5,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ):
        self.collection = collection
        self.user_id = user_id
        self.top_k = top_k
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    async def retrieve(self, query: str) -> List[Document]:
        """Retrieve using hybrid search (vector + keyword).

        For MVP, this delegates to pure vector search.
        BM25 keyword search can be added later.
        """
        # For now, delegate to vector-only retriever
        retriever = RAGRetriever(
            collection=self.collection,
            user_id=self.user_id,
            top_k=self.top_k,
        )
        return await retriever.retrieve(query)

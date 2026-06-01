"""Qdrant vector store management."""

import logging
import uuid
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages Qdrant vector storage operations."""

    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        logger.info(f"Connected to Qdrant at {host}:{port}")

    def create_collection(self, name: str, vector_size: int = 1536) -> None:
        """Create a new Qdrant collection.

        Args:
            name: Collection name
            vector_size: Dimension of embedding vectors
        """
        try:
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection: {name} (dim={vector_size})")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"Collection {name} already exists, skipping creation")
            else:
                raise

    async def upsert(
        self,
        collection: str,
        chunks: list,
        embeddings: List[List[float]],
        metadata: List[dict],
    ) -> None:
        """Insert or update vectors in the collection.

        Args:
            collection: Collection name
            chunks: Original document chunks (for reference)
            embeddings: Embedding vectors
            metadata: Metadata dicts for each chunk
        """
        points = []
        for i, (emb, meta) in enumerate(zip(embeddings, metadata)):
            point_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=point_id,
                    vector=emb,
                    payload=meta,
                )
            )

        # Upsert in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(
                collection_name=collection,
                points=batch,
            )

        logger.info(f"Upserted {len(points)} vectors to collection '{collection}'")

    async def search(
        self,
        collection: str,
        query_vector: List[float],
        top_k: int = 5,
        user_id: str = None,
    ) -> list:
        """Search for similar vectors.

        Args:
            collection: Collection name
            query_vector: Query embedding vector
            top_k: Number of results to return
            user_id: Optional user ID filter for tenant isolation

        Returns:
            List of search results with scores and payloads
        """
        query_filter = None
        if user_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id),
                    )
                ]
            )

        results = self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )

        logger.info(
            f"Searched collection '{collection}': "
            f"found {len(results)} results (top_k={top_k})"
        )

        return results

    def delete_collection(self, name: str) -> None:
        """Delete a Qdrant collection."""
        try:
            self.client.delete_collection(name)
            logger.info(f"Deleted Qdrant collection: {name}")
        except Exception as e:
            logger.warning(f"Failed to delete collection {name}: {e}")

    def delete_points(
        self, collection: str, field: str, value: str
    ) -> None:
        """Delete points matching a filter condition."""
        self.client.delete(
            collection_name=collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key=field,
                        match=MatchValue(value=value),
                    )
                ]
            ),
        )
        logger.info(f"Deleted points from '{collection}' where {field}={value}")

    def collection_exists(self, name: str) -> bool:
        """Check if a collection exists."""
        try:
            collections = self.client.get_collections().collections
            return any(c.name == name for c in collections)
        except Exception:
            return False

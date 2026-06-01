"""Embedding model integration for text vectorization."""

import logging
from typing import List

logger = logging.getLogger(__name__)


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts.

    Uses the configured embedding provider (DashScope/OpenAI compatible).

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors
    """
    from app.config import settings

    provider = settings.EMBEDDING_PROVIDER
    model = settings.EMBEDDING_MODEL
    api_key = settings.EMBEDDING_API_KEY

    if provider == "dashscope":
        return await _dashscope_embed(texts, model, api_key)
    elif provider == "openai":
        return await _openai_embed(texts, model, api_key)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")


async def _dashscope_embed(
    texts: List[str], model: str, api_key: str
) -> List[List[float]]:
    """Generate embeddings using DashScope (Alibaba Cloud)."""
    try:
        import dashscope
        from dashscope import TextEmbedding

        dashscope.api_key = api_key

        # DashScope has a batch limit, process in chunks
        all_embeddings = []
        batch_size = 25  # DashScope limit per request

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = TextEmbedding.call(model=model, input=batch)

            if response.status_code == 200:
                for item in response.output["embeddings"]:
                    all_embeddings.append(item["embedding"])
            else:
                raise RuntimeError(
                    f"DashScope embedding failed: {response.code} - {response.message}"
                )

        logger.info(f"Generated {len(all_embeddings)} embeddings using DashScope ({model})")
        return all_embeddings

    except ImportError:
        raise ImportError(
            "dashscope is required. Install with: pip install dashscope"
        )


async def _openai_embed(
    texts: List[str], model: str, api_key: str
) -> List[List[float]]:
    """Generate embeddings using OpenAI-compatible API."""
    try:
        from openai import AsyncOpenAI
        from app.config import settings

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.LLM_BASE_URL,  # Reuse LLM base URL
        )

        all_embeddings = []
        batch_size = 100  # OpenAI limit per request

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await client.embeddings.create(model=model, input=batch)

            for item in response.data:
                all_embeddings.append(item.embedding)

        logger.info(f"Generated {len(all_embeddings)} embeddings using OpenAI ({model})")
        return all_embeddings

    except ImportError:
        raise ImportError("openai is required. Install with: pip install openai")


def get_embedding_dimension(provider: str = None) -> int:
    """Get the embedding dimension for the configured provider."""
    from app.config import settings

    provider = provider or settings.EMBEDDING_PROVIDER
    model = settings.EMBEDDING_MODEL

    # Known dimensions
    dimensions = {
        "text-embedding-v3": 1536,  # DashScope
        "text-embedding-v2": 1024,  # DashScope
        "text-embedding-3-large": 3072,  # OpenAI
        "text-embedding-3-small": 1536,  # OpenAI
        "text-embedding-ada-002": 1536,  # OpenAI
    }

    return dimensions.get(model, 1536)  # Default to 1536

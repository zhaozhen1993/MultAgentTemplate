"""Text splitting strategies for document chunking."""

import logging
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class SmartTextSplitter:
    """Smart text splitter with multiple strategies for different content types."""

    # Default separators optimized for Chinese + English mixed content
    DEFAULT_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " "]

    # Code-optimized separators
    CODE_SEPARATORS = [
        "\n\nclass ", "\ndef ", "\nasync def ", "\n\n# ",
        "\n\n", "\n", " ", "",
    ]

    STRATEGIES = {
        "recursive": {
            "chunk_size": 500,
            "chunk_overlap": 50,
            "separators": DEFAULT_SEPARATORS,
        },
        "code": {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "separators": CODE_SEPARATORS,
        },
        "large": {
            "chunk_size": 1500,
            "chunk_overlap": 150,
            "separators": DEFAULT_SEPARATORS,
        },
        "small": {
            "chunk_size": 200,
            "chunk_overlap": 30,
            "separators": DEFAULT_SEPARATORS,
        },
    }

    @classmethod
    def split(
        cls,
        documents: List[Document],
        strategy: str = "recursive",
        chunk_size: int = None,
        chunk_overlap: int = None,
    ) -> List[Document]:
        """Split documents into chunks.

        Args:
            documents: List of LangChain Document objects
            strategy: Splitting strategy ('recursive', 'code', 'large', 'small')
            chunk_size: Override default chunk size
            chunk_overlap: Override default chunk overlap

        Returns:
            List of chunked Document objects
        """
        config = cls.STRATEGIES.get(strategy, cls.STRATEGIES["recursive"])

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or config["chunk_size"],
            chunk_overlap=chunk_overlap or config["chunk_overlap"],
            separators=config["separators"],
            length_function=len,
        )

        chunks = splitter.split_documents(documents)
        logger.info(
            f"Split {len(documents)} documents into {len(chunks)} chunks "
            f"(strategy={strategy}, chunk_size={chunk_size or config['chunk_size']})"
        )

        # Add chunk index to metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i

        return chunks

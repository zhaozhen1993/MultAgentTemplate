"""Document loaders for various file formats."""

import logging
from pathlib import Path
from typing import List

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Unified document loader supporting multiple file formats."""

    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}

    @classmethod
    def load(cls, file_path: str) -> List[Document]:
        """Load a document from file path.

        Args:
            file_path: Absolute path to the document file

        Returns:
            List of LangChain Document objects

        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If file does not exist
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {suffix}")

        logger.info(f"Loading document: {path.name} ({suffix})")

        if suffix == ".pdf":
            return cls._load_pdf(file_path)
        elif suffix == ".txt":
            return cls._load_text(file_path)
        elif suffix == ".md":
            return cls._load_markdown(file_path)
        elif suffix == ".docx":
            return cls._load_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    @staticmethod
    def _load_pdf(file_path: str) -> List[Document]:
        """Load PDF document."""
        try:
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            logger.info(f"Loaded PDF: {len(docs)} pages")
            return docs
        except ImportError:
            raise ImportError("pypdf is required for PDF loading. Install with: pip install pypdf")

    @staticmethod
    def _load_text(file_path: str) -> List[Document]:
        """Load plain text file."""
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(file_path, encoding="utf-8")
        docs = loader.load()
        logger.info(f"Loaded text file: {len(docs)} documents")
        return docs

    @staticmethod
    def _load_markdown(file_path: str) -> List[Document]:
        """Load Markdown file."""
        try:
            from langchain_community.document_loaders import UnstructuredMarkdownLoader
            loader = UnstructuredMarkdownLoader(file_path)
            docs = loader.load()
            logger.info(f"Loaded Markdown: {len(docs)} documents")
            return docs
        except ImportError:
            # Fallback to text loader
            logger.warning("unstructured not available, falling back to text loader for Markdown")
            return DocumentLoader._load_text(file_path)

    @staticmethod
    def _load_docx(file_path: str) -> List[Document]:
        """Load Word document (.docx)."""
        try:
            from langchain_community.document_loaders import Docx2txtLoader
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
            logger.info(f"Loaded DOCX: {len(docs)} documents")
            return docs
        except ImportError:
            raise ImportError(
                "docx2txt is required for DOCX loading. Install with: pip install docx2txt"
            )

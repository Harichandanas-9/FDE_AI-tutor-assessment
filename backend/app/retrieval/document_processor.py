"""
Document Processor
==================
Handles PDF and text file ingestion:
- PDF text extraction (pypdf + pdfplumber fallback)
- Text chunking with overlap
- Metadata extraction
- Document ID generation
- Integration with hybrid retriever for indexing
"""

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.retrieval.hybrid_retriever import HybridRetriever
from app.utils.helpers import chunk_text, clean_text, generate_document_id
from app.utils.logger import get_logger

logger = get_logger("retrieval.document_processor")


class DocumentProcessor:
    """
    Processes uploaded documents and indexes them in the retrieval system.
    Supports: PDF, TXT, MD files.
    """

    SUPPORTED_TYPES = {
        ".pdf": "pdf",
        ".txt": "text",
        ".md": "markdown",
    }

    def __init__(self, retriever: Optional[HybridRetriever] = None):
        self.retriever = retriever or HybridRetriever()
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def process_uploaded_file(
        self,
        file_path: str,
        filename: str,
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process an uploaded file: extract text, chunk, and index.

        Args:
            file_path: Full path to the uploaded file
            filename: Original filename
            collection_name: Optional collection grouping

        Returns:
            Processing result dict with stats
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        doc_type = self.SUPPORTED_TYPES.get(ext, "unknown")

        if doc_type == "unknown":
            raise ValueError(f"Unsupported file type: {ext}")

        logger.info(f"Processing file: '{filename}' ({doc_type})")

        # Extract text
        if doc_type == "pdf":
            pages = await self._extract_pdf_text(file_path)
        else:
            pages = await self._extract_text_file(file_path)

        if not pages:
            raise ValueError(f"Could not extract text from '{filename}'")

        # Generate document ID
        all_text = " ".join(page["content"] for page in pages)
        doc_id = generate_document_id(all_text, filename)

        # Chunk pages into indexable pieces
        chunks, metadatas, chunk_ids = [], [], []
        chunk_index = 0

        for page in pages:
            page_content = page["content"]
            page_num = page.get("page", 1)

            # Chunk long pages
            page_chunks = chunk_text(
                page_content,
                chunk_size=1000,
                chunk_overlap=200,
            )

            for chunk in page_chunks:
                chunk = clean_text(chunk)
                if not chunk or len(chunk) < 50:
                    continue

                chunk_id = f"{doc_id}_chunk_{chunk_index}"
                meta = {
                    "source": filename,
                    "doc_id": doc_id,
                    "page": str(page_num),
                    "type": doc_type,
                    "collection": collection_name or "default",
                    "chunk_index": str(chunk_index),
                }

                chunks.append(chunk)
                metadatas.append(meta)
                chunk_ids.append(chunk_id)
                chunk_index += 1

        if not chunks:
            raise ValueError(f"No indexable content extracted from '{filename}'")

        # Index in hybrid retriever
        await self.retriever.add_documents(
            chunks=chunks,
            metadatas=metadatas,
            ids=chunk_ids,
        )

        file_size = path.stat().st_size if path.exists() else 0

        result = {
            "document_id": doc_id,
            "filename": filename,
            "file_type": doc_type,
            "file_size_bytes": file_size,
            "num_pages": len(pages),
            "num_chunks": len(chunks),
            "collection_name": collection_name or "default",
        }

        logger.info(
            f"Document processed: '{filename}' | "
            f"pages={len(pages)} | chunks={len(chunks)} | doc_id={doc_id}"
        )

        return result

    async def _extract_pdf_text(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF using pypdf with pdfplumber fallback.

        Returns:
            List of {page, content} dicts, one per page
        """
        pages = []

        # Primary: pypdf
        try:
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({"page": page_num, "content": text})

            if pages:
                logger.debug(f"pypdf extracted {len(pages)} pages")
                return pages

        except Exception as e:
            logger.warning(f"pypdf extraction failed: {e} — trying pdfplumber")

        # Fallback: pdfplumber (better for complex layouts)
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    # Also try extracting tables
                    tables = page.extract_tables()
                    table_text = ""
                    for table in (tables or []):
                        for row in table:
                            if row:
                                table_text += " | ".join(
                                    str(cell) for cell in row if cell
                                ) + "\n"

                    combined = (text + "\n" + table_text).strip()
                    if combined:
                        pages.append({"page": page_num, "content": combined})

            logger.debug(f"pdfplumber extracted {len(pages)} pages")
            return pages

        except Exception as e:
            logger.error(f"pdfplumber extraction also failed: {e}")
            return []

    async def _extract_text_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract text from plain text or markdown file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if not content.strip():
                return []

            # For large text files, split into logical sections
            # (by double newlines / headers for markdown)
            sections = content.split("\n\n")
            combined = []
            current_chunk = ""

            for section in sections:
                if len(current_chunk) + len(section) < 2000:
                    current_chunk += section + "\n\n"
                else:
                    if current_chunk:
                        combined.append({"page": len(combined) + 1, "content": current_chunk})
                    current_chunk = section + "\n\n"

            if current_chunk:
                combined.append({"page": len(combined) + 1, "content": current_chunk})

            return combined if combined else [{"page": 1, "content": content}]

        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return []

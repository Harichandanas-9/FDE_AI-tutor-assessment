"""
Document Upload & Management Routes
=====================================
Handles PDF and text file uploads, indexing, and listing.
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.config import settings
from app.retrieval.document_processor import DocumentProcessor
from app.retrieval.hybrid_retriever import HybridRetriever
from app.schemas.models import DocumentUploadResponse, DocumentListResponse, DocumentListItem, BaseResponse
from app.utils.logger import get_logger

logger = get_logger("api.documents")
router = APIRouter()

_processor = DocumentProcessor()

# Track indexed documents in memory (extensible to DB)
_indexed_documents: List[dict] = []


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    collection_name: Optional[str] = Form(default="default"),
):
    """
    Upload and index a PDF or text document.
    The document is chunked, embedded, and stored in ChromaDB + BM25 index.
    """
    # Validate file type
    allowed_extensions = {".pdf", ".txt", ".md"}
    filename = file.filename or "document"
    ext = Path(filename).suffix.lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(allowed_extensions)}",
        )

    # Validate file size
    content = await file.read()
    file_size = len(content)
    max_size = settings.max_file_size_bytes

    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum: {settings.MAX_FILE_SIZE_MB}MB",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # Save to upload directory
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    file_path = upload_dir / safe_filename

    try:
        with open(file_path, "wb") as f:
            f.write(content)

        # Process and index the document
        result = await _processor.process_uploaded_file(
            file_path=str(file_path),
            filename=filename,
            collection_name=collection_name,
        )

        # Track in memory registry
        _indexed_documents.append({
            "document_id": result["document_id"],
            "filename": filename,
            "file_type": result["file_type"],
            "num_chunks": result["num_chunks"],
            "file_size_bytes": file_size,
            "indexed_at": __import__("datetime").datetime.utcnow().isoformat(),
            "collection": collection_name,
        })

        logger.info(
            f"Document uploaded and indexed: '{filename}' | "
            f"chunks={result['num_chunks']} | doc_id={result['document_id']}"
        )

        return DocumentUploadResponse(
            document_id=result["document_id"],
            filename=filename,
            file_size_bytes=file_size,
            num_chunks=result["num_chunks"],
            collection_name=collection_name or "default",
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.error(f"Document processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}",
        )
    finally:
        # Clean up temp file
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception:
                pass


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """List all indexed documents."""
    items = [
        DocumentListItem(
            document_id=d["document_id"],
            filename=d["filename"],
            file_type=d["file_type"],
            num_chunks=d["num_chunks"],
            indexed_at=d["indexed_at"],
            file_size_bytes=d.get("file_size_bytes"),
        )
        for d in _indexed_documents
    ]

    return DocumentListResponse(
        documents=items,
        total=len(items),
    )


@router.delete("/documents/{document_id}", response_model=BaseResponse)
async def delete_document(document_id: str):
    """Delete a document from the index."""
    from app.retrieval.vector_store import vector_store
    from app.retrieval.bm25_retriever import bm25_retriever

    success = await vector_store.delete_document(document_id)

    # Remove from registry
    global _indexed_documents
    before = len(_indexed_documents)
    _indexed_documents = [d for d in _indexed_documents if d["document_id"] != document_id]
    removed = before - len(_indexed_documents)

    if not success and removed == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found",
        )

    return BaseResponse(message=f"Document '{document_id}' deleted successfully")

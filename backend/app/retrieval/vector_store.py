"""
ChromaDB Vector Store
======================
Manages the vector database for semantic document retrieval.
Handles:
- Collection initialization
- Document embedding and storage
- Semantic similarity search
- Metadata filtering
- Document management (add/delete/list)
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import AsyncOpenAI

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("retrieval.vector_store")


class VectorStore:
    """
    ChromaDB-backed vector store for semantic document retrieval.
    Uses OpenAI embeddings for document and query encoding.
    """

    def __init__(self):
        self.persist_dir = settings.CHROMA_PERSIST_DIRECTORY
        self.collection_name = settings.CHROMA_COLLECTION_NAME
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL

        self._client: Optional[chromadb.Client] = None
        self._collection = None
        self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def initialize(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            # Ensure persist directory exists
            Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

            # Create persistent ChromaDB client
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},  # Use cosine similarity
            )

            count = self._collection.count()
            logger.info(
                f"ChromaDB initialized: collection='{self.collection_name}' | "
                f"documents={count} | persist_dir='{self.persist_dir}'"
            )

        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}", exc_info=True)
            raise

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using OpenAI API.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        try:
            response = await self._openai.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    async def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> int:
        """
        Add documents to the vector store.

        Args:
            documents: List of document text chunks
            metadatas: List of metadata dicts (source, page, type, etc.)
            ids: List of unique document IDs

        Returns:
            Number of documents added
        """
        if not documents:
            return 0

        if self._collection is None:
            await self.initialize()

        try:
            # Generate embeddings
            embeddings = await self.embed_texts(documents)

            # Add to ChromaDB
            self._collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info(f"Added {len(documents)} documents to vector store")
            return len(documents)

        except Exception as e:
            logger.error(f"Failed to add documents: {e}", exc_info=True)
            raise

    async def search(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        """
        Semantic similarity search.

        Args:
            query: Search query text
            top_k: Number of results to return
            metadata_filter: Optional ChromaDB where clause for metadata filtering

        Returns:
            Tuple of (documents, scores)
            documents: List of {id, content, metadata} dicts
            scores: List of cosine similarity scores (0-1, higher = more similar)
        """
        if self._collection is None:
            await self.initialize()

        try:
            # Get collection count
            count = self._collection.count()
            if count == 0:
                logger.debug("Vector store is empty — no semantic results")
                return [], []

            actual_k = min(top_k, count)

            # Embed the query
            query_embedding = (await self.embed_texts([query]))[0]

            # Build query kwargs
            query_kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": actual_k,
                "include": ["documents", "metadatas", "distances"],
            }

            if metadata_filter:
                # Build ChromaDB where clause
                where_clause = self._build_where_clause(metadata_filter)
                if where_clause:
                    query_kwargs["where"] = where_clause

            results = self._collection.query(**query_kwargs)

            # Parse results
            documents = []
            scores = []

            if results and results.get("ids") and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    doc_content = results["documents"][0][i]
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i]

                    # Convert distance to similarity score (cosine distance → similarity)
                    similarity = 1.0 - distance

                    documents.append({
                        "id": doc_id,
                        "content": doc_content,
                        "metadata": metadata,
                    })
                    scores.append(similarity)

            logger.debug(f"Vector search: query_len={len(query)} | results={len(documents)}")
            return documents, scores

        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            return [], []

    def _build_where_clause(self, metadata_filter: Dict[str, Any]) -> Optional[Dict]:
        """Build ChromaDB where clause from metadata filter dict."""
        if not metadata_filter:
            return None

        conditions = []
        for key, value in metadata_filter.items():
            if value and isinstance(value, str):
                conditions.append({key: {"$eq": value}})
            elif value and isinstance(value, list):
                conditions.append({key: {"$in": value}})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    async def delete_document(self, document_id: str) -> bool:
        """Delete all chunks belonging to a document by prefix."""
        if self._collection is None:
            return False

        try:
            # Get all IDs with this document prefix
            all_ids = self._collection.get(where={"doc_id": {"$eq": document_id}})
            if all_ids and all_ids.get("ids"):
                self._collection.delete(ids=all_ids["ids"])
                logger.info(f"Deleted {len(all_ids['ids'])} chunks for doc_id={document_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    def get_document_count(self) -> int:
        """Return total number of document chunks in the collection."""
        if self._collection is None:
            return 0
        return self._collection.count()

    async def list_document_sources(self) -> List[str]:
        """List unique source document names in the collection."""
        if self._collection is None:
            return []
        try:
            all_meta = self._collection.get(include=["metadatas"])
            sources = set()
            for meta in all_meta.get("metadatas", []):
                if meta and "source" in meta:
                    sources.add(meta["source"])
            return sorted(sources)
        except Exception:
            return []

    async def reset_collection(self) -> None:
        """Reset (clear) the entire collection. Use with caution."""
        if self._client:
            self._client.delete_collection(self.collection_name)
            self._collection = self._client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.warning(f"Collection '{self.collection_name}' has been reset")


# Singleton instance
vector_store = VectorStore()

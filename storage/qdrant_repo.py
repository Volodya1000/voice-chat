# repositories/qdrant_repo.py
from typing import List, Optional
from uuid import uuid4
import logging
from qdrant_client import QdrantClient
from qdrant_client.models  import Distance
from qdrant_client.http import models

from settings.settings import QdrantSettings
from storage.chunk import Chunk


class QdrantRepository:
    def __init__(self, settings: QdrantSettings, embedding_dim: int):
        self.settings = settings
        self.embedding_dim = embedding_dim
        self.client = QdrantClient(host=settings.host, port=settings.port)
        self.logger = logging.getLogger(__name__)
        self.health_check()

    def _collection_name(self, chat_id: int) -> str:
        return f"chat_{chat_id}"

    def _ensure_collection_exists(self, chat_id: int):
        name = self._collection_name(chat_id)
        if not self.client.collection_exists(name):
            self.client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE,
                ),
            )

    def add_document_chunks(self, chat_id: int, chunks: List[Chunk]):
        """
        Добавляет чанки одного документа в коллекцию соответствующего чата.
        """
        if not chunks:
            return

        self._ensure_collection_exists(chat_id)
        collection = self._collection_name(chat_id)

        points = [
            models.PointStruct(
                id=str(uuid4()),
                vector=chunk.embedding,
                payload={
                    "text": chunk.text,
                    "doc_id": chunk.doc_id,
                    "doc_name": chunk.doc_name,
                },
            )
            for chunk in chunks
        ]

        self.client.upsert(collection_name=collection, points=points)

    def search(
        self,
        chat_id: int,
        query_vector: List[float],
        top_k: int = 5,
        doc_id: Optional[str] = None,
    ):
        collection = self._collection_name(chat_id)
        if not self.client.collection_exists(collection):
            return []

        query_filter = None
        if doc_id:
            query_filter = models.Filter(
                must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))]
            )

        results = self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )

        return [
            {
                "text": r.payload.get("text"),
                "doc_id": r.payload.get("doc_id"),
                "doc_name": r.payload.get("doc_name"),
                "score": r.score,
            }
            for r in results
        ]

    def health_check(self) -> bool:
        """Check if Qdrant is healthy and accessible."""
        try:
            collections = self.client.get_collections()
            self.logger.info(f"Health check passed, found {len(collections.collections)} collections")
            return True

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

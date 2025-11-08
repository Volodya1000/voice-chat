# services/document_service.py
import io
import uuid
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from fastapi.concurrency import run_in_threadpool
from PyPDF2 import PdfReader
from docx import Document as DocxDocument
from storage.qdrant_repo import QdrantRepository
from storage.embedding_service import EmbeddingService
from settings.settings import SplittingSettings
from storage.chunk import Chunk


class DocumentService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        qdrant_repo: QdrantRepository,
        splitting_settings: SplittingSettings,
    ):
        self.embedding_service = embedding_service
        self.qdrant_repo = qdrant_repo
        self.splitting_settings = splitting_settings

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.splitting_settings.chunk_size,
            chunk_overlap=self.splitting_settings.chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", " ", ""],
        )

    def _parse_pdf_sync(self, file_bytes: bytes) -> str:
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def _parse_docx_sync(self, file_bytes: bytes) -> str:
        doc = DocxDocument(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)

    async def process_and_store(self, chat_id: int, filename: str, file_bytes: bytes):
        lower = filename.lower()
        if lower.endswith(".pdf"):
            text = await run_in_threadpool(self._parse_pdf_sync, file_bytes)
        elif lower.endswith(".docx") or lower.endswith(".doc"):
            text = await run_in_threadpool(self._parse_docx_sync, file_bytes)
        else:
            raise ValueError("Unsupported file type: only PDF and DOCX are supported")

        if not text.strip():
            return {"doc_id": None, "chunks_count": 0}

        chunks_texts: List[str] = self.splitter.split_text(text)
        embeddings = await self.embedding_service.embed_texts(chunks_texts)

        doc_id = str(uuid.uuid4())
        chunks = [
            Chunk(
                embedding=list(map(float, emb)),
                text=chunk_text,
                chat_id=chat_id,
                doc_id=doc_id,
                doc_name=filename,
            )
            for emb, chunk_text in zip(embeddings, chunks_texts)
        ]

        await run_in_threadpool(self.qdrant_repo.add_document_chunks, chat_id, chunks)

        return {"doc_id": doc_id, "doc_name": filename, "chunks_count": len(chunks)}

    async def search(self, chat_id: int, query: str, top_k: int = 5):
        qvec = await self.embedding_service.embed_query(query)
        return await run_in_threadpool(self.qdrant_repo.search, chat_id, qvec, top_k)

# services/embedding_service.py
from typing import List
from sentence_transformers import SentenceTransformer
from fastapi.concurrency import run_in_threadpool

from settings.settings import EmbeddingSettings


class EmbeddingService:
    def __init__(self, settings: EmbeddingSettings):
        self.settings = settings
        # Загружаем модель один раз на старте
        self.model = SentenceTransformer(self.settings.model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Асинхронно (через threadpool) получить эмбеддинги для списка строк.
        """
        res = await run_in_threadpool(self.model.encode, texts, show_progress_bar=False)
        return [list(map(float, v)) for v in res]

    async def embed_query(self, text: str) -> List[float]:
        res = await run_in_threadpool(self.model.encode, [text], show_progress_bar=False)
        return list(map(float, res[0]))

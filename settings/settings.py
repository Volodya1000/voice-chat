# settings.py
from pydantic_settings import BaseSettings



class QdrantSettings(BaseSettings):
    host: str = "localhost"
    port: int = 6333
    distance: str = "COSINE"

    class Config:
        env_prefix = "QDRANT_"


class EmbeddingSettings(BaseSettings):
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    # можно добавить batch_size, device и пр.
    class Config:
        env_prefix = "EMB_"


class SplittingSettings(BaseSettings):
    chunk_size: int = 800
    chunk_overlap: int = 100

    class Config:
        env_prefix = "SPLIT_"


class AppSettings(BaseSettings):
    # AppSettings содержит ТОЛЬКО вложенные настройки
    qdrant: QdrantSettings = QdrantSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    splitting: SplittingSettings = SplittingSettings()

    class Config:
        env_prefix = ""

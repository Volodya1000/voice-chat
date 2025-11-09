# containers.py
from dependency_injector import containers, providers
from repositories.user_repo import UserRepository
from repositories.chat_repo import ChatRepository
from repositories.message_repo import MessageRepository
from services.agent_service import AgentService
from services.chat_service import ChatService
from services.broadcaster_service import Broadcaster
from db import get_session
from services.transcription_service import TranscriptionService
from services.local_tts_service import LocalTextToVoiceService
from settings.settings import AppSettings
from services.document_service import DocumentService
from storage.embedding_service import EmbeddingService
from storage.qdrant_repo import QdrantRepository


class Container(containers.DeclarativeContainer):
    """
    Контейнер зависимостей приложения.
    """
    # Указываем модули, в которые будет производиться инъекция.
    # Это позволяет использовать @inject в api.py и web.py
    wiring_config = containers.WiringConfiguration(
        modules=[
            "endpoints.web_pages",
            "endpoints.web_actions",
            "endpoints.api_users",
            "endpoints.api_messages",
            "services.chat_service",
        ]
    )

    # --- Провайдеры ---

    # 1. База данных
    # Resource используется для зависимостей, которые являются
    # генераторами (с yield), как наш get_session.
    db_session = providers.Resource(get_session)

    # 2. Репозитории
    # Factory создает новый экземпляр при каждом запросе.
    # Мы "связываем" аргумент 'session' в __init__ репозитория
    # с нашим провайдером db_session.
    user_repo: providers.Factory[UserRepository] = providers.Factory(
        UserRepository,
        session=db_session,
    )

    chat_repo: providers.Factory[ChatRepository] = providers.Factory(
        ChatRepository,
        session=db_session,
    )

    message_repo: providers.Factory[MessageRepository] = providers.Factory(
        MessageRepository,
        session=db_session,
    )

    broadcaster = providers.Singleton(Broadcaster)

    local_tts_service = providers.Singleton(LocalTextToVoiceService)





    transcription_service: providers.Singleton[TranscriptionService] = providers.Singleton(
        TranscriptionService
    )

    app_settings = providers.Singleton(AppSettings)

    # Делегаты к вложенным настройкам
    qdrant_settings = providers.Delegate(app_settings.provided.qdrant)
    embedding_settings = providers.Delegate(app_settings.provided.embedding)
    splitting_settings = providers.Delegate(app_settings.provided.splitting)

    embedding_service = providers.Singleton(
        EmbeddingService,
        settings=embedding_settings(),
    )
    qdrant_repo = providers.Singleton(
        QdrantRepository,
        settings=qdrant_settings(),
        embedding_dim=embedding_service.provided.dim,
    )

    document_service = providers.Factory(
        DocumentService,
        embedding_service=embedding_service,
        qdrant_repo=qdrant_repo,
        splitting_settings=splitting_settings(),
    )

    agent_service = providers.Singleton(
        AgentService,
        document_service=document_service,
    )

    chat_service: providers.Factory[ChatService] = providers.Factory(
        ChatService,
        message_repo=message_repo,
        broadcaster=broadcaster,
        agent_service=agent_service,
        tts_service=local_tts_service
    )


# Создаем единственный экземпляр контейнера для всего приложения
container = Container()
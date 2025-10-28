# containers.py
from dependency_injector import containers, providers
from repositories.user_repo import UserRepository
from repositories.chat_repo import ChatRepository
from repositories.message_repo import MessageRepository
from services.chat_service import ChatService
from db import get_session

class Container(containers.DeclarativeContainer):
    """
    Контейнер зависимостей приложения.
    """
    # Указываем модули, в которые будет производиться инъекция.
    # Это позволяет использовать @inject в api.py и web.py
    wiring_config = containers.WiringConfiguration(modules=["api", "web"])

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

    # 3. Сервисы
    # Сервисы так же являются Factory.
    # Мы "связываем" зависимость chat_service от message_repo
    # с нашим провайдером message_repo.
    chat_service: providers.Factory[ChatService] = providers.Factory(
        ChatService,
        message_repo=message_repo,
    )

# Создаем единственный экземпляр контейнера для всего приложения
container = Container()
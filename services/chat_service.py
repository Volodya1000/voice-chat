from models import MessageType
from langchain_ollama.llms import OllamaLLM
import asyncio

class ChatService:
    def __init__(self, message_repo):
        """
        message_repo: любой объект, у которого есть метод `add_message(chat_id, content, message_type)`
        """
        self.message_repo = message_repo
        self.llm = OllamaLLM(model="saiga_llama3_8b:latest")

    async def process_user_message(self, chat_id: int, content: str) -> None:
        # Сохраняем сообщение пользователя
        await self.message_repo.add_message(
            chat_id=chat_id,
            content=content,
            message_type=MessageType.USER
        )

        # Получаем ответ модели через LangChain LLM
        model_response = await self._invoke_llm_async(content)

        # Сохраняем ответ модели
        await self.message_repo.add_message(
            chat_id=chat_id,
            content=model_response,
            message_type=MessageType.MODEL
        )

    async def _invoke_llm_async(self, prompt: str) -> str:
        """
        Обёртка для вызова синхронного метода `invoke` в асинхронном коде
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.llm.invoke, prompt)

# agent_service.py
import asyncio
from typing import List, AsyncGenerator
from functools import partial

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_classic.chains.llm import LLMChain
from langchain_classic.chains.llm_math.base import LLMMathChain
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.tools import Tool
from langchain_ollama import ChatOllama

from services.broadcaster_service import Broadcaster
from services.document_service import DocumentService

def get_weather(query: str) -> str:
    """Пример API инструмента погоды."""
    print(f"[Agent Tool] Weather query: '{query}'")
    return "Погода в Минске: +7°C, облачно."


def query_library(query: str) -> str:
    """Пример API инструмента библиотеки."""
    print(f"[Agent Tool] Library query: '{query}'")
    return f"Результаты поиска в библиотеке по запросу '{query}'."


class AgentService:
    def __init__(self, document_service: DocumentService):
        self.document_service = document_service

        # 1. Инициализация LLM
        self.llm = ChatOllama(
            model="qwen2.5-coder:14b",
            temperature=0.3,
            num_ctx=4096,
            streaming=True
        )

        # 2. Инструменты
        math_chain = LLMMathChain.from_llm(llm=self.llm)

        self.base_tools = [
            Tool(
                name="MathCalculator",
                func=math_chain.run,
                description="Solves mathematical expressions and computational tasks."
            ),
            Tool(
                name="WeatherAPI",
                func=get_weather,
                description="Retrieves current weather information based on a user query."
            ),
            Tool(
                name="LibraryAPI",
                func=query_library,
                description="Searches for information within the company's internal library."
            )
        ]

        # 3. Промпт агента
        self.prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content="Ты — полезный помощник. Используй доступные инструменты для ответа на вопросы."
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

    # ---------------------------------------------------------------------
    # Инструмент RAG, асинхронный
    # ---------------------------------------------------------------------
    async def _rag_tool_async(self, chat_id: int, query: str) -> str:
        """
        Асинхронный вызов поиска по документам через DocumentService.
        """
        results = await self.document_service.search(chat_id, query, top_k=5)
        if not results:
            return f"[RAG]: не найдено информации по запросу '{query}'"

        # Исправлено: доступ по ключу 'text'
        return "\n".join([f"- {r['text'][:300]}..." for r in results])

    # Обертка для синхронного вызова в Tool
    def _rag_tool(self, chat_id: int, query: str) -> str:
        return asyncio.run(self._rag_tool_async(chat_id, query))

    # ---------------------------------------------------------------------
    # Создание AgentExecutor
    # ---------------------------------------------------------------------
    def _get_agent_executor(self, chat_id: int) -> AgentExecutor:
        rag_tool = Tool(
            name="RAG",
            func=partial(self._rag_tool, chat_id),
            description="Используется для поиска дополнительной информации по вопросам, когда знаний модели недостаточно"
        )

        all_tools = self.base_tools + [rag_tool]

        agent = create_tool_calling_agent(
            self.llm,
            all_tools,
            self.prompt,
        )

        return AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=all_tools,
            verbose=True,
            handle_parsing_errors=True
        )

    async def arun_agent_stream(
            self,
            chat_id: int,
            input_query: str,
            history_messages: List[BaseMessage]
    ) -> AsyncGenerator[str, None]:
        """
        Генератор токенов от агента.
        Не зависит от Broadcaster, просто отдаёт токены по мере генерации.
        """
        full_text = []
        agent_executor = self._get_agent_executor(chat_id)
        input_data = {
            "input": input_query,
            "chat_history": history_messages
        }

        try:
            async for chunk in agent_executor.astream(input_data):
                if "output" in chunk:
                    token = chunk["output"]
                    if token:
                        full_text.append(token)
                        yield token  # <-- просто отдаём токен

                if "intermediate_steps" in chunk and chunk["intermediate_steps"]:
                    print(f"[Agent Step]: {chunk['intermediate_steps']}")

        except Exception as e:
            error_msg = f"\n[ОШИБКА ГЕНЕРАЦИИ ОТВЕТА АГЕНТОМ]: {e}"
            full_text.append(error_msg)
            yield error_msg

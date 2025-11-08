import asyncio
from typing import List
from functools import partial

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_classic.chains.llm import LLMChain
from langchain_classic.chains.llm_math.base import LLMMathChain
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.tools import Tool
from langchain_ollama import ChatOllama

from services.broadcaster_service import Broadcaster


def query_rag(query: str, chat_id: int | None = None) -> str:
    print(f"[Agent Tool] RAG query: '{query}' for chat_id={chat_id}")
    return f"[RAG]: найден контент по '{query}' (chat_id={chat_id})"


def get_weather(query: str) -> str:
    """Пример API инструмента погоды."""
    print(f"[Agent Tool] Weather query: '{query}'")
    return "Погода в Минске: +7°C, облачно."


def query_library(query: str) -> str:
    """Пример API инструмента библиотеки."""
    print(f"[Agent Tool] Library query: '{query}'")
    return f"Результаты поиска в библиотеке по запросу '{query}'."


# -------------------------------------------------------------------------
# Сервис Агента
# -------------------------------------------------------------------------

class AgentService:
    def __init__(self):
        # 1. Инициализируем LLM
        self.llm = ChatOllama(
            model="evilfreelancer/rugpt3.5:13b-q5_0",
            temperature=0.3,
            num_ctx=4096,
            streaming=True
        )

        # 2. Инициализируем базовые инструменты (chains)
        math_chain = LLMMathChain.from_llm(llm=self.llm)

        reasoning_prompt = PromptTemplate(
            input_variables=["question"],
            template="Ты аналитический агент. Ответь шаг за шагом: {question}"
        )
        reasoning_chain = LLMChain(llm=self.llm, prompt=reasoning_prompt)

        # Сохраняем инструменты, которые не зависят от chat_id
        self.base_tools = [
            Tool(
                name="MathCalculator",
                func=math_chain.run,
                description="Решает математические выражения и задачи"
            ),
            Tool(
                name="ReasoningTool",
                func=reasoning_chain.run,
                description="Используется для логических и рассуждающих задач"
            ),
            Tool(
                name="WeatherAPI",
                func=get_weather,
                description="Получает погоду по запросу"
            ),
            Tool(
                name="LibraryAPI",
                func=query_library,
                description="Ищет информацию в библиотеке компании"
            )
        ]

        # 3. Базовый промпт для ReAct агента с поддержкой истории
        self.prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content="Ты — полезный помощник для сотрудников компании УП «Белтехосмотр». Используй доступные инструменты для ответа на вопросы."),
                # MessagesPlaceholder отвечает за вставку истории
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),  # для шагов ReAct
            ]
        )

    def _get_agent_executor(self, chat_id: int) -> AgentExecutor:
        """
        Создает RAG-инструмент с chat_id и собирает AgentExecutor.
        """
        # 4. Создаем RAG-инструмент с привязкой chat_id
        rag_tool = Tool(
            name="RAG",
            func=partial(query_rag, chat_id=chat_id),
            description="Используется для поиска информации в прикреплённых документах"
        )

        all_tools = self.base_tools + [rag_tool]

        # 5. Создаем Agent с корректным вызовом
        agent = create_tool_calling_agent(
            self.llm,
            all_tools,
            self.prompt,
        )

        # 6. Создаем Agent Executor (запускает агент и выполняет инструменты)
        return AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=all_tools,
            verbose=True,
            handle_parsing_errors=True  # Обработка ошибок парсинга
        )

    async def arun_agent_stream(
            self,
            chat_id: int,
            model_msg_id: int,
            input_query: str,
            history_messages: List[BaseMessage],
            broadcaster: Broadcaster
    ) -> str:
        full_text = []

        # Получаем исполнителя агента
        agent_executor = self._get_agent_executor(chat_id)

        input_data = {
            "input": input_query,
            # Ключ должен соответствовать placeholder'у в промпте
            "chat_history": history_messages
        }

        try:
            # astream - асинхронно стримит все шаги агента
            async for chunk in agent_executor.astream(input_data):
                # 'output' - это ключ, содержащий финальный ответ
                if "output" in chunk:
                    token = chunk["output"]
                    if token:
                        full_text.append(token)
                        # Публикуем токен через broadcaster
                        await broadcaster.publish_token(chat_id, model_msg_id, token)

                # Вы можете добавить логирование промежуточных шагов для отладки
                if "intermediate_steps" in chunk and chunk["intermediate_steps"]:
                    print(f"[Agent Step]: {chunk['intermediate_steps']}")

        except Exception as e:
            print(f"Error during Agent stream: {e}")
            error_msg = "\n[ОШИБКА ГЕНЕРАЦИИ ОТВЕТА АГЕНТОМ]"
            await broadcaster.publish_token(chat_id, model_msg_id, error_msg)
            full_text.append(error_msg)

        return "".join(full_text)

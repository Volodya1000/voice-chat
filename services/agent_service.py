# agent_service.py
import asyncio
from typing import List, AsyncGenerator
from functools import partial

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_classic.chains.llm_math.base import LLMMathChain
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool
from langchain_ollama import ChatOllama

from services.document_service import DocumentService
from tools.library_tools import get_available_book_count_by_author, get_book_info, get_last_book_from_author, \
    get_book_author
from tools.weather_tool import get_weather


class AgentService:
    def __init__(self, document_service: DocumentService):
        self.document_service = document_service

        # 1. Инициализация LLM
        self.llm = ChatOllama(
            model="gpt-oss:20b-cloud",
            temperature=0.3,
            num_ctx=4096,
            streaming=True
        )

        # 2. Инструменты
        math_chain = LLMMathChain.from_llm(llm=self.llm)

        self.base_tools = [
            Tool(
                name="WeatherAPI",
                func=get_weather,
                description=(
                    "Retrieves current weather for a specified city. "
                    "Use only this tool to answer questions about weather in cities."
                )
            ),
            Tool(
                name="WeatherAPI",
                func=get_weather,
                description="Retrieves current weather information based on a user query."
            ),
            get_available_book_count_by_author,
            get_book_info,
            get_last_book_from_author,
            get_book_author,
        ]

        # 3. Промпт агента
        self.prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=(
                        "Ты — полезный помощник. "
                        "Если ты не знаешь точного ответа из своих знаний, "
                        "обязательно используй инструмент 'RAG' для поиска информации в документах. "
                        "Не придумывай факты."
                        "Отвечай только на русском языке"
                    )
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

    async def _rag_tool_async(self, chat_id: int, query: str) -> str:
        results = await self.document_service.search(chat_id, query, top_k=5)
        if not results:
            return f"[RAG]: не найдено информации по запросу '{query}'"

        return "\n".join([f"- {r['text'][:300]}..." for r in results])

    def _rag_tool(self, chat_id: int, query: str) -> str:
        return asyncio.run(self._rag_tool_async(chat_id, query))

    def _get_agent_executor(self, chat_id: int) -> AgentExecutor:
        rag_tool = Tool(
            name="RAG",
            func=partial(self._rag_tool, chat_id),
            description=(
                "Searches uploaded documents for information the model may not know. "
                "Always use this tool when the model's knowledge may be insufficient. "
                "Do NOT answer without using this tool if unsure."
            )
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

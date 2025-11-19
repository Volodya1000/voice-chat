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
    def __init__(self, document_service: DocumentService, llm_weight: float = 0.7,
                 ):
        self.document_service = document_service
        self.llm_weight = llm_weight
        self.document_service = document_service

        self.llm = ChatOllama(
            model="gpt-oss:20b-cloud",
            temperature=0.3,
            num_ctx=4096,
            streaming=True
        )

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
                name="MathCalculator",
                func=math_chain.run,
                description=(
                    "Calculates mathematical expressions and solves math problems. "
                    "Always use this tool to answer any question related to mathematics. "
                    "Do NOT attempt to answer math questions without using this tool."
                )
            ),
            get_available_book_count_by_author,
            get_book_info,
            get_last_book_from_author,
            get_book_author,
        ]

        self.prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=(
                        "Ты — полезный помощник. "
                        "Используй только достоверную информацию из RAG и инструментов. "
                        "Отвечай только на русском языке."
                    )
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

    def _get_agent_executor(self, chat_id: int) -> AgentExecutor:
        all_tools = self.base_tools
        agent = create_tool_calling_agent(
            self.llm,
            all_tools,
            self.prompt,
        )

        return AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=all_tools,
            verbose=True,
            handle_parsing_errors=True,
            return_intermediate_steps=True

        )

    async def get_rag_context(self, chat_id: int, query: str) -> str:
        """
        Возвращает объединенный текст всех релевантных документов,
        отфильтрованных по комбинированной оценке LLM + векторной.
        """
        results = await self.document_service.search(chat_id, query, top_k=20)

        # Сортируем по score
        sorted_results = sorted(results, key=lambda r: r["score"], reverse=True)

        topn = sorted_results[:10]

        # Логируем кратко: score + начало текста
        print("[RAG LOG] Найдено чанков:", len(topn))
        for idx, r in enumerate(topn, 1):
            snippet = r["text"][:80].replace("\n", " ")  # первые 80 символов
            print(f"  {idx}. score={r['score']:.3f}, text='{snippet}...'")

        # Возвращаем текст
        top5_texts = [r["text"] for r in topn]
        return "\n".join(top5_texts)

    async def arun_agent_stream(
            self,
            chat_id: int,
            input_query: str,
            history_messages: List[BaseMessage]
    ) -> AsyncGenerator[str, None]:

        # Всегда добавляем RAG контекст
        rag_context = await self.get_rag_context(chat_id, input_query)
        if rag_context:
            full_input = f"[RAG контекст]:\n{rag_context}\n\n[Вопрос]: {input_query}"
        else:
            full_input = input_query

        full_text = []
        agent_executor = self._get_agent_executor(chat_id)
        input_data = {
            "input": full_input,
            "chat_history": history_messages
        }

        try:
            used_tools = set()
            async for chunk in agent_executor.astream(input_data):
                if "output" in chunk:
                    token = chunk["output"]
                    if token:
                        full_text.append(token)
                        yield token

                if "intermediate_steps" in chunk and chunk["intermediate_steps"]:
                    for step in chunk["intermediate_steps"]:
                        tool_name = step[0].tool if hasattr(step[0], "tool") else None

                        if tool_name:
                            used_tools.add(tool_name)
                    print(f"[Agent Step]: {chunk['intermediate_steps']}")
            if used_tools:
                tools_list = ", ".join(sorted(used_tools))
                conclusion = f"Для ответа были использованы инструменты: {tools_list}"
                full_text.append(conclusion)
                yield conclusion

        except Exception as e:
            error_msg = f"\n[ОШИБКА ГЕНЕРАЦИИ ОТВЕТА АГЕНТОМ]: {e}"
            full_text.append(error_msg)
            yield error_msg

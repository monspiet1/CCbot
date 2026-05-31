import sqlite3
from typing import cast

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from pydantic import BaseModel

from nodes import GraphState
from workflow import workflow

checkpoint_conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
memory = SqliteSaver(checkpoint_conn)

app_graph = workflow.compile(checkpointer=memory)

analytics_conn = sqlite3.connect("analytics.db", check_same_thread=False)
cursor = analytics_conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id TEXT,
        user_message TEXT,
        bot_response TEXT,
        current_stage TEXT,
        is_tutoring_active BOOLEAN,
        approved BOOLEAN,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
analytics_conn.commit()

api = FastAPI(title="Wing Agent API")


class ChatRequest(BaseModel):
    pergunta: str
    thread_id: str


class ChatResponse(BaseModel):
    rota: str
    resposta: str


@api.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        config = RunnableConfig(configurable={"thread_id": request.thread_id})

        inputs = cast(
            GraphState, {"messages": [HumanMessage(content=request.pergunta)]}
        )

        final_state = app_graph.invoke(inputs, config=config)

        raw_content = final_state["messages"][-1].content

        if isinstance(raw_content, list):
            resposta_bot = "".join(
                [
                    bloco.get("text", "")
                    for bloco in raw_content
                    if isinstance(bloco, dict)
                ]
            )
        else:
            resposta_bot = str(raw_content)

        is_active = final_state.get("is_tutoring_active", False)
        estagio = final_state.get("current_stage", "casual")

        aprovado = final_state.get("approved", None)

        rota_usada = estagio if is_active else "casual_ou_general"

        analytics_cursor = analytics_conn.cursor()
        analytics_cursor.execute(
            """
            INSERT INTO chat_logs (thread_id, user_message, bot_response, current_stage, is_tutoring_active, approved)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                request.thread_id,
                request.pergunta,
                resposta_bot,
                estagio,
                is_active,
                aprovado,
            ),
        )
        analytics_conn.commit()

        return ChatResponse(rota=rota_usada, resposta=resposta_bot)

    except Exception as e:
        print(f"Erro na API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from typing import cast

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel

from nodes import GraphState
from workflow import workflow

memory = MemorySaver()

app_graph = workflow.compile(checkpointer=memory)

api = FastAPI(title="CCBot Agent API")


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
        rota_usada = estagio if is_active else "casual_ou_general"

        return ChatResponse(rota=rota_usada, resposta=resposta_bot)

    except Exception as e:
        print(f"Erro na API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

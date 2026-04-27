from typing import Literal, List
from langchain_core.documents import Document

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langgraph.graph import MessagesState
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from vector_store import vector_store

from dotenv import load_dotenv

load_dotenv("./.env")

llm_generator = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    temperature=1.0
)

llm_evaluator = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    temperature=0.0
)

class GraphState(MessagesState):
    context: List[Document]
    is_relevant: bool

class RelevanceDecision(BaseModel):
    is_relevant: bool = Field(
        description="Retorne True se o contexto for suficiente, correto e relevante para responder à pergunta. Caso contrário, retorne False."
    )

def retrieve_context(state: GraphState):
    """Retrieve top documents from ChromaDB Collection bases on query."""

    query = state["messages"][-1].content

    if not isinstance(query, str):
        # Handle list-based content by joining it or picking the first text block
        # For now, we'll just force it or raise an error
        return {"context": ""}

    docs = vector_store.similarity_search(query, k=3)

    return {"context": docs}

def relevance_context(state: GraphState):
    """Determine whether the retrieved context is relevant and sufficient."""

    query = state["messages"][-1].content
    context_docs = state["context"]

    formatted_context = "\n\n".join(
        f"Fonte {i+1}:\n{doc.page_content}" 
        for i, doc in enumerate(context_docs)
    )

    structured_llm = llm_evaluator.with_structured_output(RelevanceDecision)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Você é um avaliador de contexto extremamente rigoroso. "
            "Sua função é determinar se os documentos recuperados fornecem informações SUFICIENTES, "
            "CORRETAS e RELEVANTES para gerar uma resposta completa e altamente didática para a pergunta do usuário.\n\n"
            "Critérios para aprovação (Responda APENAS 'yes'):\n"
            "- O contexto aborda diretamente o núcleo da pergunta.\n"
            "- Há profundidade suficiente para uma explicação passo a passo e educativa.\n"
            "- Nenhuma informação externa crítica é necessária para responder.\n\n"
            "Critérios para falha (Responda APENAS 'no'):\n"
            "- O contexto é tangencial, vago ou superficial.\n"
            "- Faltam peças-chave para uma resposta completa e correta.\n"
            "- O Agente precisaria adivinhar ou inventar informações (alucinar) para preencher lacunas.\n\n"
            "Retorne ESTRITAMENTE a palavra 'yes' ou 'no', em letras minúsculas, sem NENHUMA outra palavra, pontuação ou explicação."
        ),
        ("human", "Contexto Recuperado:\n{context}\n\nPergunta do Usuário: {query}")
    ])

    chain = prompt | structured_llm

    response = chain.invoke({
        "context": formatted_context,
        "query": query
    })

    return {"is_relevant": response.is_relevant} 

def web_search(state: GraphState):
    """Perform web search using Tavily Search API."""

    tavily = TavilySearch(topic="general", max_results=3)

    query = state["messages"][-1].content

    results = tavily.invoke({"query": query})

    return {"context": results}

def create_response(state: GraphState):
    """Create the educational answer based on combined context."""

    query = state["messages"][-1].content
    context = state["context"]

    formatted_context = "\n\n".join(
        f"Fonte {i+1}:\n{doc.page_content}" 
        for i, doc in enumerate(context)
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system", 
            "Você é um tutor técnico altamente capacitado e didático. "
            "Sua missão é responder à pergunta do usuário de forma educativa, clara e estruturada, "
            "utilizando APENAS as informações fornecidas no Contexto abaixo. "
            "Siga estas regras:\n"
            "- Explique os conceitos passo a passo.\n"
            "- Use formatação (negrito, listas) para facilitar a leitura.\n"
            "- Se as informações no Contexto não forem suficientes para responder, admita que não sabe "
            "e não invente informações.\n\n"
            "Contexto recuperado:\n{context}"
        ),
        ("human", "{query}")
    ])

    chain = prompt | llm_generator

    response = chain.invoke({
        "context": formatted_context,
        "query": query
    })

    return {"messages": [response]}

def route_after_relevance(state: GraphState) -> Literal["create_response", "web_search"]:
    """Decide the next node based on relevant evaluation"""
    if state["is_relevant"]:
        return "create_response"
    else:
        return ["web_search"]

import operator
from typing import Annotated, Literal, List
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langgraph.graph import MessagesState
from pydantic import BaseModel, Field
from vector_store import vector_store
from dotenv import load_dotenv
from prompts import contextualize_q_system_prompt, evaluator_system_prompt, answer_system_prompt

load_dotenv("./.env")

class Intent(BaseModel):
    intent: Literal["casual", "information_seeking"] = Field(
        description="Classification of user intent. 'casual' for greetings, small talk, identity questions; 'information_seeking' for factual or knowledge-based queries."
    )

class GraphState(MessagesState):
    context: Annotated[List[Document], operator.add]
    query: str
    is_relevant: bool
    intent: str

class RelevanceDecision(BaseModel):
    is_relevant: bool = Field(
        description="Return True if the context is sufficient, correct, and relevant to answer the question. Otherwise, return False."
    )

llm_intent = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    temperature=1.0
)

llm_intent_structured = llm_intent.with_structured_output(Intent)

llm_generator = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    temperature=1.0
)

llm_evaluator = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    temperature=0.0
)

llm_evaluator_structured = llm_evaluator.with_structured_output(RelevanceDecision)

def classify_intent(state: GraphState) -> dict:
    """Classifies the user's intent: casual or information-seeking."""

    last_msg = state["messages"][-1]
    raw = last_msg.content

    if isinstance(raw, list):
        text_parts = [item["text"] for item in raw if isinstance(item, dict) and "text" in item]
        user_text = " ".join(text_parts).strip()
    else:
        user_text = str(raw).strip()

    decision = llm_intent_structured.invoke([
        {"role": "system", "content": "Classify the user's intent in the following message."},
        {"role": "user", "content": user_text},
    ])

    return {"intent": decision.intent}

def route_by_intent(state: GraphState) -> Literal["extract_query", "casual_response"]:
    """Route based on newly classified intent."""

    intent = state.get("intent", "information_seeking")
    if intent == "casual":
        return "casual_response"
    return "extract_query"

def casual_response(state: GraphState) -> dict:
    "Answers casual questions in a friendly manner, without external context."
    
    last_msg = state["messages"][-1]
    raw = last_msg.content

    if isinstance(raw, list):
        text_parts = [item["text"] for item in raw if isinstance(item, dict) and "text" in item]
        user_text = " ".join(text_parts).strip()
    else:
        user_text = str(raw).strip()

    response = llm_generator.invoke([
        {"role": "system", "content": "Você é um assistente amigável. Responda de forma curta e simpática a mensagem do usuário."},
        {"role": "user", "content": user_text},
    ])

    return {"messages": [response]}

def extract_query(state: GraphState):
    """Extracts and contextualizes the user's query based on their history."""
    messages = state["messages"]
    last_msg = messages[-1]
    raw_content = last_msg.content

    if isinstance(raw_content, list):
        parts = []
        for item in raw_content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
        query_string = " ".join(parts).strip()
    else:
        query_string = str(raw_content).strip()

    if len(messages) <= 1:
        return {"query": query_string}

    sys_msg = SystemMessage(content=contextualize_q_system_prompt)
    result = llm_evaluator.invoke([sys_msg] + list(messages))
    contextualized_query = result.content

    if isinstance(contextualized_query, list):
        parts = []
        for item in contextualized_query:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
        contextualized_query = " ".join(parts).strip()

    return {"query": contextualized_query}

def retrieve_context(state: GraphState):
    """Retrieve top documents from ChromaDB Collection bases on query."""

    query = state["query"]

    if not isinstance(query, str) or not query:
        return {"context": []}

    docs = vector_store.similarity_search(query, k=3)

    return {"context": docs}

def relevance_context(state: GraphState):
    """Determine whether the retrieved context is relevant and sufficient."""

    query = state["query"]
    context_docs = state["context"]

    if not context_docs:
        return {"is_relevant": False}

    formatted = "\n\n".join(
        f"Fonte {i+1}:\n{d.page_content}" for i, d in enumerate(context_docs)
    )

    prompt = evaluator_system_prompt.format(context=formatted)
    response = llm_evaluator_structured.invoke([
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"User Query: {query}\n\nAssess the context and return your decision."},
    ])

    return {"is_relevant": response.is_relevant}

def route_after_relevance(state: GraphState) -> Literal["create_response", "web_search"]:
    """Decide the next node based on relevant evaluation"""
    if state["is_relevant"]:
        return "create_response"
    else:
        return "web_search"

def web_search(state: GraphState):
    """Perform web search using Tavily Search API and format as Documents."""
    query = state["query"]

    if isinstance(query, list):
        parts = []
        for item in query:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
        query = " ".join(parts).strip()
    query = str(query)

    tavily = TavilySearch(topic="general", max_results=3)
    raw_result = tavily.invoke({"query": query})

    if isinstance(raw_result, dict):
        results = raw_result.get("results", [])
    elif isinstance(raw_result, list):
        results = raw_result
    else:
        results = []

    new_docs = []
    for item in results:
        content = item.get("content") or item.get("text") or ""
        url = item.get("url", "")
        if content:
            new_docs.append(Document(page_content=content, metadata={"source": url}))

    return {"context": new_docs}

def create_response(state: GraphState):
    """Create the educational answer based on combined context."""

    query = state["query"]

    if isinstance(query, list):
        parts = []
        for item in query:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
        query = " ".join(parts).strip()
    query = str(query)

    docs = state.get("context", [])
    if not docs:
        formatted_context = "Nenhum documento foi encontrado."
    else:
        formatted_context = "\n\n".join(
            f"Fonte {i+1}:\n{d.page_content}" for i, d in enumerate(docs)
        )

    sys_prompt = answer_system_prompt.format(context=formatted_context)
    response = llm_generator.invoke([
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": query},
    ])

    return {"messages": [response]}

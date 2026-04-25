import pandas as pd
import numpy as np
import json
import re
from typing import List, Dict, Any, Tuple, Literal, TypedDict
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import time
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import seaborn as sns
from dotenv import load_dotenv
import openai
import os
import chromadb
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, MessagesState, START, END
from groq import Groq
load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

if not groq_api_key:
    raise ValueError("API key do Groq não encontrada no .env")

client_chromadb = chromadb.PersistentClient(path="./chromadb")

def get_llm_response(prompt: str) -> str:

    client = Groq(api_key=groq_api_key)
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content

def retrieve_context_qa(state):
    """ Retrieve top documents from ChromaDB Collection 1 based on query"""

    collection = client_chromadb.get_collection(name='medical_qa')

    print("---RETRIEVING CONTENT---")
    
    query = state["query"]
    results = collection.query(query_texts=[query], n_results=3)
    context = "\n".join(results["documents"][0])
    state['context'] = context
    state['source'] = "Medical QA Collection"

    print(context)

    return state

def retrieve_context_devices(state):
    """ Retrieve top documents from ChromaDB Collection 2 based on query"""

    collection = client_chromadb.get_collection(name='medical_devices')

    print("---RETRIEVING CONTENT---")
    
    query = state["query"]
    results = collection.query(query_texts=[query], n_results=3)
    context = "\n".join(results["documents"][0])
    state['context'] = context
    state['source'] = "Medical Manual Devices"

    print(context)

    return state

def websearch(state):
    """Perform web search using  Tavily Search API"""
    print("---Performing Tavily web search---")

    tavily_search = TavilySearch(topic="general", max_results=3)

    query = state['query']

    result = tavily_search.invoke({"query": query})
    state['context'] = result['results'][0]['content']

    return state

def check_relevance(state: GraphState):
    """Determine wheter the retrieved context is relevant or not."""
    print("---CONTEXT RELEVANCE CHECKER")

    query = state["query"]
    context = state["context"]

    relevance_prompt = f"""
        Check the context below to see if the contect is relevant to the user query or not.
        ####
        Context:
        {context}
        ####
        User Query: {query}

        Options: 
        - Yes: if the context is relevant.
        - No: if the context is not relevant.

        Please answer with only 'Yes' or 'No'
    """
    relevance_decision_value = get_llm_response(relevance_prompt).strip()
    print(f"---RELEVANCE DECISION: {relevance_decision_value} ---")
    state["is_relevant"] = relevance_decision_value
    return state

def relevance_decision(state: GraphState) -> str:
    iteration_count = state.get("iteration_count", 0)
    iteration_count += 1

    state['iteration_count'] = iteration_count

    if iteration_count >= 3:
        print("---MAX ITERATIONS REACHED, FORCING 'Yes'---")
        state['is_relevant'] = "Yes"
    return state["is_relevant"]

# THE ROUTER
def router(state: GraphState) -> Literal[
    "Retrive_QA", "Retrieve_Device", "Web_Search"
]:
    """ Agentic router: decides which retriebal method to use. """
    query = state["query"]
    
    decision_prompt = f"""
    You are a routing agent. Based on the user query, decide where to look for information.

    Options:
    - Retrieve_QA: if it's about general medical knowledge, symptoms or treatment.
    - Retrieve_Device: if it's about medical devices, manuals or instructions.
    - Web_Search: if it's about recent news, brand names or external data.

    Query: "{query}"

    Respond ONLY with one of: Retrieve_QA, Retrieve_Device, Web_Search
    """

    router_decision = get_llm_response(decision_prompt).strip()
    print(f"---ROUTER DECISION: {router_decision}---")

    print(router_decision)

    state["source"] = router_decision
    return state

def route_decision(state: GraphState) -> str:
    return state["source"]

def build_prompt(state: GraphState):
    """
    Constructs the structured prompt using the GraphState keys.
    """
    print("--- NODE: AUGMENT ---")
    
    # Using your specific GraphState keys
    user_query = state["query"]
    retrieved_content = state["context"]

    # Structured Prompt following your project's English pattern
    full_prompt = f"""
    You are a technical medical assistant. Use the following pieces of context to answer the user's question. 
    If you don't know the answer, just say that you don't know, don't try to make up an answer.

    Context:
    {retrieved_content}

    Question: "{user_query}"

    Answer:
    """

    state['prompt'] = full_prompt
    # Updating the 'prompt' key in your GraphState
    return state

def generate_node(state: GraphState):
    print("--- NODE: GENERATE ---")
    
    # 1. Extrai a string do estado
    prompt_para_llm = state["prompt"]
    
    # 2. Chama sua função original que só aceita string
    resposta_final = get_llm_response(prompt_para_llm)
    
    # 3. Devolve o dicionário para atualizar o GraphState
    return {"response": resposta_final}

# BUILDING THE GRAPH
class GraphState(TypedDict):
    query: str
    context: str
    prompt: str
    response: str
    source: str
    is_relevant: str
    iteration_count: str

workflow = StateGraph(GraphState)

# NODES
workflow.add_node("Router", router)
workflow.add_node("Retrieve_QA", retrieve_context_qa)
workflow.add_node("Retrieve_Device", retrieve_context_devices)
workflow.add_node("Web_Search", websearch)
workflow.add_node("Relevance_Checker", check_relevance)
workflow.add_node("Augment", build_prompt)
workflow.add_node("Generate", generate_node)

# EDGES
workflow.add_edge(START, "Router")
workflow.add_conditional_edges(
    "Router",
    route_decision,
    {
        "Retrieve_QA": "Retrieve_QA",
        "Retrieve_Device": "Retrieve_Device",
        "Web_Search": "Web_Search"
    }
)

workflow.add_edge("Retrieve_QA", "Relevance_Checker")
workflow.add_edge("Retrieve_Device", "Relevance_Checker")
workflow.add_edge("Web_Search", "Relevance_Checker")

workflow.add_conditional_edges(
    "Relevance_Checker",
    relevance_decision,
    {
        "Yes": "Augment",
        "No": "Web_Search"
    }
)
workflow.add_edge("Augment", "Generate")
workflow.add_edge("Generate", END)

agentic_rag = workflow.compile()

input_state = {"query" : "What is the treatment for Alzheimer"}

from pprint import pprint
for step in agentic_rag.stream(input=input_state):
    for key, value in step.items():
        pprint(f"Finished running {key}: ")
pprint(value["response"])

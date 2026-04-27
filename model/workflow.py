from dotenv import load_dotenv

load_dotenv("./.env")

from langgraph.graph import StateGraph, START, END
from nodes import GraphState, create_response, relevance_context, retrieve_context, route_after_relevance, web_search

workflow = StateGraph(GraphState)

workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("relevance_context", relevance_context)
workflow.add_node("web_search", web_search)
workflow.add_node("create_response", create_response)

workflow.add_edge(START, "retrieve_context") 
workflow.add_edge("retrieve_context", "relevance_context") 
workflow.add_conditional_edges(
    "relevance_context",
    route_after_relevance
)
workflow.add_edge("web_search", "create_response")
workflow.add_edge("create_response", END)

app = workflow.compile()

image_bytes = app.get_graph().draw_mermaid_png()
with open("workflow.png", "wb") as f:
    f.write(image_bytes)
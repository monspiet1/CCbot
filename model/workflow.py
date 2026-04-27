from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from nodes import GraphState, casual_response, classify_intent, create_response, extract_query, relevance_context, retrieve_context, route_after_relevance, route_by_intent, web_search

load_dotenv("./.env")

workflow = StateGraph(GraphState)

workflow.add_node("classify_intent", classify_intent)
workflow.add_node("casual_response", casual_response)
workflow.add_node("extract_query", extract_query)
workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("relevance_context", relevance_context)
workflow.add_node("web_search", web_search)
workflow.add_node("create_response", create_response)

workflow.add_edge(START, "classify_intent")
workflow.add_conditional_edges(
    "classify_intent",
    route_by_intent,
    {"extract_query": "extract_query", "casual_response": "casual_response"}
)
workflow.add_edge("casual_response", END)

workflow.add_edge("extract_query", "retrieve_context") 
workflow.add_edge("retrieve_context", "relevance_context")

workflow.add_conditional_edges(
    "relevance_context",
    route_after_relevance,
    {
        "create_response": "create_response",
        "web_search": "web_search"
    }
)

workflow.add_edge("web_search", "create_response")
workflow.add_edge("create_response", END)

app = workflow.compile()

image_bytes = app.get_graph().draw_mermaid_png()
with open("workflow.png", "wb") as f:
    f.write(image_bytes)
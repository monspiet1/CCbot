from langgraph.graph import StateGraph, START, END
from nodes import (
    GraphState,
    retrieve_context_qa,
    retrieve_context_devices,
    relevance_decision,
    router,websearch,
    check_relevance,
    build_prompt,
    generate_node,
    route_decision
)

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



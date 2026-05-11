from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from nodes import (
    GraphState,
    abstraction_eval,
    abstraction_node,
    algorithm_eval,
    algorithm_node,
    casual_node,
    decomposition_eval,
    decomposition_node,
    general_qa_node,
    intent_router,
    pattern_eval,
    pattern_node,
    route_abstraction,
    route_algorithm,
    route_decomposition,
    route_pattern,
)

workflow = StateGraph(GraphState)

workflow.add_node("casual_node", casual_node)
workflow.add_node("general_qa_node", general_qa_node)
workflow.add_node("decomposition_node", decomposition_node)
workflow.add_node("decomposition_eval", decomposition_eval)
workflow.add_node("pattern_node", pattern_node)
workflow.add_node("pattern_eval", pattern_eval)
workflow.add_node("abstraction_node", abstraction_node)
workflow.add_node("abstraction_eval", abstraction_eval)
workflow.add_node("algorithm_node", algorithm_node)
workflow.add_node("algorithm_eval", algorithm_eval)

workflow.add_conditional_edges(
    START,
    intent_router,
    {
        "casual_node": "casual_node",
        "general_qa_node": "general_qa_node",
        "decomposition_node": "decomposition_node",
        "pattern_node": "pattern_node",
        "abstraction_node": "abstraction_node",
        "algorithm_node": "algorithm_node",
    },
)

workflow.add_edge("casual_node", END)
workflow.add_edge("general_qa_node", END)

workflow.add_edge("decomposition_node", "decomposition_eval")
workflow.add_conditional_edges(
    "decomposition_eval",
    route_decomposition,
    {"pattern_node": "pattern_node", "decomposition_node": "decomposition_node"},
)

workflow.add_edge("pattern_node", "pattern_eval")
workflow.add_conditional_edges(
    "pattern_eval",
    route_pattern,
    {"abstraction_node": "abstraction_node", "pattern_node": "pattern_node"},
)

workflow.add_edge("abstraction_node", "abstraction_eval")
workflow.add_conditional_edges(
    "abstraction_eval",
    route_abstraction,
    {"algorithm_node": "algorithm_node", "abstraction_node": "abstraction_node"},
)

workflow.add_edge("algorithm_node", "algorithm_eval")
workflow.add_conditional_edges(
    "algorithm_eval", route_algorithm, {END: END, "algorithm_node": "algorithm_node"}
)

app = workflow.compile()

image_bytes = app.get_graph().draw_mermaid_png()
with open("workflow.png", "wb") as f:
    f.write(image_bytes)

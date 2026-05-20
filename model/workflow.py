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

# Auxiliary Nodes
workflow.add_node("casual_node", casual_node)
workflow.add_node("general_qa_node", general_qa_node)

# Tutor Nodes (The Socratic questioners)
workflow.add_node("decomposition_node", decomposition_node)
workflow.add_node("pattern_node", pattern_node)
workflow.add_node("abstraction_node", abstraction_node)
workflow.add_node("algorithm_node", algorithm_node)

# Evaluator Nodes (The LLM-as-a-judge extractors)
workflow.add_node("decomposition_eval", decomposition_eval)
workflow.add_node("pattern_eval", pattern_eval)
workflow.add_node("abstraction_eval", abstraction_eval)
workflow.add_node("algorithm_eval", algorithm_eval)

workflow.add_conditional_edges(
    START,
    intent_router,
    {
        "casual_node": "casual_node",
        "general_qa_node": "general_qa_node",
        # Paths to START a new stage (Tutors)
        "decomposition_node": "decomposition_node",
        "pattern_node": "pattern_node",
        "abstraction_node": "abstraction_node",
        "algorithm_node": "algorithm_node",
        # Paths to EVALUATE a user's answer (Judges)
        "decomposition_eval": "decomposition_eval",
        "pattern_eval": "pattern_eval",
        "abstraction_eval": "abstraction_eval",
        "algorithm_eval": "algorithm_eval",
    },
)

# After a Judge evaluates, it uses the route_* function to decide the next step
workflow.add_conditional_edges("decomposition_eval", route_decomposition)
workflow.add_conditional_edges("pattern_eval", route_pattern)
workflow.add_conditional_edges("abstraction_eval", route_abstraction)
workflow.add_conditional_edges("algorithm_eval", route_algorithm)

# CRITICAL: Every node that talks to the user MUST end the graph execution.
# This prevents the system from running multiple nodes before the user replies.
workflow.add_edge("casual_node", END)
workflow.add_edge("general_qa_node", END)

workflow.add_edge("decomposition_node", END)
workflow.add_edge("pattern_node", END)
workflow.add_edge("abstraction_node", END)
workflow.add_edge("algorithm_node", END)

app = workflow.compile()

image_bytes = app.get_graph().draw_mermaid_png()
with open("workflow.png", "wb") as f:
    f.write(image_bytes)

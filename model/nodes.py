from typing import Annotated, List, Literal, TypedDict, cast

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

load_dotenv("./.env")


class Intent(BaseModel):
    # 'casual' = greetings, 'general_qa' = specific questions, 'tutoring' = the exercise flow
    intent: Literal["casual", "general_qa", "tutoring"] = Field(
        description="Classify intent: 'casual' for greetings; 'general_qa' for generic programming questions; 'tutoring' for the pillar exercise."
    )


class EvaluationResult(BaseModel):
    approved: bool = Field(
        description="True if the student met the criteria for the current pillar."
    )
    next_action: Literal["advance", "reinforce", "didactic_example"] = Field(
        description="Action based on student performance."
    )
    missing_requirements: List[str] = Field(
        description="Specific items from the checklist not yet satisfied."
    )
    knowledge_score: float = Field(
        description="0-10 score of the student's current understanding."
    )
    internal_feedback: str = Field(
        description="Technical hint for the tutor node to guide the student."
    )


class GraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    current_stage: str  # decomposition, pattern, abstraction, algorithm, completed
    summary: str
    evaluation_feedback: str
    # Specific fields to store the 'mental model' or 'subtasks' defined by the student
    student_artifacts: dict


llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
llm_structured_eval = llm.with_structured_output(EvaluationResult)
llm_structured_intent = llm.with_structured_output(Intent)


def intent_router(state: GraphState):
    """
    Decides the path based on user message.
    Corresponds to the 'router' in your diagrams.
    """
    last_msg = state["messages"][-1].content
    decision = llm_structured_intent.invoke(
        [
            {"role": "system", "content": "Classify the user intent strictly."},
            {"role": "user", "content": last_msg},
        ]
    )

    decision = cast(Intent, decision)

    if decision.intent == "casual":
        return "casual_node"
    elif decision.intent == "general_qa":
        return "general_qa_node"
    else:
        # If tutoring, route to the current active pillar tutor
        return state.get("current_stage", "decomposition_node")


def casual_node(state: GraphState):
    """Greetings and small talk."""
    response = llm.invoke(
        [
            {
                "role": "system",
                "content": "Respond friendly to the student's greeting.",
            },
            {"role": "user", "content": state["messages"][-1].content},
        ]
    )
    return {"messages": [response]}


def general_qa_node(state: GraphState):
    """
    Corresponds to 'qa_node' or 'Resposta generica'.
    Handles generic programming/logic questions.
    """
    sys_prompt = """You are an expert Programming Tutor. Answer the user's specific question clearly and concisely.
    After answering, remind them that they can continue their exercise in Computational Thinking."""

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])
    return {"messages": [response]}


def decomposition_node(state: GraphState):
    """Pillar 1: Breaking down complex problems into manageable parts[cite: 119]."""
    sys_prompt = """You are a Decomposition Assistant. Your goal is to guide the user in fragmenting problems.
    RULES: 1. Request a single-sentence problem definition. 2. Induce listing subtasks. 3. Test independence.
    4. Define Inputs/Outputs. 5. Monitor complexity.
    POSTURE: Socratic, Brief, Analytical."""

    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\nEvaluator Instruction: {state['evaluation_feedback']}"

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])
    return {"messages": [response], "current_stage": "decomposition"}


def pattern_node(state: GraphState):
    """Pillar 2: Identifying similarities and regularities[cite: 132]."""
    sys_prompt = """You are a Pattern Recognition Assistant. Help the user see similarities across subtasks.
    RULES: 1. Connect to previous subtasks. 2. Search for common characteristics. 3. Focus on effort economy.
    4. Generalize experience to daily life. 5. Encourage predictability.
    POSTURE: Socratic, Brief, Focus on Reuse."""

    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\nEvaluator Instruction: {state['evaluation_feedback']}"

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])
    return {"messages": [response], "current_stage": "pattern"}


def abstraction_node(state: GraphState):
    """Pillar 3: Filtering information to focus on the essential[cite: 140]."""
    sys_prompt = """You are an Abstraction Assistant. Help the user filter essential info from irrelevant noise.
    RULES: 1. Apply relevance filter. 2. Create mental models (skeletons). 3. Remove noise (names, colors, details).
    4. Focus on critical variables. 5. Generalize concepts.
    POSTURE: Socratic, Minimalist, Analytical."""

    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\nEvaluator Instruction: {state['evaluation_feedback']}"

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])
    return {"messages": [response], "current_stage": "abstraction"}


def algorithm_node(state: GraphState):
    """Pillar 4: Creating ordered steps to solve the problem[cite: 149]."""
    sys_prompt = """You are an Algorithm Assistant. Guide the user in building a logical step-by-step process.
    RULES: 1. Logical sequencing. 2. Precision and clarity (Robot-like instructions).
    3. Conditionals and repetitions. 4. Execution test. 5. Clear finiteness.
    POSTURE: Socratic, Rigorous, Practical."""

    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\nEvaluator Instruction: {state['evaluation_feedback']}"

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])
    return {"messages": [response], "current_stage": "algorithm"}


def generic_evaluator(state: GraphState, stage_name: str):
    """A generic evaluation logic that uses the LLM-as-a-judge for each stage."""
    eval_prompt = f"""Evaluate the conversation between Mentor and Student for the {stage_name} stage.
    Check for: Goal synthesis, granularity (min 3 tasks), independence, and I/O interfaces.
    Return JSON with 'approved', 'next_action', and 'internal_feedback'."""

    decision = llm_structured_eval.invoke(
        [SystemMessage(content=eval_prompt)] + state["messages"]
    )

    decision = cast(EvaluationResult, decision)

    return decision


def decomposition_eval(state: GraphState):
    res = generic_evaluator(state, "Decomposition")
    return {"evaluation_feedback": res.internal_feedback, "approved": res.approved}


def pattern_eval(state: GraphState):
    res = generic_evaluator(state, "Pattern Recognition")
    return {"evaluation_feedback": res.internal_feedback, "approved": res.approved}


def abstraction_eval(state: GraphState):
    res = generic_evaluator(state, "Abstraction")
    return {"evaluation_feedback": res.internal_feedback, "approved": res.approved}


def algorithm_eval(state: GraphState):
    res = generic_evaluator(state, "Algorithm")
    return {"evaluation_feedback": res.internal_feedback, "approved": res.approved}


def route_decomposition(state: GraphState):
    return "pattern_node" if state.get("approved") else "decomposition_node"


def route_pattern(state: GraphState):
    return "abstraction_node" if state.get("approved") else "pattern_node"


def route_abstraction(state: GraphState):
    return "algorithm_node" if state.get("approved") else "abstraction_node"


def route_algorithm(state: GraphState):
    return END if state.get("approved") else "algorithm_node"

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
        description="Classify intent: 'casual' for greetings; 'general_qa' for explicit out-of-context technical questions; 'tutoring' for answering the tutor or starting an exercise."
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
    is_tutoring_active: bool


llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0.2)
llm_structured_eval = llm.with_structured_output(EvaluationResult)
llm_structured_intent = llm.with_structured_output(Intent)


def intent_router(state: GraphState):
    """Decides the path based on user message intent AND conversation context."""
    messages = state["messages"]
    last_user_msg = messages[-1].content

    last_ai_msg = "Nenhuma"

    for m in reversed(messages[:-1]):
        if m.type == "ai":
            last_ai_msg = m.content
            break

    is_active = state.get("is_tutoring_active", False)
    current_stage = state.get("current_stage", "decomposition_node")

    sys_prompt = f"""Você é um roteador de intenções de um Tutor de IA.
        CONTEXTO ATUAL:
        - Exercício de tutoria ativo? {is_active}
        - Fase atual do exercício: {current_stage}
        - Última fala da IA: "{last_ai_msg}"

        REGRAS DE CLASSIFICAÇÃO:
        Se 'Exercício ativo' for True, é altamente provável que o usuário esteja tentando responder a 'Última fala da IA' para continuar o exercício (intent = 'tutoring').
        SÓ classifique como 'general_qa' se o usuário ignorar completamente a pergunta da IA para fazer uma NOVA pergunta técnica direta (ex: "O que é um array?").
        Se ele estiver pedindo para começar o exercício, também é 'tutoring'.
        """

    decision = llm_structured_intent.invoke(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": last_user_msg},
        ]
    )

    decision = cast(Intent, decision)

    if decision.intent == "casual":
        return "casual_node"
    elif decision.intent == "general_qa":
        return "general_qa_node"
    else:
        # If tutoring, route to the current active pillar tutor
        return current_stage


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
    """Handles generic questions and offers to resume or restart."""

    is_active = state.get("is_tutoring_active", False)

    sys_prompt = """You are an expert Programming Tutor. Answer the user's specific question clearly and concisely."""

    if is_active:
        sys_prompt += "\n\nAo final da sua resposta, diga exatamente: 'Notei que você tem um exercício de Pensamento Computacional em andamento. Você gostaria de **retomar o exercício anterior** de onde paramos, ou quer **usar essa sua nova dúvida para iniciar um novo fluxo** do zero?'"
    else:
        sys_prompt += "\n\nAo final da resposta, lembre-o que ele pode iniciar um exercício de Pensamento Computacional sobre esse ou outro tema a qualquer momento."

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
    return {
        "messages": [response],
        "current_stage": "decomposition_node",
        "is_tutoring_active": True,
    }


def pattern_node(state: GraphState):
    """Pillar 2: Identifying similarities and regularities[cite: 132]."""
    sys_prompt = """You are a Pattern Recognition Assistant. Help the user see similarities across subtasks.
    RULES: 1. Connect to previous subtasks. 2. Search for common characteristics. 3. Focus on effort economy.
    4. Generalize experience to daily life. 5. Encourage predictability.
    POSTURE: Socratic, Brief, Focus on Reuse."""

    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\nEvaluator Instruction: {state['evaluation_feedback']}"

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])
    return {
        "messages": [response],
        "current_stage": "pattern_node",
        "is_tutoring_active": True,
    }


def abstraction_node(state: GraphState):
    """Pillar 3: Filtering information to focus on the essential[cite: 140]."""
    sys_prompt = """You are an Abstraction Assistant. Help the user filter essential info from irrelevant noise.
    RULES: 1. Apply relevance filter. 2. Create mental models (skeletons). 3. Remove noise (names, colors, details).
    4. Focus on critical variables. 5. Generalize concepts.
    POSTURE: Socratic, Minimalist, Analytical."""

    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\nEvaluator Instruction: {state['evaluation_feedback']}"

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])
    return {
        "messages": [response],
        "current_stage": "abstraction_node",
        "is_tutoring_active": True,
    }


def algorithm_node(state: GraphState):
    """Pillar 4: Creating ordered steps to solve the problem[cite: 149]."""
    sys_prompt = """You are an Algorithm Assistant. Guide the user in building a logical step-by-step process.
    RULES: 1. Logical sequencing. 2. Precision and clarity (Robot-like instructions).
    3. Conditionals and repetitions. 4. Execution test. 5. Clear finiteness.
    POSTURE: Socratic, Rigorous, Practical."""

    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\nEvaluator Instruction: {state['evaluation_feedback']}"

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])
    return {
        "messages": [response],
        "current_stage": "algorithm_node",
        "is_tutoring_active": True,
    }


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

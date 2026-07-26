from typing import Annotated, Any, Literal, TypedDict, cast, Dict, List

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END
from langgraph.graph.message import add_messages
from llm_factory import get_llm, get_structured_llm
from message_utils import get_last_ai_message, get_last_human_message
from prompts import (
    ABSTRACTION_NODE_PROMPT,
    ALGORITHM_NODE_PROMPT,
    CASUAL_NODE_PROMPT,
    DECOMPOSITION_NODE_PROMPT,
    EVALUATOR_PROMPT,
    GENERAL_QA_CONTINUATION_ACTIVE,
    GENERAL_QA_CONTINUATION_INACTIVE,
    GENERAL_QA_NODE_PROMPT,
    INTENT_ROUTER_PROMPT,
    PATTERN_NODE_PROMPT,
)
from pydantic import BaseModel, Field


class Intent(BaseModel):
    intent: Literal["casual", "general_qa", "tutoring"] = Field(
        description="Classify intent: 'casual' for greetings; 'general_qa' for explicit out-of-context technical questions; 'tutoring' for answering the tutor or starting an exercise."
    )


class EvaluationResult(BaseModel):
    reasoning: str = Field(
        description="Step-by-step reasoning analyzing if the LAST human message satisfies the CURRENT stage's rubric. Explain your decision before giving the verdict."
    )
    missing_requirements: List[str] = Field(
        description="If not approved, list the specific items from the rubric that the user missed or got wrong. If approved, return an empty list."
    )
    approved: bool = Field(
        description="True ONLY IF the current message fully satisfies the rubric requirements."
    )
    internal_feedback: str = Field(
        description="Technical hint for the tutor to guide the student if they failed. If approved, simply write 'Approved'."
    )
    extracted_artifacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="If approved, extract the user's consolidated answer into a JSON format using EXACTLY the keys requested in the extraction instructions. If not approved, return an empty object.",
    )


class GraphState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    current_stage: str
    is_tutoring_active: bool
    approved: bool
    evaluation_feedback: str
    student_artifacts: dict[str, Any]


llm = get_llm()
llm_structured_eval = get_structured_llm(EvaluationResult)
llm_structured_intent = get_structured_llm(Intent)


def intent_router(state: GraphState):
    """Decides the path based on user message intent AND conversation context."""
    messages = state["messages"]
    last_user_msg = messages[-1].content

    last_ai_msg = get_last_ai_message(messages[:-1]) or "None"

    is_active = state.get("is_tutoring_active", False)
    current_stage = state.get("current_stage", "decomposition")

    sys_prompt = INTENT_ROUTER_PROMPT.format(
        is_active=is_active,
        current_stage=current_stage,
        last_ai_msg=last_ai_msg,
    )

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
    elif decision.intent == "tutoring":
        if is_active:
            return f"{current_stage}_eval"
        else:
            return f"{current_stage}_node"


def casual_node(state: GraphState):
    """Greetings and small talk."""
    response = llm.invoke(
        [
            {"role": "system", "content": CASUAL_NODE_PROMPT},
            {"role": "user", "content": state["messages"][-1].content},
        ]
    )
    return {"messages": [response]}


def general_qa_node(state: GraphState):
    """Handles generic conceptual questions without giving away logic, offering to resume or restart."""

    is_active = state.get("is_tutoring_active", False)

    artifacts = state.get("student_artifacts", {})
    current_goal = artifacts.get("decomposition", {}).get(
        "goal", "your ongoing exercise"
    )
    current_stage = state.get("current_stage", "decomposition")

    sys_prompt = GENERAL_QA_NODE_PROMPT

    if is_active:
        sys_prompt += GENERAL_QA_CONTINUATION_ACTIVE.format(
            current_stage=current_stage, current_goal=current_goal
        )
    else:
        sys_prompt += GENERAL_QA_CONTINUATION_INACTIVE

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])

    return {"messages": [response]}


def decomposition_node(state: GraphState):
    """Pillar 1: Breaking down complex problems into manageable parts."""

    sys_prompt = DECOMPOSITION_NODE_PROMPT

    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\n### EVALUATOR FEEDBACK (INTERNAL USE ONLY):\n{state['evaluation_feedback']}\nAdjust your next question to specifically address this feedback and guide the user to fix the missing requirements."

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])

    return {
        "messages": [response],
        "current_stage": "decomposition",
        "is_tutoring_active": True,
        "approved": False,
        "evaluation_feedback": "",
    }


def pattern_node(state: GraphState):
    """Pillar 2: Identifying similarities and regularities."""
    artifacts = state.get("student_artifacts", {})
    decomp_data = artifacts.get("decomposition", {})

    sys_prompt = PATTERN_NODE_PROMPT.format(
        goal=decomp_data.get("goal", "Not explicitly defined"),
        subtasks=decomp_data.get("subtasks", []),
    )

    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\n### EVALUATOR FEEDBACK (INTERNAL USE ONLY):\n{state['evaluation_feedback']}\nAdjust your next question to address this feedback."

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])

    return {
        "messages": [response],
        "current_stage": "pattern",
        "is_tutoring_active": True,
        "approved": False,
        "evaluation_feedback": "",
    }


def abstraction_node(state: GraphState):
    """Pillar 3: Filtering information to focus on the essential."""
    artifacts = state.get("student_artifacts", {})
    decomp_data = artifacts.get("decomposition", {})
    pattern_data = artifacts.get("pattern", {})

    sys_prompt = ABSTRACTION_NODE_PROMPT.format(
        subtasks=decomp_data.get("subtasks", []),
        general_rule=pattern_data.get("general_rule", "No pattern identified"),
    )

    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\n### EVALUATOR FEEDBACK (INTERNAL USE ONLY):\n{state['evaluation_feedback']}\nAdjust your next question to address this feedback."

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])

    return {
        "messages": [response],
        "current_stage": "abstraction",
        "is_tutoring_active": True,
        "approved": False,
        "evaluation_feedback": "",
    }


def algorithm_node(state: GraphState):
    """Pillar 4: Creating ordered steps to solve the problem."""
    artifacts = state.get("student_artifacts", {})
    decomp_data = artifacts.get("decomposition", {})
    abstract_data = artifacts.get("abstraction", {})

    sys_prompt = ALGORITHM_NODE_PROMPT.format(
        goal=decomp_data.get("goal", "Not defined"),
        core_variables=abstract_data.get("core_variables", []),
        simplified_model=abstract_data.get("simplified_model", "Not defined"),
        ignored_noise=abstract_data.get("ignored_noise", []),
    )

    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\n### EVALUATOR FEEDBACK (INTERNAL USE ONLY):\n{state['evaluation_feedback']}\nAdjust your next question to address this feedback."

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])

    return {
        "messages": [response],
        "current_stage": "algorithm",
        "is_tutoring_active": True,
        "approved": False,
        "evaluation_feedback": "",
    }


def generic_evaluator(
    state: GraphState, specific_rubric: str, extraction_instructions: str
):
    """Executes the LLM-as-a-judge with a specific rubric and structured output, isolating the human's input."""
    messages = state["messages"]
    artifacts = state.get("student_artifacts", {})

    last_human_msg = get_last_human_message(messages)
    last_ai_msg = get_last_ai_message(messages)

    sys_prompt = EVALUATOR_PROMPT.format(
        artifacts=artifacts,
        last_ai_msg=last_ai_msg,
        last_human_msg=last_human_msg,
        specific_rubric=specific_rubric,
        extraction_instructions=extraction_instructions,
    )

    decision = llm_structured_eval.invoke(
        [
            SystemMessage(content=sys_prompt),
            HumanMessage(
                content="Please evaluate the student's last answer based on the provided context and rubric."
            ),
        ]
    )

    return cast(EvaluationResult, decision)


def decomposition_eval(state: GraphState):
    rubric = """
    - Single Goal: Did the student synthesize the problem into a clear, final sentence?
    - Granularity: Did the student list independent subtasks?
    - Interfaces (I/O): Did the student explicitly define what is needed to start (Input) and the expected result (Output) for each subtask?
    """

    extraction = """
    Extract the problem breakdown using EXACTLY these JSON keys:
    {
        "goal": "The final objective in a short sentence",
        "subtasks": ["task 1 (in: x, out: y)", "task 2 (in: w, out: z)"]
    }
    """

    res = generic_evaluator(state, rubric, extraction)

    if res.approved:
        artifacts = state.get("student_artifacts", {}).copy()
        artifacts["decomposition"] = res.extracted_artifacts

        return {
            "approved": True,
            "current_stage": "pattern",
            "student_artifacts": artifacts,
            "evaluation_feedback": "",
        }

    feedback = f"Missing requirements: {', '.join(res.missing_requirements)}. Hint: {res.internal_feedback}"
    return {"approved": False, "evaluation_feedback": feedback}


def pattern_eval(state: GraphState):
    rubric = """
    - Historical Connection: Did the student relate the current subtasks to past experiences or known problems?
    - Similarity Identification: Did the student explicitly point out common characteristics between the parts?
    - Generalization: Did the student formulate and describe the "general rule" or pattern behind the repetitions?
    If they only say "yes, they are similar" without explaining HOW, return approved: false.
    """

    extraction = """
    Extract the identified pattern using EXACTLY these JSON keys:
    {
        "identified_similarity": "The common traits the student found between the tasks",
        "general_rule": "The mental shortcut, rule, or analogy they decided to use"
    }
    """

    res = generic_evaluator(state, rubric, extraction)

    if res.approved:
        artifacts = state.get("student_artifacts", {}).copy()
        artifacts["pattern"] = res.extracted_artifacts

        return {
            "approved": True,
            "current_stage": "abstraction",
            "student_artifacts": artifacts,
            "evaluation_feedback": "",
        }

    feedback = f"Missing requirements: {', '.join(res.missing_requirements)}. Hint: {res.internal_feedback}"
    return {"approved": False, "evaluation_feedback": feedback}


def abstraction_eval(state: GraphState):
    rubric = """
    - Noise Identification: Did the student successfully separate irrelevant information (cosmetic details, specific names) from the core problem?
    - Critical Variables Definition: Did the student explicitly identify which fundamental data impacts the final result?
    - Simplified Modeling: Did the student describe the "skeleton" of the problem minimally?
    """

    extraction = """
    Extract the abstraction model using EXACTLY these JSON keys:
    {
        "ignored_noise": ["list of irrelevant details the student decided to discard"],
        "core_variables": ["list of essential data that actually matters for the logic"],
        "simplified_model": "A one-sentence minimalist description of the problem's skeleton"
    }
    """

    res = generic_evaluator(state, rubric, extraction)

    if res.approved:
        artifacts = state.get("student_artifacts", {}).copy()
        artifacts["abstraction"] = res.extracted_artifacts

        return {
            "approved": True,
            "current_stage": "algorithm",
            "student_artifacts": artifacts,
            "evaluation_feedback": "",
        }

    feedback = f"Missing requirements: {', '.join(res.missing_requirements)}. Hint: {res.internal_feedback}"
    return {"approved": False, "evaluation_feedback": feedback}


def algorithm_eval(state: GraphState):
    rubric = """
    - Sequencing: Are the instructions in a correct logical and chronological order?
    - Determinism (Clarity): Are the steps precise enough to be executed by a "robot" without ambiguity?
    - Flow Control: Did the student consider conditions (IF/THEN) or repetitions (LOOPS)?
    - Conclusion (Finiteness): Does the algorithm have a clear stopping point?
    """

    extraction = """
    Extract the final algorithm using EXACTLY these JSON keys:
    {
        "ordered_steps": ["Step 1...", "Step 2...", "Step 3..."],
        "conditions_or_loops": "Any IF/ELSE or repetition rules mentioned",
        "end_condition": "How the algorithm knows it is successfully finished"
    }
    """

    res = generic_evaluator(state, rubric, extraction)

    if res.approved:
        artifacts = state.get("student_artifacts", {}).copy()
        artifacts["algorithm"] = res.extracted_artifacts

        return {
            "approved": True,
            "is_tutoring_active": False,  # Ends the tutoring session!
            "student_artifacts": artifacts,
            "evaluation_feedback": "",
        }

    feedback = f"Missing requirements: {', '.join(res.missing_requirements)}. Hint: {res.internal_feedback}"
    return {"approved": False, "evaluation_feedback": feedback}


def route_decomposition(state: GraphState):
    """Routes based on the Decomposition evaluation result."""
    return "pattern_node" if state.get("approved") else "decomposition_node"


def route_pattern(state: GraphState):
    """Routes based on the Pattern evaluation result."""
    return "abstraction_node" if state.get("approved") else "pattern_node"


def route_abstraction(state: GraphState):
    """Routes based on the Abstraction evaluation result."""
    return "algorithm_node" if state.get("approved") else "abstraction_node"


def route_algorithm(state: GraphState):
    """Routes based on the final Algorithm evaluation result."""
    return END if state.get("approved") else "algorithm_node"

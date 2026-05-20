from typing import Annotated, Any, Dict, List, Literal, TypedDict, cast

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

load_dotenv("./.env")


class Intent(BaseModel):
    intent: Literal["casual", "general_qa", "tutoring"] = Field(
        description="Classify intent: 'casual' for greetings; 'general_qa' for explicit out-of-context technical questions; 'tutoring' for answering the tutor or starting an exercise."
    )


class EvaluationResult(BaseModel):
    # 1st Field: Forces Chain-of-Thought before the verdict
    reasoning: str = Field(
        description="Step-by-step reasoning analyzing if the LAST human message satisfies the CURRENT stage's rubric. Explain your decision before giving the verdict."
    )

    # 2nd Field: Exact errors for the Tutor to address
    missing_requirements: List[str] = Field(
        description="If not approved, list the specific items from the rubric that the user missed or got wrong. If approved, return an empty list."
    )

    # 3rd Field: The final verdict (Gatekeeper)
    approved: bool = Field(
        description="True ONLY IF the current message fully satisfies the rubric requirements."
    )

    # 4th Field: Hint for the next Tutor prompt
    internal_feedback: str = Field(
        description="Technical hint for the tutor to guide the student if they failed. If approved, simply write 'Approved'."
    )

    # 5th Field: The 'Blackboard' extraction
    extracted_artifacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="If approved, extract the user's consolidated answer into a JSON format using EXACTLY the keys requested in the extraction instructions. If not approved, return an empty object.",
    )


class GraphState(TypedDict):
    # Natural chat history (automatically appends new messages)
    messages: Annotated[list[AnyMessage], add_messages]

    # Routing Control
    current_stage: str  # e.g., "decomposition", "pattern", "abstraction", "algorithm"
    is_tutoring_active: bool  # Prevents forcing exercises in casual chats
    approved: bool  # Explicitly tracks if the user can advance to the next node

    # Judge -> Tutor Communication
    evaluation_feedback: (
        str  # Stores the failure reasons for the Tutor to formulate the next question
    )

    # The Blackboard (Clean Memory)
    student_artifacts: Dict[
        str, Any
    ]  # Stores the extracted_artifacts from each approved stage


llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0.2)
llm_structured_eval = llm.with_structured_output(EvaluationResult)
llm_structured_intent = llm.with_structured_output(Intent)


def intent_router(state: GraphState):
    """Decides the path based on user message intent AND conversation context."""
    messages = state["messages"]
    last_user_msg = messages[-1].content

    # Retrieve the last AI message to provide context for the classification
    last_ai_msg = "None"
    for m in reversed(messages[:-1]):
        if m.type == "ai":
            last_ai_msg = m.content
            break

    is_active = state.get("is_tutoring_active", False)

    # We only store the base name now (e.g., "decomposition", not "decomposition_node")
    # The .replace() is a safety net for backwards compatibility during this transition
    current_stage = state.get("current_stage", "decomposition").replace("_node", "")

    # High-level English prompt for the Intent Router
    sys_prompt = f"""You are the Intent Router for a specialized AI Tutor based on the Computational Thinking methodology.
    Your goal is to accurately classify the user's input to maintain the flow of the educational exercise.

    CURRENT CONTEXT:
    - Tutoring Session Active: {is_active}
    - Current Pillar/Stage: {current_stage}
    - Last Tutor Question: "{last_ai_msg}"

    CLASSIFICATION CATEGORIES:
    1. 'casual': Greetings, small talk, or unrelated non-technical comments.

    2. 'tutoring':
       - The user expresses a desire to start a Computational Thinking exercise.
       - The user is answering the Tutor's Socratic question related to the current stage.
       - The user presents a specific problem to solve, build, or implement regarding PROGRAMMING LOGIC, DATA STRUCTURES, or ALGORITHMS (e.g., "How do I implement a queue to manage a hospital?", "Help me create a binary tree", "How do I sort this array?"). These practical challenges MUST be routed to tutoring so the user can be guided to think and solve them step-by-step.

    3. 'general_qa':
       - The user asks for a purely theoretical definition or syntax clarification (e.g., "What is an array?", "Define a Linked List", "What is Big O notation?").
       - Do NOT use this for implementation requests, real-world scenarios, or logic puzzles.

    ROUTING LOGIC (STRICT RULES):
    - If 'Tutoring Session Active' is True, assume the user is participating in the exercise (intent = 'tutoring') unless they explicitly pivot to a new purely conceptual question.
    - If the user asks HOW to build, solve, or implement a Data Structure, Algorithm, or Logic Puzzle, strictly classify it as 'tutoring'. This will automatically trigger the Computational Thinking methodology starting with Decomposition.
    - Contrast Rule: "What is X?" -> 'general_qa'. "How do I build/use X to solve Y?" -> 'tutoring'.
    - If the user provides a brief answer that fits the last Tutor question, it is strictly 'tutoring'.
    """

    decision = llm_structured_intent.invoke(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": last_user_msg},
        ]
    )

    decision = cast(Intent, decision)

    # NEW ROUTING LOGIC: The "Gatekeeper"
    if decision.intent == "casual":
        return "casual_node"

    elif decision.intent == "general_qa":
        return "general_qa_node"

    elif decision.intent == "tutoring":
        if is_active:
            # The user is ANSWERING the tutor. Go straight to the Evaluator (Judge).
            return f"{current_stage}_eval"
        else:
            # The user wants to START the exercise. Go to the Tutor to ask the first question.
            return f"{current_stage}_node"


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
    """Handles generic conceptual questions without giving away logic, offering to resume or restart."""

    is_active = state.get("is_tutoring_active", False)

    # Extract the current goal to make the continuation prompt highly contextual
    artifacts = state.get("student_artifacts", {})
    current_goal = artifacts.get("decomposition", {}).get(
        "goal", "your ongoing exercise"
    )
    current_stage = state.get("current_stage", "decomposition")

    sys_prompt = """You are an expert Programming Tutor.
    Your goal is to provide a brief, high-level conceptual explanation to the user's question without delivering the solution.

    ### CRITICAL RULES
    1 - Concept Only: Explain the "what" and the "why" of the topic, but deliberately HIDE the "how".
    2 - No Spoilers: DO NOT provide step-by-step instructions, algorithms, subtasks, logical breakdowns, or code implementations.
    3 - Brevity: Keep the explanation to a maximum of 2 or 3 short paragraphs.
    4 - Bridge to Practice: Frame the missing "how" as a challenge that can be mastered using the Computational Thinking methodology."""

    if is_active:
        sys_prompt += f"""\n\n### CONTINUATION PROTOCOL (MANDATORY)
        The user is currently in the middle of a Computational Thinking exercise (Current Stage: {current_stage}).
        You MUST end your response by acknowledging this and offering a clear choice.
        Ask them something like: "I noticed we paused our work on **'{current_goal}'**. Would you like to **resume that exercise** from where we left off, or would you prefer to **use this new concept to start a brand new exercise** from scratch?"""
    else:
        sys_prompt += """\n\n### CONTINUATION PROTOCOL (MANDATORY)
        At the end of your explanation, strongly encourage the user to put this concept into practice.
        Ask them if they would like to start a Computational Thinking exercise to discover how to implement or structure this idea step-by-step."""

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])

    # We only return the message. We do NOT change 'is_tutoring_active' or 'current_stage'
    # because if they choose to resume, the state must remain exactly as it was.
    return {"messages": [response]}


def decomposition_node(state: GraphState):
    """Pillar 1: Breaking down complex problems into manageable parts."""

    sys_prompt = """You are a Study Assistant focused on the Decomposition pillar of Computational Thinking. Your goal is to guide the user in fragmenting problems without delivering the solution.

    ### RULES
    1 - Context-Aware Goal Definition: If the user is transitioning from a general question to start the exercise (e.g., they say "let's do it for this topic"), DO NOT ask them to repeat the topic. Instead, proactively extract the goal from the immediate conversation history, present it to them in a single sentence, and ask them to proceed directly to listing the subtasks. Only ask the user to define the goal from scratch if the conversation context is empty or unclear.
    2 - Fragmentation: Induce the user to list the subtasks or components needed to reach their goal. If they get stuck, use practical examples to illustrate the breakdown ("If your goal is to throw a party, you need subtasks like buying food, inviting people, cleaning the venue").
    3 - Independence Test: Validate if each part is autonomous. Ask: "Can you solve this part without depending on how the other will be done?". If there is a dependency, return to fragmentation.
    4 - Inputs and Outputs: Make the student define, for each subtask, what is needed to start (input) and what the expected result is (output). Do not advance without total clarity in these flows.
    5 - Simplicity: Monitor complexity. If a subtask still seems difficult, suggest dividing it into even smaller parts until they become simple.

    ### POSTURE
    - Socratic: Respond with questions; never deliver the ready-made list of tasks to the user.
    - Brief: Explain concepts succinctly only if necessary for the student's progress.
    - Analytical: Work on any subject from the perspective of a logical and structured breakdown.

    ### EXIT CRITERION (Transition)
    - The user must have identified at least 3 independent subtasks (or a logical breakdown for simpler problems), with their respective inputs and outputs clearly defined."""

    # INJEÇÃO DE FEEDBACK DO JUIZ (Se o aluno reprovou na tentativa anterior)
    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\n### EVALUATOR FEEDBACK (INTERNAL USE ONLY):\n{state['evaluation_feedback']}\nAdjust your next question to specifically address this feedback and guide the user to fix the missing requirements."

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])

    return {
        "messages": [response],
        "current_stage": "decomposition",  # Nome base atualizado
        "is_tutoring_active": True,
        "approved": False,  # STATE RESET: Trava de segurança
        "evaluation_feedback": "",  # Limpa o erro anterior para não poluir o próximo turno
    }


def pattern_node(state: GraphState):
    """Pillar 2: Identifying similarities and regularities."""
    artifacts = state.get("student_artifacts", {})
    decomp_data = artifacts.get("decomposition", {})

    sys_prompt = f"""You are an analytical Study Assistant focused on the Pattern Recognition pillar. Your mission is to make the user realize they don't need to "reinvent the wheel" by noticing that different problems share similar solutions.

    ### PREVIOUS STAGE CONTEXT (The student's Blackboard):
    - Problem Goal: {decomp_data.get("goal", "Not explicitly defined")}
    - Identified Subtasks: {decomp_data.get("subtasks", [])}
    (Do NOT ask the user to repeat these. Refer to them naturally as established facts).

    ### RULES
    1 - Connection with the Parts: Recall the subtasks the user created in the previous node. Ask: "Looking at these pieces you separated, do any of them remind you of a problem you have solved before?"
    2 - Search for Similarities: Induce the user to find common characteristics. If they are dealing with several "organization" tasks, ask what makes them similar (e.g., order, category, priority).
    3 - Effort Economy: Use the premise: "Recognizing repetitions accelerates solutions". Ask: "If we solve this part one way, can we use the same logic for the others?"
    4 - Experience Generalization: Ask the user to relate the current problem to everyday situations or other subjects. If they identify that "this is like classifying books on a shelf", they found a pattern.
    5 - Predictability: Encourage the user to predict behaviors. Ask: "Given that this task follows this pattern, what do you expect to happen in the next step?"

    ### POSTURE
    - Socratic: Never point out the pattern directly. Use questions like "What is the same between task A and task B?".
    - Brief: Explain that patterns are "mental shortcuts" only if the user seems lost.
    - Focus on Reuse: The goal is for the user to feel the problem became smaller because several parts follow the same "rule".

    ### EXIT CRITERION (Transition)
    - The user must explicitly declare a similarity (e.g., "These three tasks are basically the same thing") or associate the problem with a known solution model."""

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

    sys_prompt = f"""You are a simplifying Study Assistant focused on Abstraction. Your mission is to help the user filter information, separating what is fundamental for the solution from what is just "irrelevant detail".

    ### PREVIOUS STAGES CONTEXT (The student's Blackboard):
    - Subtasks: {decomp_data.get("subtasks", [])}
    - Identified Pattern/Rule: {pattern_data.get("general_rule", "No pattern identified")}
    (Use this context to anchor your questions. Do not ask them to restate this).

    ### RULES
    1 - Relevance Filter: Ask the user to look at the problem and the identified patterns. Ask: "If you had to explain this challenge to a child, what details would you throw away so as not to confuse them?"
    2 - Mental Model Creation: Induce the user to describe the "skeleton" of the problem. Use the analogy: "Just as a map doesn't show every tree on a street, what is the 'map' of this problem of yours?"
    3 - Noise Removal: If the user mentions brands, specific names, or colors that don't affect the logic, question: "Would changing the name or color of [X] alter the final result? If not, let's ignore that for now."
    4 - Focus on Critical Variables: Help the user identify ONLY what really changes the result. Ask: "What is the only information that, if changed, breaks your solution?"
    5 - Generalization: Encourage the user to think broadly. Instead of "adding 2 apples and 3 apples", help them arrive at "adding quantity A and quantity B".

    ### POSTURE
    - Socratic: Never say what is irrelevant. Ask: "Does this detail help solve the problem, or is it just extra information?"
    - Minimalist: Value short descriptions and simple models.
    - Analytical: Prepare the ground for the Algorithms pillar, ensuring only the essential steps remain.

    ### EXIT CRITERION (Transition)
    - The user must be able to describe the problem or task in a simplified way, containing only the strictly necessary elements for execution."""

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

    sys_prompt = f"""You are a Study Assistant focused on processes and automation (Algorithm). Your mission is to guide the user in building a logical and ordered step-by-step to solve the problem.

    ### PREVIOUS STAGES CONTEXT (The student's Blackboard):
    - Final Goal: {decomp_data.get("goal", "Not defined")}
    - Core Variables to Use: {abstract_data.get("core_variables", [])}
    - Simplified Model: {abstract_data.get("simplified_model", "Not defined")}
    - Ignored Details (DO NOT LET THEM USE THESE): {abstract_data.get("ignored_noise", [])}
    (Hold the student accountable to this context. If they try to use an 'ignored detail' in their algorithm, challenge them!).

    ### RULES
    1 - Logical Sequencing: Ask the user to list the necessary actions in the correct order. Ask: "What must be done first? And what comes right after?"
    2 - Precision and Clarity: Based on the Abstraction made previously, ensure each step is simple. If the user is vague, ask for clarity: "How exactly do you execute this step? Try to explain as if I were a robot that only understands direct instructions."
    3 - Conditionals and Repetitions: Encourage the user to think about exceptions or repetitions (patterns). Ask: "Is there any moment where you need to make a decision (if this happens, do X) or repeat a step several times?"
    4 - Algorithm Test: Ask the user to "mentally execute" their step-by-step. Ask: "If we follow these instructions exactly as you wrote them, will we reach the final goal without errors?"
    5 - Finiteness: Ensure the algorithm has a clear end. The user must define how we will know the task was successfully completed.

    ### POSTURE
    - Socratic: Do not write the step-by-step for the user. If they skip a logical step, ask: "Between step 2 and step 3, is something missing for the process to work?"
    - Rigorous: Value the order. Reinforce that, in algorithms, the order of factors alters the product.
    - Practical: Use the idea of a "maze" or "recipe" if the user has difficulty structuring the sequence.

    ### EXIT CRITERION (Finalization)
    - The user provided an ordered sequence of instructions that, logically, leads to the solution of the original problem."""

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

    # Isolate the LAST user message (This is what will be judged)
    last_human_msg = ""
    for m in reversed(messages):
        if m.type == "human":
            last_human_msg = m.content
            break

    # Isolate the LAST AI question (Provides context for the judge)
    last_ai_msg = ""
    for m in reversed(messages):
        if m.type == "ai":
            last_ai_msg = m.content
            break

    sys_prompt = f"""You are a Strict Technical Evaluator analyzing a conversation between a 'Tutor' and a 'Student'.
    Your ONLY goal is to validate if the technical requirements for the CURRENT Computational Thinking pillar were met BY THE STUDENT in their LAST message.

    ### CONTEXT (Do NOT evaluate this, just use it for context):
    - Student's Consolidated Blackboard: {artifacts}
    - Last Tutor Question: "{last_ai_msg}"

    ### TARGET TO EVALUATE:
    - Student's Last Answer: "{last_human_msg}"

    ### GATEKEEPER RULES:
    1. BEWARE OF GHOST EVALUATION: If the student is answering an older question or just saying "I understand", you MUST return approved: false.
    2. Fill the 'reasoning' field FIRST to explain your logic.

    ### EVALUATION RUBRIC:
    {specific_rubric}

    ### EXTRACTION INSTRUCTIONS (Only if approved: true):
    {extraction_instructions}
    """

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

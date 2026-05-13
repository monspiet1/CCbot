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
    reasoning: str = Field(
        description="Step-by-step reasoning analyzing if the LAST HUMAN MESSAGE satisfies the CURRENT stage's rubric. Explicitly state if the user is answering a previous question and not the current one."
    )
    approved: bool = Field(
        description="True ONLY IF the student met the criteria for the CURRENT pillar. False if they are answering an older stage."
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

    # Retrieve the last AI message to provide context for the classification
    last_ai_msg = "None"
    for m in reversed(messages[:-1]):
        if m.type == "ai":
            last_ai_msg = m.content
            break

    is_active = state.get("is_tutoring_active", False)
    current_stage = state.get("current_stage", "decomposition_node")

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
       - The user is answering the Tutor's Socratic question related to the current stage (e.g., providing a goal definition, listing subtasks, identifying patterns, simplifying details, or creating steps).
       - The user presents a specific, practical programming, logic, or algorithmic problem to solve (e.g., "How do I implement a queue to manage a hospital?", "If I have numbers 1, 2, 3 in that order and remove one, what do I get?"). These practical challenges MUST be routed to tutoring so the user can be guided to think and solve them step-by-step.
    3. 'general_qa':
       - The user asks for a purely theoretical definition, conceptual explanation, or syntax clarification (e.g., "What is an array?", "What is the theoretical definition of a queue?").
       - Do NOT use this for real-world scenarios or logic puzzles.

    ROUTING LOGIC:
    - If 'Tutoring Session Active' is True, assume the user is participating in the exercise (intent = 'tutoring') unless they explicitly pivot to a new purely conceptual question or ignore the Tutor's Socratic prompt entirely.
    - If the user introduces a real-world problem, a project idea, or a logic puzzle, strictly classify it as 'tutoring' to automatically trigger the Computational Thinking methodology starting with Decomposition.
    - If the user provides a brief answer that fits the last Tutor question, it is strictly 'tutoring'.
    - If the user asks for a definition or explanation during a tutoring session, classify as 'general_qa' to allow the Tutor to provide a quick theoretical answer before resuming the exercise.
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
    """Handles generic questions conceptually without giving away the full logic, offering to resume or restart."""

    is_active = state.get("is_tutoring_active", False)

    sys_prompt = """You are an expert Programming Tutor.
    Your goal is to provide a brief, high-level conceptual explanation to the user's question.

    ### CRITICAL RULES
    1 - Concept Only: Explain the "what" and the "why" of the topic, but deliberately HIDE the "how".
    2 - No Spoilers: DO NOT provide step-by-step instructions, algorithms, subtasks, logical breakdowns, or code implementations.
    3 - Brevity: Keep the explanation to a maximum of 2 or 3 short paragraphs.
    4 - Bridge to Practice: Frame the missing "how" as a challenge that can be solved using Computational Thinking."""

    if is_active:
        sys_prompt += "\n\nAo final da sua resposta, diga exatamente: 'Notei que você tem um exercício de Pensamento Computacional em andamento. Você gostaria de **retomar o exercício anterior** de onde paramos, ou quer **usar essa sua nova dúvida para iniciar um novo fluxo** do zero?'"
    else:
        sys_prompt += "\n\nAo final da resposta, sugira fortemente que ele inicie um exercício de Pensamento Computacional para descobrir na prática como implementar ou estruturar isso passo a passo."

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])
    return {"messages": [response]}


def decomposition_node(state: GraphState):
    """Pillar 1: Breaking down complex problems into manageable parts[cite: 119]."""
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

    if state.get("evaluation_feedback"):
        sys_prompt += f"\n\n### EVALUATOR FEEDBACK (INTERNAL USE ONLY):\n{state['evaluation_feedback']}\nAdjust your next question to address this feedback."

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])

    return {
        "messages": [response],
        "current_stage": "decomposition_node",
        "is_tutoring_active": True,
    }


def pattern_node(state: GraphState):
    """Pillar 2: Identifying similarities and regularities[cite: 132]."""
    sys_prompt = """You are an analytical Study Assistant focused on the Pattern Recognition pillar. Your mission is to make the user realize they don't need to "reinvent the wheel" by noticing that different problems share similar solutions.

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
        "current_stage": "pattern_node",
        "is_tutoring_active": True,
    }


def abstraction_node(state: GraphState):
    """Pillar 3: Filtering information to focus on the essential[cite: 140]."""
    sys_prompt = """You are a simplifying Study Assistant focused on Abstraction. Your mission is to help the user filter information, separating what is fundamental for the solution from what is just "irrelevant detail".

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
        "current_stage": "abstraction_node",
        "is_tutoring_active": True,
    }


def algorithm_node(state: GraphState):
    """Pillar 4: Creating ordered steps to solve the problem[cite: 149]."""
    sys_prompt = """You are a Study Assistant focused on processes and automation (Algorithm). Your mission is to guide the user in building a logical and ordered step-by-step to solve the problem.

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
        "current_stage": "algorithm_node",
        "is_tutoring_active": True,
    }


def generic_evaluator(state: GraphState, specific_rubric: str):
    """Executes the LLM-as-a-judge with a specific rubric and structured output, strictly isolating the human's input."""
    messages = state["messages"]

    last_human_msg = ""
    for m in reversed(messages):
        if m.type == "human":
            last_human_msg = m.content
            break

    base_prompt = """You are a Strict Technical Evaluator analyzing a conversation between a 'Mentor' and a 'Student'.
        Your goal is to validate if the technical requirements for the CURRENT Computational Thinking pillar were met BY THE STUDENT.

        CRITICAL RULES (GATEKEEPER):
        1. Evaluate ONLY the student's LAST message: "{last_human}"
        2. BEWARE OF GHOST EVALUATION: The student's last message might be answering the PREVIOUS stage. If the message does not explicitly contain the core objective of the CURRENT rubric, you MUST return approved: false.
        3. Use the 'reasoning' field to explain your logic first. State clearly if the student is actually answering the current question or just an old one.

        EVALUATION RUBRIC:
        {rubric}
        """

    sys_prompt = base_prompt.format(rubric=specific_rubric, last_human=last_human_msg)

    decision = llm_structured_eval.invoke(
        [SystemMessage(content=sys_prompt)] + messages
    )

    return cast(EvaluationResult, decision)


def decomposition_eval(state: GraphState):
    rubric = """
        - Single Goal: Did the student synthesize the problem into a clear, final sentence?
        - Granularity: Did the student list subtasks? (Note: Do not strictly force 3 subtasks if the problem is too simple, but ensure logical breakdown).
        - Independence: Are the tasks autonomous enough to be solved without mutual implementation dependency?
        - Interfaces (I/O): Did the student explicitly define what is needed to start (Input) and the expected result (Output) for each subtask?

        CONDITIONAL LOGIC:
        - IF all criteria above are met: Set 'approved': true and 'next_action': 'advance'.
        - IF the user gave a partial answer or forgot a criterion (e.g., forgot inputs/outputs): Set 'approved': false and 'next_action': 'reinforce'.
        - IF the user shows frustration or does not understand the concept: Set 'approved': false and 'next_action': 'didactic_example'.
        """
    res = generic_evaluator(state, rubric)

    if res.approved:
        return {
            "evaluation_feedback": res.internal_feedback,
            "approved": True,
            "current_stage": "pattern_node",
        }

    return {"evaluation_feedback": res.internal_feedback, "approved": False}


def pattern_eval(state: GraphState):
    rubric = """
        ### EVALUATION CRITERIA (CHECKLIST)
        1. Historical Connection: Did the student relate the current subtasks to past experiences or known problems?
        2. Similarity Identification: Did the student explicitly point out common characteristics (attributes, behaviors, rules) between the decomposed parts?
        3. Reuse Perception: Did the student demonstrate an understanding that a single logic or "mental shortcut" can be applied to more than one task?
        4. Generalization: Did the student formulate and describe the "general rule" or the pattern behind the repetitions?

        ### FATAL EXCEPTION: STAGE MISMATCH (MUST FAIL)
        If the message does NOT explicitly contain an analogy, a real-world comparison, or a mention of a pattern/similarity, they have NOT answered the Pattern Recognition question yet. You MUST return approved: false.
        Simply agreeing (e.g., "Yes, it makes sense") is also a FAIL.

        ### STRICT CONDITIONAL LOGIC (GATEKEEPER)
        - TO APPROVE ('approved': true, 'next_action': 'advance'): The student MUST have explicitly identified a similarity or associated the problem with a known solution model in THEIR OWN WORDS. Simply agreeing with the Mentor (e.g., "Yes, that makes sense", "Exactly") is an automatic FAIL.
        - TO REINFORCE ('approved': false, 'next_action': 'reinforce_pattern'): If the student realized tasks are similar but could not explain WHY or HOW to reuse the logic.
        - TO GIVE EXAMPLE ('approved': false, 'next_action': 'didactic_example'): If the student cannot see any relationship between tasks or tries to solve each as an entirely new, unrelated problem.
        """
    res = generic_evaluator(state, rubric)

    if res.approved:
        return {
            "evaluation_feedback": res.internal_feedback,
            "approved": True,
            "current_stage": "abstraction_node",
        }
    return {"evaluation_feedback": res.internal_feedback, "approved": False}


def abstraction_eval(state: GraphState):
    rubric = """
        ### EVALUATION CRITERIA (CHECKLIST)
        1. Noise Identification: Did the student successfully separate irrelevant information (cosmetic details, specific names, isolated examples) from the core problem?
        2. Critical Variables Definition: Did the student explicitly identify which data or fundamental components truly impact the final result?
        3. Simplified Modeling: Did the student describe the "skeleton" or "map" of the problem in a generalized way (e.g., swapping "apples" for "quantities")?
        4. Essentialism: Is the student's final description minimalist, focusing ONLY on what is strictly necessary to build an algorithm?

        ### STRICT CONDITIONAL LOGIC (GATEKEEPER)
        - TO APPROVE ('approved': true, 'next_action': 'advance'): The student MUST have explicitly described the problem in a simplified way, containing ONLY the strictly necessary elements for execution. If the student has not yet produced this "skeleton" sentence, you MUST fail them.
        - TO REINFORCE ('approved': false, 'next_action': 'reinforce_abstraction'): If the student is still attached to specific details or gets lost in long descriptions containing "extra" or irrelevant information.
        - TO GIVE EXAMPLE ('approved': false, 'next_action': 'didactic_example'): If the student cannot differentiate what is essential from what is a detail, showing confusion about the "skeleton" of the problem.
        """
    res = generic_evaluator(state, rubric)

    if res.approved:
        return {
            "evaluation_feedback": res.internal_feedback,
            "approved": True,
            "current_stage": "algorithm_node",
        }
    return {"evaluation_feedback": res.internal_feedback, "approved": False}


def algorithm_eval(state: GraphState):
    rubric = """
        ### EVALUATION CRITERIA (CHECKLIST)
        1. Sequencing: Are the instructions in a correct logical and chronological order?
        2. Determinism (Clarity): Are the steps precise enough to be executed by a "robot", without ANY ambiguities?
        3. Flow Control: Did the student consider conditions (IF/THEN) or repetitions (LOOPS) where necessary?
        4. Conclusion (Finiteness): Does the algorithm have a clear stopping point and successfully reach the final goal defined in the first stage?

        ### STRICT CONDITIONAL LOGIC (GATEKEEPER)
        - TO APPROVE ('approved': true, 'next_action': 'advance'): The user MUST have provided a complete, ordered sequence of instructions that logically leads to the solution. If the list is missing, implicit, or just a generic summary, you MUST fail them.
        - TO REINFORCE ('approved': false, 'next_action': 'reinforce_algorithm'): If the algorithm is incomplete, out of order, or missing essential logical steps.
        - TO GIVE EXAMPLE ('approved': false, 'next_action': 'didactic_example'): If the student does not understand how to structure steps or creates overly generic instructions (e.g., "just do the task").
        """
    res = generic_evaluator(state, rubric)

    if res.approved:
        return {
            "evaluation_feedback": res.internal_feedback,
            "approved": True,
            "is_tutoring_active": False,
        }
    return {"evaluation_feedback": res.internal_feedback, "approved": False}


def route_decomposition(state: GraphState):
    return "pattern_node" if state.get("approved") else "decomposition_node"


def route_pattern(state: GraphState):
    return "abstraction_node" if state.get("approved") else "pattern_node"


def route_abstraction(state: GraphState):
    return "algorithm_node" if state.get("approved") else "abstraction_node"


def route_algorithm(state: GraphState):
    return END if state.get("approved") else "algorithm_node"

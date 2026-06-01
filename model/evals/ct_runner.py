from __future__ import annotations

import copy
from typing import Any

from deepeval.test_case import ConversationalTestCase, Turn
from langchain_core.messages import HumanMessage

from evals.ct_constants import CHATBOT_ROLE, COMPUTATIONAL_THINKING_CONTEXT
from evals.ct_scenarios import EducationalScenario
from workflow import app as langgraph_app


def make_initial_state() -> dict[str, Any]:
    """
    Estado inicial esperado pelo GraphState.

    Esse estado evita que o teste dependa de memória externa ou checkpointer.
    Cada cenário começa de forma isolada.
    """
    return {
        "messages": [],
        "current_stage": "decomposition",
        "is_tutoring_active": False,
        "approved": False,
        "evaluation_feedback": "",
        "student_artifacts": {},
    }


def message_to_text(message: Any) -> str:
    """
    Normaliza mensagens LangChain para string.
    Alguns modelos podem retornar content como str ou como lista multimodal.
    """
    content = getattr(message, "content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
            else:
                parts.append(str(item))
        return "\n".join(parts)

    return str(content)


def count_ai_messages(state: dict[str, Any]) -> int:
    return sum(
        1
        for message in state.get("messages", [])
        if getattr(message, "type", None) == "ai"
    )


def get_new_assistant_messages(
    previous_state: dict[str, Any],
    current_state: dict[str, Any],
) -> list[str]:
    """
    Retorna somente as novas mensagens do assistente geradas no último invoke().
    """
    previous_ai_count = count_ai_messages(previous_state)

    ai_messages = [
        message
        for message in current_state.get("messages", [])
        if getattr(message, "type", None) == "ai"
    ]

    new_messages = ai_messages[previous_ai_count:]
    return [message_to_text(message) for message in new_messages]


def run_scripted_conversation(
    scenario: EducationalScenario,
) -> tuple[ConversationalTestCase, dict[str, Any], list[dict[str, Any]]]:
    """
    Executa uma conversa scripted contra o LangGraph.

    Retorna:
    - ConversationalTestCase: objeto usado pelo DeepEval.
    - final_state: estado final do LangGraph.
    - trace: trilha simplificada para auditoria e relatório.
    """
    state = make_initial_state()
    turns: list[Turn] = []
    trace: list[dict[str, Any]] = []

    for index, user_message in enumerate(scenario.user_messages, start=1):
        previous_state = copy.deepcopy(state)

        input_state = {
            **state,
            "messages": [
                *state.get("messages", []),
                HumanMessage(content=user_message),
            ],
        }

        state = langgraph_app.invoke(input_state)

        assistant_messages = get_new_assistant_messages(
            previous_state=previous_state,
            current_state=state,
        )

        assistant_output = "\n\n".join(
            message for message in assistant_messages if message.strip()
        )

        turns.append(Turn(role="user", content=user_message))

        if assistant_output.strip():
            turns.append(Turn(role="assistant", content=assistant_output))

        trace.append(
            {
                "turn_index": index,
                "user": user_message,
                "assistant": assistant_output,
                "current_stage": state.get("current_stage"),
                "approved": state.get("approved"),
                "is_tutoring_active": state.get("is_tutoring_active"),
                "evaluation_feedback": state.get("evaluation_feedback"),
                "student_artifacts_keys": list(
                    state.get("student_artifacts", {}).keys()
                ),
            }
        )

    test_case = ConversationalTestCase(
        scenario=scenario.scenario,
        expected_outcome=scenario.expected_outcome,
        user_description=scenario.user_description,
        chatbot_role=CHATBOT_ROLE,
        context=COMPUTATIONAL_THINKING_CONTEXT,
        turns=turns,
    )

    return test_case, state, trace

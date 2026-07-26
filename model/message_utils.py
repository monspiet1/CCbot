from typing import List

from langchain_core.messages import AnyMessage


def get_last_human_message(messages: List[AnyMessage]) -> str:
    """Extrai o conteúdo da última mensagem humana da lista de mensagens."""
    for m in reversed(messages):
        if m.type == "human":
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


def get_last_ai_message(messages: List[AnyMessage]) -> str:
    """Extrai o conteúdo da última mensagem de IA da lista de mensagens."""
    for m in reversed(messages):
        if m.type == "ai":
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""

from typing import Any, Type

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

load_dotenv("./.env")

DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_RETRIES = 3
DEFAULT_REQUEST_TIMEOUT = 120.0


def get_llm(
    temperature: float = DEFAULT_TEMPERATURE,
    model: str = DEFAULT_MODEL,
    max_retries: int = DEFAULT_MAX_RETRIES,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> BaseChatModel:
    """Factory centralizada para instanciar o LLM base do Tutor."""
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        max_retries=max_retries,
        request_timeout=request_timeout,
    )


def get_structured_llm(
    schema: Type[BaseModel],
    temperature: float = DEFAULT_TEMPERATURE,
    model: str = DEFAULT_MODEL,
    max_retries: int = DEFAULT_MAX_RETRIES,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> Runnable:
    """Factory para LLM com saída estruturada (with_structured_output)."""
    llm = get_llm(temperature, model, max_retries, request_timeout)
    return llm.with_structured_output(schema)

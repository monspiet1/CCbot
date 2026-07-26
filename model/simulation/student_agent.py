import random
from typing import List

from langchain_core.messages import AnyMessage, SystemMessage

from llm_factory import get_llm
from simulation.schema import StudentProfile

STUDENT_SYSTEM_PROMPT = """Você é um Estudante humano simulado interagindo com um Tutor de Inteligência Artificial baseado no Pensamento Computacional.

### PERFIL DISCENTE:
- Identificação: {name}
- Nível de Conhecimento Prévio: {knowledge_level}
- Estilo Linguístico: {communication_style}
- Objetivo Pedagógico: {domain_problem}

### DIRETRIZES COMPORTAMENTAIS DE SIMULAÇÃO:
1. Aja estritamente como um estudante que está aprendendo lógica de programação. Nunca revele que você é um modelo de linguagem ou um assistente virtual.
2. Responda especificamente à última pergunta formulada pelo Tutor, aplicando o seguinte comportamento de simulação:{behavior_instruction}
3. Restrinja o tamanho da resposta a um formato compatível com interações em chat educacional (máximo de 1 a 3 parágrafos curtos)."""

BEHAVIOR_IMPATIENT = """
- COMPORTAMENTO ATUAL: Você está demonstrando impaciência com o método socrático. Reclame que a abordagem está excessivamente abstrata ou demorada, exija que o tutor forneça o código em Python ou a resposta final, e forneça uma resposta incompleta à pergunta formulada."""

BEHAVIOR_ERROR = """
- COMPORTAMENTO ATUAL: Introduza um erro conceitual ou lógico característico de estudantes na etapa de {stage}. Por exemplo, na Decomposição, misture conceitos de entrada com saída ou liste tarefas interdependentes; na Abstração, insista em manter detalhes estéticos ou ruídos irrelevantes."""

BEHAVIOR_COLLABORATIVE = """
- COMPORTAMENTO ATUAL: Colabore ativamente com a solicitação do tutor, respondendo de forma lógica e alinhada a um estudante com nível de conhecimento {knowledge_level}."""


def run_student_turn(
    messages: List[AnyMessage], profile: StudentProfile, current_stage: str
) -> str:
    """Executa um turno interativo do Agente Aluno formulando uma resposta com base na pergunta do Tutor e no perfil discente."""
    should_make_error = random.random() < profile.error_propensity
    should_be_impatient = random.random() < profile.impatience_level

    if should_be_impatient:
        behavior_instruction = BEHAVIOR_IMPATIENT
    elif should_make_error:
        behavior_instruction = BEHAVIOR_ERROR.format(stage=current_stage.upper())
    else:
        behavior_instruction = BEHAVIOR_COLLABORATIVE.format(
            knowledge_level=profile.knowledge_level.upper()
        )

    sys_prompt = STUDENT_SYSTEM_PROMPT.format(
        name=profile.name,
        knowledge_level=profile.knowledge_level,
        communication_style=profile.communication_style,
        domain_problem=profile.domain_problem,
        behavior_instruction=behavior_instruction,
    )

    llm = get_llm(temperature=0.7)

    invocation_messages = [SystemMessage(content=sys_prompt)] + messages[-6:]
    response = llm.invoke(invocation_messages)

    return response.content if isinstance(response.content, str) else str(response.content)

import random
from typing import List

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage

from llm_factory import get_llm
from simulation.schema import StudentProfile

MAX_ATTEMPTS_PER_STAGE = 2

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
- COMPORTAMENTO ATUAL: Você é um estudante dedicado e curioso. Colabore ativamente.
- Reflita internamente sobre a explicação do tutor e aja da seguinte forma:
  1. Se não compreender totalmente, formule uma nova pergunta conectada à resposta anterior.
  2. Raciocine de forma estruturada (Chain of Thought) e avance passo a passo.
- Responda de forma lógica e alinhada a um estudante de nível {knowledge_level}."""

BEHAVIOR_COMPREHENSION = """
- COMPORTAMENTO ATUAL: Você refletiu internamente e alcançou a compreensão plena da etapa de {stage}.
- Para que o sistema reconheça seu avanço, você DEVE fornecer a síntese COMPLETA e ESTRUTURADA em sua resposta.
- Se for Decomposição: Escreva o objetivo final, liste todas as subtarefas e defina Entrada (Input) e Saída (Output) para CADA subtarefa.
- Se for Padrões: Descreva a regra geral e as semelhanças encontradas.
- Se for Abstração: Liste as variáveis críticas, os detalhes ignorados e o modelo simplificado.
- Se for Algoritmo: Escreva o passo a passo completo, com condições/loops e critério de parada.
- Não deixe faltar nenhum elemento! Seja cooperativo e exato."""


def _ensure_last_message_is_human(messages: List[AnyMessage]) -> List[AnyMessage]:
    """Garante que a última mensagem seja um HumanMessage para compatibilidade com Gemini."""
    if not messages:
        return [HumanMessage(content="Por favor, comece sua resposta.")]

    last_msg = messages[-1]
    if isinstance(last_msg, AIMessage):
        return messages[:-1] + [
            HumanMessage(content="Por favor, responda à pergunta anterior do Tutor.")
        ]
    return messages


def run_student_turn(
    messages: List[AnyMessage],
    profile: StudentProfile,
    current_stage: str,
    attempts_in_stage: int,
) -> str:
    """Executa um turno interativo do Agente Aluno formulando uma resposta com base na pergunta do Tutor e no perfil discente."""
    if attempts_in_stage >= MAX_ATTEMPTS_PER_STAGE:
        behavior_instruction = BEHAVIOR_COMPREHENSION.format(
            stage=current_stage.upper()
        )
    else:
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

    context_messages = _ensure_last_message_is_human(messages[-6:])
    invocation_messages = [SystemMessage(content=sys_prompt)] + context_messages
    response = llm.invoke(invocation_messages)

    return (
        response.content if isinstance(response.content, str) else str(response.content)
    )

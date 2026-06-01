from __future__ import annotations

import os

from deepeval.metrics import (
    ConversationalGEval,
    ConversationCompletenessMetric,
    KnowledgeRetentionMetric,
    RoleAdherenceMetric,
)

# Compatibilidade entre versões do DeepEval.
# Em versões atuais, a métrica documentada é TurnRelevancyMetric.
try:
    from deepeval.metrics import TurnRelevancyMetric
except ImportError:  # pragma: no cover
    from deepeval.metrics import ConversationRelevancyMetric as TurnRelevancyMetric

from deepeval.test_case import MultiTurnParams


def _judge_kwargs() -> dict:
    """
    Permite trocar o LLM juiz sem alterar o código.

    Exemplo:
    export DEEPEVAL_JUDGE_MODEL="gpt-4.1"
    """
    model = os.getenv("DEEPEVAL_JUDGE_MODEL")

    if not model:
        return {}

    return {"model": model}


def computational_thinking_flow_metric() -> ConversationalGEval:
    """
    Métrica customizada principal para o artigo.

    Ela mede se a conversa seguiu o fluxo pedagógico de Pensamento Computacional,
    algo que as métricas genéricas não capturam completamente.
    """
    return ConversationalGEval(
        name="Computational Thinking Pedagogical Flow",
        evaluation_steps=[
            (
                "Verifique se o assistente conduziu a conversa de forma sequencial "
                "pelos pilares Decomposição, Reconhecimento de Padrões, Abstração "
                "e Algoritmo, sem pular etapas indevidamente."
            ),
            (
                "Verifique se o assistente manteve postura socrática, fazendo perguntas "
                "orientadoras em vez de entregar a solução pronta ou código final."
            ),
            (
                "Verifique se o assistente exigiu, na etapa de Decomposição, subtarefas "
                "com entradas e saídas explícitas."
            ),
            (
                "Verifique se o assistente exigiu, na etapa de Reconhecimento de Padrões, "
                "uma relação explícita com experiências, algoritmos ou modelos conhecidos."
            ),
            (
                "Verifique se o assistente exigiu, na etapa de Abstração, a separação entre "
                "variáveis essenciais e detalhes irrelevantes."
            ),
            (
                "Verifique se o assistente exigiu, na etapa de Algoritmo, uma sequência "
                "ordenada, clara, finita e com condições ou repetições quando aplicável."
            ),
            (
                "Penalize fortemente se o assistente avançar de etapa quando a resposta "
                "do aluno ainda estiver vaga, incompleta ou sem os artefatos esperados."
            ),
        ],
        evaluation_params=[MultiTurnParams.CONTENT],
        threshold=0.75,
        strict_mode=False,
        async_mode=False,
        **_judge_kwargs(),
    )


def build_conversational_metrics() -> list:
    """
    Conjunto enxuto de métricas para evitar redundância.

    DeepEval recomenda priorizar poucas métricas: 2-3 genéricas e 1-2 customizadas.
    """
    kwargs = _judge_kwargs()

    return [
        RoleAdherenceMetric(
            threshold=0.75,
            include_reason=True,
            strict_mode=False,
            **kwargs,
        ),
        ConversationCompletenessMetric(
            threshold=0.70,
            include_reason=True,
            strict_mode=False,
            **kwargs,
        ),
        TurnRelevancyMetric(
            threshold=0.70,
            include_reason=True,
            strict_mode=False,
            **kwargs,
        ),
        computational_thinking_flow_metric(),
    ]

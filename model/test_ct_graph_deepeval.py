# tests/test_ct_graph_deepeval.py

from __future__ import annotations

import pytest
from deepeval import assert_test

from evals.ct_metrics import build_conversational_metrics
from evals.ct_runner import run_scripted_conversation
from evals.ct_scenarios import (
    GENERAL_QA_DURING_TUTORING_SCENARIO,
    NEGATIVE_DECOMPOSITION_SCENARIO,
    POSITIVE_SCENARIOS,
)


@pytest.mark.parametrize(
    "scenario",
    POSITIVE_SCENARIOS,
    ids=lambda scenario: scenario.id,
)
def test_positive_conversation_passes_deepeval_metrics(scenario):
    """
    Teste end-to-end principal.

    Valida:
    1. O grafo executa uma conversa completa.
    2. Os quatro artefatos pedagógicos são preenchidos.
    3. O DeepEval considera a conversa adequada nas métricas conversacionais.
    """
    test_case, final_state, trace = run_scripted_conversation(scenario)

    artifacts = final_state.get("student_artifacts", {})

    assert "decomposition" in artifacts, trace
    assert "pattern" in artifacts, trace
    assert "abstraction" in artifacts, trace
    assert "algorithm" in artifacts, trace

    assert final_state.get("is_tutoring_active") is False, trace

    assert_test(
        test_case=test_case,
        metrics=build_conversational_metrics(),
        run_async=False,
    )


def test_gatekeeper_rejects_incomplete_decomposition():
    """
    Valida que uma resposta vaga na etapa de Decomposição não permite avanço
    para Reconhecimento de Padrões.

    O campo evaluation_feedback não é verificado no estado final porque ele é
    consumido pelo nó tutor seguinte e limpo antes do retorno do app.invoke().
    """
    _, final_state, trace = run_scripted_conversation(NEGATIVE_DECOMPOSITION_SCENARIO)

    artifacts = final_state.get("student_artifacts", {})

    assert final_state.get("current_stage") == "decomposition", trace
    assert final_state.get("is_tutoring_active") is True, trace
    assert final_state.get("approved") is False, trace

    assert "decomposition" not in artifacts, trace
    assert "pattern" not in artifacts, trace
    assert "abstraction" not in artifacts, trace
    assert "algorithm" not in artifacts, trace


def test_general_qa_does_not_reset_tutoring_state():
    """
    Teste estrutural determinístico.

    Quando o aluno faz uma pergunta conceitual durante a tutoria, o grafo
    pode responder conceitualmente, mas não deve apagar o estado do exercício.
    """
    _, final_state, trace = run_scripted_conversation(
        GENERAL_QA_DURING_TUTORING_SCENARIO
    )

    assert final_state.get("is_tutoring_active") is True, trace
    assert final_state.get("current_stage") == "decomposition", trace

    artifacts = final_state.get("student_artifacts", {})
    assert artifacts == {}, trace

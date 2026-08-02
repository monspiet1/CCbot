from deepeval.metrics import GEval
from deepeval.models import GeminiModel
from deepeval.test_case import SingleTurnParams

from llm_factory import DEFAULT_MODEL

gemini_model = GeminiModel(model=DEFAULT_MODEL)

THRESHOLD_SOCRATIC = 0.8
THRESHOLD_SCAFFOLDING = 0.75
THRESHOLD_PROGRESSION = 0.8


def get_socratic_alignment_metric() -> GEval:
    """Métrica 1: Alinhamento Socrático (Socratic Alignment).
    Mede a capacidade do tutor de manter a postura inquisitiva com base na escala de 0 a 5 da UFRJ."""
    return GEval(
        name="Socratic Alignment Metric (Escala UFRJ)",
        criteria="""
        Evaluate if the AI Tutor strictly adheres to the Socratic pedagogical methodology.
        You MUST evaluate the response based on the following 0 to 5 scale of Socratic alignment and assign the corresponding level of adherence.
        """,
        evaluation_steps=[
            "Nota 0 (Nenhum): O tutor dá a resposta diretamente ou o código completo; não faz perguntas.",
            "Nota 1 (Muito baixo): O tutor faz perguntas irrelevantes ou retóricas, mas ainda entrega a solução.",
            "Nota 2 (Baixo): O tutor faz uma pergunta relevante, mas explica parcialmente a solução.",
            "Nota 3 (Moderado): O tutor faz perguntas abertas e dá algumas dicas, estimulando a reflexão.",
            "Nota 4 (Alto): O tutor faz perguntas encadeadas, evita explicações diretas e promove o raciocínio guiado.",
            "Nota 5 (Excelente): O tutor faz apenas perguntas abertas, profundas e encadeadas; não entrega nenhuma resposta direta."
        ],
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
        ],
        threshold=THRESHOLD_SOCRATIC,
        model=gemini_model,
    )


def get_scaffolding_effectiveness_metric() -> GEval:
    """Métrica 2: Eficácia do Andaime Pedagógico (Scaffolding Effectiveness).
    Quando um discente falha em uma etapa e o avaliador emite um 'evaluation_feedback', esta métrica mensura
    se a próxima pergunta formulada pelo Tutor incorporou com precisão a lacuna detectada sem revelar a resposta."""
    return GEval(
        name="Scaffolding Effectiveness Metric",
        criteria="""
        Evaluate the effectiveness of the pedagogical scaffolding provided by the AI Tutor following a student failure:
        1. Analyze the Retrieval Context, which contains the internal evaluation feedback identifying the exact requirements missed by the student.
        2. Verify if the AI Tutor's subsequent response directly targets the conceptual gaps listed in the evaluation feedback.
        3. Ensure that the Tutor reformulated the inquiry or introduced a pedagogical analogy to assist the student in overcoming the obstacle without spoiling the solution.
        """,
        evaluation_steps=[
            "Analyze the Retrieval Context, which contains the internal evaluation feedback identifying the exact requirements missed by the student.",
            "Verify that the Tutor's subsequent response directly targets the conceptual gaps listed in the evaluation feedback.",
            "Confirm the Tutor reformulated the inquiry or introduced a pedagogical analogy without revealing the solution.",
        ],
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.RETRIEVAL_CONTEXT,
        ],
        threshold=THRESHOLD_SCAFFOLDING,
        model=gemini_model,
    )


def get_pedagogical_progression_metric() -> GEval:
    """Métrica 3: Progressão no Pensamento Computacional (CT Progression).
    Avalia a continuidade lógica e a fluidez cognitiva da transição entre os pilares de Decomposição,
    Reconhecimento de Padrões, Abstração e Algoritmos, baseando-se nos artefatos aprovados no Quadro-Negro."""
    return GEval(
        name="Computational Thinking Progression Metric",
        criteria="""
        Evaluate whether the transition to the current Computational Thinking stage is logically sound and pedagogically justified:
        1. Verify if the Tutor accurately builds upon the student's previously consolidated concepts stored in the Blackboard artifacts.
        2. Check if the transition between stages is coherent and naturally triggered by the completion of the prior pillar.
        3. Ensure that no foundational stage of Computational Thinking was skipped or prematurely closed.
        """,
        evaluation_steps=[
            "Verify that the Tutor accurately builds upon the student's previously consolidated concepts stored in the Blackboard artifacts.",
            "Check if the transition between stages is coherent and naturally triggered by the completion of the prior pillar.",
            "Ensure that no foundational stage of Computational Thinking was skipped or prematurely closed.",
        ],
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        threshold=THRESHOLD_PROGRESSION,
        model=gemini_model,
    )


def get_contextual_relevancy_metric() -> GEval:
    """Métrica 4: Relevância Contextual (Contextual Relevancy).
    Substitui a ConversationalRelevancyMetric ausente no DeepEval 4.1.4, avaliando se a resposta do Tutor
    é pertinente ao contexto do Quadro-Negro e ao estágio atual do Pensamento Computacional."""
    return GEval(
        name="Contextual Relevancy Metric",
        criteria="""
        Evaluate whether the AI Tutor's response is contextually relevant to the retrieved pedagogical context:
        1. Verify if the Tutor's response directly addresses the student's input given the current Computational Thinking stage.
        2. Check if the response appropriately leverages the Blackboard artifacts (previously approved concepts) without introducing unrelated topics.
        3. Assess whether the response contains only information that is pertinent to the ongoing tutoring session.
        """,
        evaluation_steps=[
            "Check whether the Tutor's response directly addresses the student's input given the current Computational Thinking stage.",
            "Verify the response appropriately leverages the Blackboard artifacts without introducing unrelated topics.",
            "Assess whether the response contains only information pertinent to the ongoing tutoring session.",
        ],
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.RETRIEVAL_CONTEXT,
        ],
        threshold=0.7,
        model=gemini_model,
    )

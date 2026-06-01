from dataclasses import dataclass


@dataclass(frozen=True)
class EducationalScenario:
    id: str
    scenario: str
    expected_outcome: str
    user_description: str
    user_messages: list[str]


POSITIVE_SCENARIOS = [
    EducationalScenario(
        id="valid_queue_problem_full_flow",
        scenario=(
            "Aluno quer resolver, com pensamento computacional, o problema de "
            "criar a lógica de uma fila de atendimento para uma biblioteca."
        ),
        expected_outcome=(
            "O assistente deve conduzir o aluno pelos quatro pilares, sem entregar "
            "a solução pronta, até que o aluno formule um algoritmo final coerente."
        ),
        user_description=(
            "Aluno iniciante em programação, com noções básicas de lógica e estruturas simples."
        ),
        user_messages=[
            (
                "Quero praticar pensamento computacional. Meu problema é criar a lógica "
                "de um sistema que organize uma fila de atendimento em uma biblioteca."
            ),
            (
                "Objetivo: organizar a ordem de atendimento dos alunos na biblioteca.\n\n"
                "Subtarefa 1: cadastrar chegada do aluno na fila. "
                "Entrada: nome ou matrícula do aluno e horário de chegada. "
                "Saída: aluno inserido no final da fila.\n\n"
                "Subtarefa 2: chamar o próximo aluno. "
                "Entrada: fila atual de alunos. "
                "Saída: primeiro aluno da fila removido e encaminhado ao atendimento.\n\n"
                "Subtarefa 3: verificar se ainda existem alunos aguardando. "
                "Entrada: estado atual da fila. "
                "Saída: informação dizendo se a fila está vazia ou não."
            ),
            (
                "Isso lembra uma fila comum de banco ou lanchonete. "
                "A semelhança é que quem chega primeiro deve ser atendido primeiro. "
                "As tarefas seguem a mesma regra de organização: inserir no final, "
                "remover do começo e repetir enquanto houver pessoas. "
                "A regra geral é FIFO, first-in first-out."
            ),
            (
                "Detalhes irrelevantes: nome da biblioteca, cor da interface, nome do atendente "
                "e decoração do local.\n\n"
                "Variáveis essenciais: lista ou fila de alunos, ordem de chegada, primeiro aluno "
                "da fila e estado vazio ou não vazio da fila.\n\n"
                "Modelo simplificado: manter uma coleção ordenada em que novos alunos entram no "
                "final e o atendimento sempre remove o primeiro elemento."
            ),
            (
                "Algoritmo:\n"
                "1. Criar uma fila inicialmente vazia.\n"
                "2. Quando um aluno chegar, inserir seus dados no final da fila.\n"
                "3. Enquanto a fila não estiver vazia, permitir chamar o próximo aluno.\n"
                "4. Ao chamar, remover o aluno que está no início da fila.\n"
                "5. Encaminhar esse aluno para atendimento.\n"
                "6. Se a fila ficar vazia, informar que não há alunos aguardando.\n"
                "7. Se outro aluno chegar, voltar ao passo 2.\n\n"
                "Condição: se a fila estiver vazia, não chamar ninguém.\n"
                "Repetição: repetir o atendimento enquanto existirem alunos na fila.\n"
                "Fim: o processo termina quando a fila está vazia e não há novo aluno chegando."
            ),
        ],
    )
]


NEGATIVE_DECOMPOSITION_SCENARIO = EducationalScenario(
    id="incomplete_decomposition_should_not_advance",
    scenario=(
        "Aluno inicia uma atividade, mas responde de forma vaga na etapa de decomposição."
    ),
    expected_outcome=(
        "O grafo deve manter o aluno em Decomposição e pedir uma resposta mais completa."
    ),
    user_description="Aluno iniciante que ainda não detalhou subtarefas, entradas e saídas.",
    user_messages=[
        (
            "Quero resolver com pensamento computacional o problema de organizar "
            "uma lista de tarefas de estudo."
        ),
        "Eu dividiria em algumas partes e depois resolveria cada uma.",
    ],
)


GENERAL_QA_DURING_TUTORING_SCENARIO = EducationalScenario(
    id="general_question_during_active_tutoring",
    scenario=(
        "Aluno inicia a tutoria, mas faz uma pergunta conceitual no meio do fluxo."
    ),
    expected_outcome=(
        "O assistente deve responder conceitualmente sem apagar o estado da tutoria."
    ),
    user_description="Aluno iniciante que interrompe a atividade para tirar uma dúvida conceitual.",
    user_messages=[
        (
            "Quero usar pensamento computacional para criar a lógica de uma fila "
            "de atendimento em uma biblioteca."
        ),
        "Antes de continuar, o que é uma fila em programação?",
    ],
)

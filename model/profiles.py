from simulation.schema import StudentProfile


PROFILES = [
    StudentProfile(
        name="Ana - Iniciante Colaborativa",
        knowledge_level="novice",
        error_propensity=0.2,
        impatience_level=0.1,
        communication_style="verboso e entusiasmado",
        domain_problem="Sistema de gerenciamento de fila de banco",
    ),
    StudentProfile(
        name="Carlos - Intermediário Impaciente",
        knowledge_level="intermediate",
        error_propensity=0.3,
        impatience_level=0.7,
        communication_style="direto e às vezes abrupto",
        domain_problem="Algoritmo de ordenação para lista de pacientes",
    ),
    StudentProfile(
        name="Maria - Avançada Concisa",
        knowledge_level="advanced",
        error_propensity=0.1,
        impatience_level=0.2,
        communication_style="técnico e preciso",
        domain_problem="Sistema de cache com política de substituição LRU",
    ),
    StudentProfile(
        name="Pedro - Propenso a Erros Formais",
        knowledge_level="intermediate",
        error_propensity=0.6,
        impatience_level=0.3,
        communication_style="confuso e com dúvidas frequentes",
        domain_problem="Implementação de árvore binária de busca",
    ),
]

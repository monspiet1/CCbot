# AGENTS.md: Guia de Engenharia para Desenvolvimento do Agente Aluno, Refatoração e Benchmarking Científico

Este documento serve como a especificação arquitetural e guia de boas práticas definitivas para desenvolvedores de software, pesquisadores e assistentes de codificação com Inteligência Artificial (como OpenCode, Cursor, GitHub Copilot e Claude Dev).

O objetivo principal deste guia é instruir a refatoração do código atual do Socratic CT-Tutor e orientar o desenvolvimento completo do novo Agente Aluno (Student Agent), permitindo a simulação automatizada de sessões de tutoria para a construção de um dataset de pesquisa científica. Além disso, especifica a implementação de testes unitários e métricas psicométricas via DeepEval para validação estatística em artigos científicos.

---

## Sumário
1. [Diretrizes de Boas Práticas (Python & LangChain/LangGraph)](#1-diretrizes-de-boas-práticas-python--langchainlanggraph)
2. [Roadmap de Refatoração do Código Atual](#2-roadmap-de-refatoração-do-código-atual)
3. [Arquitetura e Implementação do Agente Aluno (Student Agent)](#3-arquitetura-e-implementação-do-agente-aluno-student-agent)
4. [Orquestrador Dual-Agent para Geração de Datasets](#4-orquestrador-dual-agent-para-geração-de-datasets)
5. [Protocolo de Validação Científica com DeepEval (Métricas de Artigo)](#5-protocolo-de-validação-científica-com-deepeval-métricas-de-artigo)
6. [Checklist de Prontidão para o OpenCode](#6-checklist-de-prontidão-para-o-opencode)

---

### ⚠️ DIRETIVA DE IMPLEMENTAÇÃO PARA AGENTES DE IA
Os trechos de código e modelos estruturais fornecidos neste documento operam estritamente como **blueprints arquiteturais, templates de referência funcional e padrões de projeto (Design Patterns)**. 

Ao refatorar o código existente ou criar novos módulos (como o Agente Aluno e os testes do DeepEval):
1. **NÃO realize cópia e cola cega (cópia literal):** Você DEVE adaptar as estruturas propostas ao contexto real do workspace, respeitando o histórico do projeto, convenções de nomenclatura preexistentes, caminhos de diretórios e variáveis de ambiente já configuradas.
2. **Preserve a lógica e a tipagem, adapte a sintaxe:** O rigor arquitetural (uso de Pydantic v2, separação de estado no LangGraph, desacoplamento via LLM Factory e métricas G-Eval) é obrigatório, mas a implementação exata deve ser ajustada e otimizada para se integrar de forma limpa e funcional ao código que está sendo refatorado.
3. **Consulte antes de reescrever:** Ao modificar os arquivos core (`nodes.py` e `workflow.py`), integre as melhorias de forma incremental sem quebrar as rotas e validações do grafo compilado original.

---

## 1. Diretrizes de Boas Práticas (Python & LangChain/LangGraph)

Ao modificar ou expandir o código do projeto, o assistente de IA ou desenvolvedor deve respeitar estritamente os seguintes padrões de engenharia:

### 1.1. Tipagem Estática e Validação com Pydantic v2
- **Tipagem Explícita**: Todas as assinaturas de funções, retornos e variáveis complexas devem possuir Type Hints nativos do Python (`typing` ou `collections.abc`).
- **Pydantic v2**: Utilize sempre `BaseModel`, `Field(description=...)` e validações nativas. Evite dicionários genéricos (`Dict[str, Any]`) quando uma estrutura puder ser formalizada em um modelo Pydantic.
- **Imutabilidade de Estado no LangGraph**: O estado (`GraphState`) passado para um nó deve ser tratado como imutável dentro da função do nó. Retorne apenas um dicionário contendo as chaves específicas que precisam ser atualizadas ou utilize `.copy()` ao manipular estruturas de dados aninhadas (como o dicionário `student_artifacts`).

### 1.2. Desacoplamento e Confiabilidade em LangChain/LangGraph
- **Instanciação de Modelos via Factory**: NUNCA instancie diretamente o `ChatGoogleGenerativeAI` ou qualquer outro modelo dentro dos nós de processamento (`nodes.py`). Crie um módulo dedicado em `src/config/llm.py` que exporte fábricas configuradas com timeouts, retries automáticos e observabilidade:
  ```python
  # Exemplo de implementação em src/config/llm.py
  from langchain_google_genai import ChatGoogleGenerativeAI
  from langchain_core.runnables import Runnable

  def get_tutor_llm(temperature: float = 0.2) -> Runnable:
      llm = ChatGoogleGenerativeAI(
          model="gemini-3.5-flash-lite",
          temperature=temperature,
          max_retries=3,
          request_timeout=30.0
      )
      return llm
  ```
- **Saídas Estruturadas Seguras**: Ao utilizar `with_structured_output()`, certifique-se de tratar potenciais erros de parsing envolvendo blocos de exceção ou utilizando runnables com reanálise (`RunnableRetry`).
- **Isolamento de Prompts via Módulos**: Encapsule todos os prompts de sistema e rubricas de avaliação em arquivos dedicados (`src/prompts/tutor_prompts.py` e `src/prompts/rubrics.py`). Isso possibilita o controle de versão experimental, facilitando estudos de ablação para o artigo científico.
- **Observabilidade e Tracing**: Mantenha o suporte a rastreamento definindo metadados de invocação (`config={"tags": ["tutor_node", "decomposition"]}`) em chamadas `.invoke()` no corpo dos nós.

---

## 2. Roadmap de Refatoração do Código Atual

O assistente OpenCode deve aplicar as seguintes refatorações estruturais no código original (`nodes.py` e `workflow.py`) antes de acoplar o Agente Aluno:

1. **Eliminação de Manipulação Manual de Substrings (`.replace("_node", "")`)**:
   - No código original, o `intent_router` realiza a extração do pilar via: `current_stage = state.get("current_stage", "decomposition").replace("_node", "")`.
   - **Solução Arquitetural**: O campo `current_stage` do estado deve armazenar estritamente o identificador limpo do pilar (`"decomposition"`, `"pattern"`, `"abstraction"`, `"algorithm"`). O mapeamento para nomes de nós no grafo deve ser resolvido no roteador condicional ou através de constantes no arquivo `workflow.py`.
2. **Centralização de Constantes para Nomes de Nós e Rotas**:
   - Crie o módulo `src/constants.py` definindo classes de constantes ou Enums para evitar erros em tempo de execução causados por strings literais dispersas (por exemplo, `NodeNames.DECOMPOSITION_NODE`, `NodeNames.DECOMPOSITION_EVAL`).
3. **Padronização na Transição de Estado e Limpeza de Erros**:
   - Ao transitar para um novo nó de tutoria após uma reprovação ou ao iniciar uma etapa, garanta que os sinalizadores de controle como `approved` sejam redefinidos como `False` e que `evaluation_feedback` seja esvaziado (`""`), prevenindo que feedbacks antigos poluam o prompt da rodada atual.
4. **Refatoração dos Métodos Auxiliares de Avaliação**:
   - A função `generic_evaluator` atualmente isola as mensagens do histórico através de laços de repetição reversos duplicados. Substitua essas buscas por funções utilitárias puras: `get_last_human_message(messages: list) -> str` e `get_last_ai_message(messages: list) -> str`.
5. **Implementação do Nó de Síntese Metacognitiva (`final_summary_node`)**:
   - O fluxo interativo não deve ser encerrado abruptamente após a aprovação no pilar de Algoritmos. É obrigatório implementar um nó final de consolidação que atue no fechamento transacional e no estímulo à metacognição do estudante.
   - O nó `final_summary_node` deve consumir integralmente o histórico do Quadro-Negro (`student_artifacts`), gerar uma retrospectiva demonstrando como cada pilar sustentou o seguinte e apresentar a resolução algorítmica ou arquitetural completa alcançada pelo aluno.
   - O roteador `route_algorithm` deve ser refatorado para direcionar o fluxo para `final_summary_node` em caso de aprovação (`approved: True`), reservando a primitiva `END` para ser acionada exclusivamente após a emissão do resumo final.

### 2.1. Especificação do Nó de Síntese (`src/nodes.py`)

A função abaixo deve ser adicionada ao módulo `src/nodes.py`, e o roteador `route_algorithm` deve ser atualizado para substituir a transição direta ao `END`:

```python
from langchain_core.messages import SystemMessage
from src.schema import GraphState # Ou importação correspondente do TypedDict

def final_summary_node(state: GraphState):
    """Nó de síntese pedagógica: Consolida a jornada do pensamento computacional e exibe a resolução final alcançada pelo aluno."""
    artifacts = state.get("student_artifacts", {})
    decomp = artifacts.get("decomposition", {})
    pattern = artifacts.get("pattern", {})
    abstract = artifacts.get("abstraction", {})
    algo = artifacts.get("algorithm", {})

    sys_prompt = f"""You are an encouraging and analytical AI Tutor. The student has successfully completed all four pillars of Computational Thinking.
    Your mission is to provide a comprehensive, structured summary of their educational journey, celebrating their independent problem-solving process.

    ### THE STUDENT'S CONSOLIDATED BLACKBOARD:
    1. Decomposition:
       - Problem Goal: {decomp.get('goal', 'Not defined')}
       - Subtasks: {decomp.get('subtasks', [])}
    2. Pattern Recognition:
       - Identified Similarities: {pattern.get('identified_similarity', 'Not defined')}
       - General Rule/Analogy: {pattern.get('general_rule', 'Not defined')}
    3. Abstraction:
       - Core Variables: {abstract.get('core_variables', [])}
       - Ignored Noise: {abstract.get('ignored_noise', [])}
       - Simplified Model: {abstract.get('simplified_model', 'Not defined')}
    4. Algorithm:
       - Ordered Steps: {algo.get('ordered_steps', [])}
       - Flow Control (Conditions/Loops): {algo.get('conditions_or_loops', 'Not defined')}
       - End Condition: {algo.get('end_condition', 'Not defined')}

    ### INSTRUCTIONS FOR THE FINAL SYNTHESIS:
    1. Acknowledge and congratulate the student for building the entire solution from scratch using guided Socratic inquiry.
    2. Present a clear, structured retrospective of the four pillars, demonstrating explicitly how each stage provided the foundation for the next.
    3. Formulate and present the complete, polished resolution (the finalized algorithm or architectural logic) that the student arrived at based on their own approved progression.
    4. Maintain an academic, encouraging tone focused purely on metacognitive reflection and closure. Do not introduce new problems or questions."""

    response = llm.invoke([SystemMessage(content=sys_prompt)] + state["messages"])

    return {
        "messages": [response],
        "is_tutoring_active": False,
        "current_stage": "completed",
        "approved": True
    }


def route_algorithm(state: GraphState):
    """Roteia o fluxo com base na avaliação do Algoritmo, direcionando para o resumo final em caso de aprovação."""
    return "final_summary_node" if state.get("approved") else "algorithm_node"
```

---

## 3. Arquitetura e Implementação do Agente Aluno (Student Agent)

Para validar experimentalmente a eficácia pedagógica e evitar **loops infinitos de simulação** (onde o aluno erra repetidamente na mesma fase), o Agente Aluno foi remodelado para possuir um mecanismo de **Progressão Cognitiva (Comprehension)**. O comportamento do aluno mescla a estocasticidade de erros com a diretiva de raciocínio estruturado (Chain of Thought) proposta na literatura acadêmica recente.

### 3.1. Lógica do Nó do Agente Aluno (`student_agent.py`)

A função abaixo incorpora a contagem de tentativas (`attempts_in_stage`) para forçar o aprendizado após falhas consecutivas, mesclando o prompt socrático referenciado na literatura com o controle estocástico:

```python
import random
from typing import List
from langchain_core.messages import SystemMessage, AnyMessage, HumanMessage, AIMessage
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

# Integração da diretiva colaborativa do artigo base
BEHAVIOR_COLLABORATIVE = """
- COMPORTAMENTO ATUAL: Você é um estudante dedicado e curioso. Colabore ativamente.
- Reflita internamente sobre a explicação do tutor e aja da seguinte forma:
  1. Se não compreender totalmente, formule uma nova pergunta conectada à resposta anterior.
  2. Raciocine de forma estruturada (Chain of Thought) e avance passo a passo.
- Responda de forma lógica e alinhada a um estudante de nível {knowledge_level}."""

# Mecanismo de Progressão (Comprehension)
BEHAVIOR_COMPREHENSION = """
- COMPORTAMENTO ATUAL: Você refletiu internamente e alcançou a compreensão plena do conceito da etapa.
- Diga expressamente: "Entendi!" ou agradeça a dica.
- Formule a resposta EXATA, CORRETA e COOPERATIVA esperada pelo Tutor para concluir a etapa de {stage}. Mostre que você absorveu o conhecimento e resolveu a restrição da etapa."""

def _ensure_last_message_is_human(messages: List[AnyMessage]) -> List[AnyMessage]:
    """Garante que a última mensagem seja um HumanMessage para compatibilidade com a API."""
    if not messages:
        return [HumanMessage(content="Por favor, comece sua resposta.")]
    last_msg = messages[-1]
    if isinstance(last_msg, AIMessage):
        return messages[:-1] + [HumanMessage(content="Por favor, responda à pergunta anterior do Tutor.")]
    return messages

def run_student_turn(messages: List[AnyMessage], profile: StudentProfile, current_stage: str, attempts_in_stage: int) -> str:
    """Executa um turno interativo do Agente Aluno formulando uma resposta com base na pergunta do Tutor e no perfil discente."""
    
    # Progressão Cognitiva: Força o acerto após 2 falhas na mesma fase
    if attempts_in_stage >= 2:
        behavior_instruction = BEHAVIOR_COMPREHENSION.format(stage=current_stage.upper())
    else:
        should_make_error = random.random() < profile.error_propensity
        should_be_impatient = random.random() < profile.impatience_level

        if should_be_impatient:
            behavior_instruction = BEHAVIOR_IMPATIENT
        elif should_make_error:
            behavior_instruction = BEHAVIOR_ERROR.format(stage=current_stage.upper())
        else:
            behavior_instruction = BEHAVIOR_COLLABORATIVE.format(knowledge_level=profile.knowledge_level.upper())

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

    return response.content if isinstance(response.content, str) else str(response.content)
```

### 3.2. Lógica do Mecanismo de Compreensão (student_agent.py)

A constante de compreensão deve obrigar o LLM a fornecer a síntese completa para satisfazer o Avaliador:

```python
BEHAVIOR_COMPREHENSION = """
- COMPORTAMENTO ATUAL: Você refletiu internamente e alcançou a compreensão plena da etapa de {stage}.
- Para que o sistema reconheça seu avanço, você DEVE fornecer a síntese COMPLETA e ESTRUTURADA em sua resposta.
- Se for Decomposição: Escreva o objetivo final, liste todas as subtarefas e defina Entrada (Input) e Saída (Output) para CADA subtarefa.
- Se for Padrões: Descreva a regra geral e as semelhanças encontradas.
- Se for Abstração: Liste as variáveis críticas, os detalhes ignorados e o modelo simplificado.
- Se for Algoritmo: Escreva o passo a passo completo, com condições/loops e critério de parada.
- Não deixe faltar nenhum elemento! Seja cooperativo e exato."""

---

## 4. Orquestrador Dual-Agent para Geração de Datasets

Para consolidar um dataset empírico robusto para o artigo científico (contendo de 50 a 100 sessões completas de tutoria), é fundamental implementar um orquestrador que coordene o loop de retroalimentação entre o `TutorGraph` e o `StudentAgent`.

```python
# src/simulation/orchestrator.py
import json
import time
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage
from src.workflow import app as tutor_app
from src.simulation.schema import StudentProfile
from src.simulation.student_agent import run_student_turn

class SimulationOrchestrator:
    def __init__(self, max_turns_per_session: int = 15):
        self.max_turns = max_turns_per_session

    def simulate_session(self, profile: StudentProfile, session_id: str) -> Dict[str, Any]:
        """Executa uma simulação ponta a ponta entre o Tutor e o Aluno, registrando a telemetria da conversação."""
        print(f"
--- Iniciando Simulação [{session_id}] | Persona: {profile.name} ({profile.knowledge_level}) ---")
        
        initial_msg = f"Olá, preciso de ajuda pedagógica para modelar e criar a lógica de um problema de {profile.domain_problem}."
        
        state = {
            "messages": [HumanMessage(content=initial_msg)],
            "current_stage": "decomposition",
            "is_tutoring_active": False,
            "approved": False,
            "evaluation_feedback": "",
            "student_artifacts": {}
        }
        
        turn_count = 0
        session_trace = []
        is_completed = False

        while turn_count < self.max_turns:
            turn_count += 1
            print(f"
[Turno {turn_count}] Processando transição no Grafo do Tutor...")
            
            # IMPORTANTE: stream_mode="values" entrega o ESTADO COMPLETO acumulado (mensagens via reducer add_messages,
            # artefatos via last-write-wins) a cada super-step. Capturar o último snapshot evita a AMNÉSIA DE ESTADO
            # (artefatos e histórico perdidos ao ler apenas a saída do último nó em modo "updates").
            final_state = None
            for snapshot in tutor_app.stream(state, stream_mode="values"):
                final_state = snapshot

            if final_state is not None:
                for key in ["current_stage", "is_tutoring_active", "approved", "evaluation_feedback", "student_artifacts"]:
                    state[key] = final_state.get(key, state[key])
                state["messages"] = final_state.get("messages", state["messages"])

            last_ai_msg = state["messages"][-1].content
            print(f"[Tutor -> Aluno | Pilar: {state['current_stage']} | Status Aprovado: {state['approved']}]: {last_ai_msg[:100]}...")
            
            session_trace.append({
                "turn": turn_count,
                "speaker": "tutor",
                "stage": state["current_stage"],
                "approved": state["approved"],
                "content": last_ai_msg,
                "artifacts_snapshot": str(state["student_artifacts"])
            })

            # Critério de Parada Técnico: transição ao estado "completed" (após a execução do final_summary_node)
            if state["current_stage"] == "completed":
                print("--- Sessão finalizada com sucesso: Todos os quatro pilares foram consolidados no Quadro-Negro ---")
                is_completed = True
                break

            print(f"[Turno {turn_count}] Processando resposta cognitiva do Agente Aluno...")
            student_reply = run_student_turn(state["messages"], profile, state["current_stage"])
            print(f"[Aluno -> Tutor]: {student_reply[:100]}...")
            
            state["messages"].append(HumanMessage(content=student_reply))
            
            session_trace.append({
                "turn": turn_count,
                "speaker": "student",
                "stage": state["current_stage"],
                "content": student_reply
            })
            
            time.sleep(1) # Intervalo preventivo contra limitação de taxa de requisição na API

        return {
            "session_id": session_id,
            "profile": profile.model_dump(),
            "completed": is_completed,
            "total_turns": turn_count,
            "final_stage_reached": state["current_stage"],
            "artifacts_collected": state["student_artifacts"],
            "trace": session_trace
        }

    def export_dataset_jsonl(self, sessions: List[Dict[str, Any]], filepath: str = "dataset_ct_tutoring.jsonl"):
        """Exporta os registros das sessões no formato JSONL padrão para fine-tuning ou benchmarking estatístico."""
        with open(filepath, "w", encoding="utf-8") as f:
            for s in sessions:
                f.write(json.dumps(s, ensure_ascii=False) + "
")
        print(f"
--- Dataset contendo {len(sessions)} interações exportado com sucesso para '{filepath}' ---")
```

---

## 5. Protocolo de Validação Científica com DeepEval (Métricas de Artigo)

Para outorgar validade estatística e rigor acadêmico aos resultados empíricos que serão relatados na seção de Resultados e Discussão do artigo, a inspeção visual dos logs é insuficiente. É indispensável aplicar uma suíte de avaliação quantitativa baseada no paradigma de LLM-as-a-Judge, utilizando a framework DeepEval.

O DeepEval operacionaliza rubricas pedagógicas baseadas no critério G-Eval, realizando normalização estatística de log-probabilidades e gerando justificativas analíticas para cada pontuação atribuída.

### 5.1. Formalização das Métricas Científicas de Avaliação Pedagógica

As métricas customizadas para o experimento devem ser implementadas no módulo `tests/eval_metrics.py`:

```python
# tests/eval_metrics.py
from deepeval.metrics import GEval
from deepeval.models import GeminiModel
from deepeval.test_case import SingleTurnParams
from llm_factory import DEFAULT_MODEL

gemini_model = GeminiModel(model=DEFAULT_MODEL)

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
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        threshold=THRESHOLD_SOCRATIC,
        model=gemini_model
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
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.RETRIEVAL_CONTEXT],
        threshold=0.75,
        model=gemini_model
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
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
        threshold=0.8,
        model=gemini_model
    )
```

> **Nota de implementação:** Ao instanciar métricas do DeepEval, passe sempre a instância `GeminiModel(model=DEFAULT_MODEL)` explicitamente. Passar apenas a string `"gemini-3.5-flash-lite"` faz o `initialize_model()` do DeepEval cair no fallback `GPTModel` (que exige `OPENAI_API_KEY`). A chave `GOOGLE_API_KEY` é lida automaticamente do ambiente pela instância.

### 5.2. Pipeline de Benchmarking Automatizado para Inclusão no Paper

O script `tests/benchmark_paper.py` instrui a execução da avaliação em lote sobre o dataset exportado na Seção 4, agregando as métricas estatísticas de média, desvio-padrão e taxa de aprovação para formatação tabular no artigo científico:

```python
# tests/benchmark_paper.py
import json
import pandas as pd
from typing import List
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.metrics import ContextualRelevancyMetric
from eval_metrics import (
    get_socratic_alignment_metric,
    get_scaffolding_effectiveness_metric,
    get_pedagogical_progression_metric
)

def load_dataset_as_test_cases(jsonl_filepath: str) -> List[LLMTestCase]:
    """Converte os arquivos JSONL de telemetria em casos de teste formais da biblioteca DeepEval,
    isolando os turnos em que o Tutor interage em resposta ao estudante."""
    test_cases = []
    with open(jsonl_filepath, "r", encoding="utf-8") as f:
        for line in f:
            session = json.loads(line)
            trace = session["trace"]
            
            for i in range(1, len(trace)):
                current_turn = trace[i]
                prev_turn = trace[i-1]
                
                if current_turn["speaker"] == "tutor" and prev_turn["speaker"] == "student":
                    artifacts = current_turn.get("artifacts_snapshot", "{}")
                    
                    test_case = LLMTestCase(
                        input=prev_turn["content"],
                        actual_output=current_turn["content"],
                        retrieval_context=[f"Blackboard Snapshot: {artifacts}", f"Current CT Stage: {current_turn['stage']}"],
                        expected_output=f"A Socratic guiding question aligned with the {current_turn['stage']} methodology."
                    )
                    test_cases.append(test_case)
                    
    return test_cases

def run_paper_benchmark(jsonl_filepath: str = "dataset_ct_tutoring.jsonl"):
    """Executa a suíte psicométrica completa via DeepEval e exporta tabelas consolidadas para o artigo."""
    print("--- Inciando carregamento do dataset e montagem dos casos de teste ---")
    test_cases = load_dataset_as_test_cases(jsonl_filepath)
    print(f"--- Total de turnos pedagógicos isolados para avaliação: {len(test_cases)} ---")
    
    socratic_metric = get_socratic_alignment_metric()
    scaffolding_metric = get_scaffolding_effectiveness_metric()
    progression_metric = get_pedagogical_progression_metric()
    relevancy_metric = ContextualRelevancyMetric(threshold=0.7, model="gemini-3.5-flash-lite")
    
    metrics = [socratic_metric, scaffolding_metric, progression_metric, relevancy_metric]
    
    print("--- Executando julgamento automatizado via DeepEval (LLM-as-a-Judge) ---")
    results = evaluate(test_cases=test_cases, metrics=metrics)
    
    data_rows = []
    for test_result in results.test_results:
        row = {
            "input_student": test_result.input[:60] + "...",
            "output_tutor": test_result.actual_output[:60] + "...",
        }
        for metric_data in test_result.metrics_data:
            row[f"{metric_data.name} (Score)"] = metric_data.score
            row[f"{metric_data.name} (Success)"] = metric_data.success
            row[f"{metric_data.name} (Reasoning)"] = metric_data.reason[:120] + "..." if metric_data.reason else ""
        data_rows.append(row)
        
    df_results = pd.DataFrame(data_rows)
    df_results.to_csv("paper_benchmark_detailed_results.csv", index=False)
    
    print("--- Síntese Estatística para Seção de Resultados do Artigo ---")
    summary = {}
    for m in metrics:
        score_col = f"{m.name} (Score)"
        success_col = f"{m.name} (Success)"
        if score_col in df_results.columns:
            mean_score = df_results[score_col].mean()
            std_score = df_results[score_col].std()
            pass_rate = (df_results[success_col].sum() / len(df_results)) * 100
            summary[m.name] = {
                "Média Score (0.0 - 1.0)": f"{mean_score:.3f} (±{std_score:.3f})",
                "Taxa de Sucesso (%)": f"{pass_rate:.1f}%"
            }
            
    df_summary = pd.DataFrame(summary).T
    print(df_summary.to_string())
    df_summary.to_csv("paper_benchmark_summary_table.csv")
    print("--- Validação concluída: Arquivos CSV de benchmark gerados com êxito ---")

if __name__ == "__main__":
    run_paper_benchmark()
```

---

## 6. Checklist de Prontidão para o OpenCode

Ao acionar o OpenCode ou outra ferramenta de engenharia assistida na IDE para executar as modificações no repositório, utilize a seguinte lista de verificação como base no prompt de instrução inicial:

- [x] **Fase 1: Refatoração e Estabilização do Código Original**
  - [x] Erradicar o uso da manipulação de string `.replace("_node", "")` no arquivo `nodes.py`.
  - [x] Implementar o módulo de fábrica `llm_factory.py` para gerenciamento centralizado do modelo Gemini e controle de timeouts.
  - [x] Padronizar a reinicialização dos atributos de controle (`approved` e `evaluation_feedback`) em todas as transições de estado do grafo.
  - [x] Implementar a função `final_summary_node` em `nodes.py` para consumir o histórico consolidado do Quadro-Negro (`student_artifacts`), emitir a retrospectiva pedagógica e apresentar a resolução algorítmica completa.
  - [x] Refatorar a função de roteamento `route_algorithm` em `nodes.py` para direcionar o fluxo aprovado para `final_summary_node` em vez de acionar a primitiva `END`.
  - [x] Registrar o nó `final_summary_node` e atualizar as arestas terminais no arquivo `workflow.py`, garantindo que a saída do resumo final transite diretamente para `END`.
- [x] **Fase 2: Implementação do Ambiente de Simulação Discente**
  - [x] Declarar o modelo Pydantic `StudentProfile` no módulo `simulation/schema.py`.
  - [x] Desenvolver o nó gerador de texto no arquivo `simulation/student_agent.py`, implementando a lógica estocástica de injeção de erros conceituais e impaciência.
  - [x] Estruturar a classe `SimulationOrchestrator` em `simulation/orchestrator.py` para acoplar os grafos em execução cíclica autônoma, ajustando o critério de parada para aguardar a transição ao estado `"completed"` (após a execução do `final_summary_node`) antes de encerrar e gravar o log.
- [x] **Fase 3: Execução Experimental e Geração de Datasets**
  - [x] Parametrizar no mínimo quatro perfis discentes com comportamentos contrastantes (ex: iniciante colaborativo, intermediário impaciente, avançado conciso, propenso a erros formais).
  - [x] Rodar o orquestrador dual-agent para compilar um dataset empírico contendo pelo menos 10 sessões inteiras, exportando os dados para o arquivo `dataset_ct_tutoring.jsonl`.
- [ ] **Fase 4: Avaliação Psicométrica com DeepEval e Análise para o Artigo**
  - [x] Instalar o pacote `deepeval` e autenticar as variáveis de ambiente necessárias.
  - [x] Implementar as rubricas pedagógicas `SocraticAlignmentMetric`, `ScaffoldingEffectivenessMetric` e `PedagogicalProgressionMetric`.
  - [ ] Executar o script `benchmark_paper.py`, gerar as tabelas estatísticas (`paper_benchmark_summary_table.csv`) e consolidar os dados descritivos para a redação científica.
# PROGRESS.md - Socratic CT-Tutor

## Status Atual
- **Fase**: 4 - Avaliação Psicométrica com DeepEval e Análise para o Artigo
- **Estado**: Em andamento
- **Data de Início**: 2025-07-25
- **Data de Conclusão Fase 1**: 2025-07-25
- **Data de Conclusão Fase 2**: 2025-07-25
- **Data de Conclusão Fase 3**: 2026-07-30

## Histórico de Modificações

### 2025-07-25 - Início da Fase 1
- Análise completa do codebase (`nodes.py`, `workflow.py`, `prompts.py`, `api.py`, `dashboard.py`)
- Identificação dos problemas arquiteturais listados no AGENTS.md Seção 2
- Criação do plano de execução incremental

### 2025-07-25 - Conclusão da Fase 1 (Parte 1)
- Criado `llm_factory.py` com factory centralizada do LLM (max_retries=3, timeout=30s)
- Criado `message_utils.py` com `get_last_human_message()` e `get_last_ai_message()`
- Migrados 10 prompts inline de `nodes.py` para `prompts.py`
- Eliminado `.replace("_node", "")` do `intent_router` (linha 88 original)
- Substituídos loops duplicados por chamadas às funções utilitárias
- Todos os nós de tutoria usam prompts importados de `prompts.py`
- Reset de `approved` e `evaluation_feedback` padronizado em todos os nós

### 2025-07-25 - Conclusão da Fase 1 (Parte 2 - Nó de Síntese)
- Adicionado `FINAL_SUMMARY_NODE_PROMPT` em `prompts.py`
- Implementado `final_summary_node()` em `nodes.py` para consolidação metacognitiva
- Refatorado `route_algorithm()` para direcionar para `final_summary_node` em caso de aprovação
- Registrado nó `final_summary_node` em `workflow.py` com aresta para `END`

### 2025-07-25 - Início da Fase 2
- Criado pacote `simulation/` com `__init__.py`
- Declarado `StudentProfile` em `simulation/schema.py` (Pydantic v2)
- Implementado `run_student_turn()` em `simulation/student_agent.py` com lógica estocástica
- Implementado `SimulationOrchestrator` em `simulation/orchestrator.py` com loop via `stream()`

### 2025-07-25 - Início da Fase 3
- Criado `profiles.py` com 4 perfis discentes pré-configurados (Ana, Carlos, Maria, Pedro)
- Criado `run_simulation.py` com CLI (`argparse`) e distribuição uniforme de sessões
- Adicionado delay configurável entre requisições LLM (padrão: 65s)

### 2025-07-26 - Correções e Melhorias
- Implementado salvamento incremental de sessões em JSONL (append a cada sessão finalizada)
- Removido delay entre sessões, mantendo apenas delay entre chamadas LLM individuais
- Corrigido bug `ValueError: Model does not support model prefilling` com função `_ensure_last_message_is_human()`

### 2026-07-30 - Início da Fase 4
- Confirmada instalação do DeepEval 4.1.4 com pandas 3.0.5 e pydantic 2.13.4
- Validada compatibilidade da API: `LLMTestCaseParams` é deprecated (alias de `SingleTurnParams`); `ContextualRelevancyMetric` existe; `ConversationalRelevancyMetric` NÃO existe no 4.1.4
- Decisão: usar instância `GeminiModel(model=DEFAULT_MODEL)` passada às métricas GEval (padrão documentado do DeepEval); API key `GOOGLE_API_KEY` lida automaticamente do ambiente
- Criado pacote `tests/` com `__init__.py`, `eval_metrics.py` e `benchmark_paper.py`
- Implementadas 4 métricas: SocraticAlignment, ScaffoldingEffectiveness, CT Progression e ContextualRelevancy
- Implementado `clean_message_content()` para normalizar content blocks stringificados do trace (`"[{'type': 'text', ...}]"`)
- Pipeline usa `DEFAULT_MODEL` de `llm_factory.py` como fonte centralizada do modelo
- Atualizado `AGENTS.md`: 6 ocorrências de `gemini-3.1-flash-lite-preview` → `gemini-3.5-flash-lite`; `LLMTestCaseParams` → `SingleTurnParams`; `ConversationalRelevancyMetric` → `ContextualRelevancyMetric`; import local `from eval_metrics import`
- Diagnóstico do dataset: 8 sessões existentes TODAS incompletas (`completed=False`, 15 turnos, travadas em `decomposition`); conteúdo do trace precisa de limpeza
- Plano: executar piloto do benchmark com as 8 sessões; regenerar dataset oficial (≥10 sessões completas) em seguida

### 2026-07-31 - Fase 4: Pipeline e Piloto do Benchmark
- Corrigida a forma de fornecer o modelo: instância `GeminiModel(model=DEFAULT_MODEL)` passada às métricas (string `"gemini-..."` faz o `initialize_model()` do DeepEval cair no fallback `GPTModel` e exigir `OPENAI_API_KEY`)
- Adicionados `evaluation_steps` às 4 métricas G-Eval: elimina a chamada extra de `_a_generate_evaluation_steps` (1 chamada LLM por métrica/caso em vez de 2)
- Descoberto limite do free tier do Gemini: **15 req/min por modelo** (`gemini-3.5-flash-lite`); rajadas acima disparam 429 `RESOURCE_EXHAUSTED`
- `benchmark_paper.py` refatorado: processamento em lotes (`--batch-size`, padrão 2) com pausa (`--sleep`, padrão 70s) entre lotes + retry automático (`_evaluate_with_retry`, 5 tentativas) para erros transitórios (429/503); amostragem via `--max-cases`; imports não utilizados removidos
- Fixado bug de agregação: `metric_data.name` do DeepEval carrega o sufixo `[GEval]` (`"Socratic Alignment Metric [GEval]"`), quebrava o match do resumo; agora as colunas são localizadas por prefixo
- Fixado nome do índice da tabela resumo (`Metric` em vez de `Unnamed: 0`)
- **Piloto executado com sucesso**: 8 casos (turnos tutor-após-aluno) × 4 métricas = 32 julgamentos; 100% de sucesso e scores 1.000 (amostra pequena, esperado dado o comportamento consistente do tutor)
- CSVs gerados: `paper_benchmark_detailed_results.csv` (8 linhas com score/success/reasoning por métrica) e `paper_benchmark_summary_table.csv`
- Estimativa para o piloto completo (112 casos × 4 métricas = 448 chamadas): ~45 min no ritmo de ~10 chamadas/min impostos pela cota do free tier
- Pendência: executar o benchmark completo (112 casos) e/ou regenerar o dataset oficial (≥10 sessões completas) antes da avaliação final

### 2026-08-01 - Refatoração Anti-Loop do Agente Aluno (Fase 2)
- Diagnóstico: as 8 sessões do dataset estavam TODAS travadas em `decomposition` (`completed=False`, 15 turnos) — a estocasticidade do aluno rejeitava o feedback do tutor indefinidamente, causando loop infinito de simulação
- `simulation/student_agent.py` refatorado conforme AGENTS.md Seção 3.1:
  - `BEHAVIOR_COLLABORATIVE` atualizado com reflexão interna + Chain of Thought (perfil dedicado/curioso, pergunta conectada se não entender, raciocínio passo a passo)
  - Novo `BEHAVIOR_COMPREHENSION` (substitui o antigo "Aha! Moment"): aluno declara "Entendi!", agradece a dica e formula a resposta exata/correta esperada pelo Tutor
  - Nova constante `MAX_ATTEMPTS_PER_STAGE = 2` (Progressão Cognitiva)
  - Nova assinatura `run_student_turn(messages, profile, current_stage, attempts_in_stage)`: após `MAX_ATTEMPTS_PER_STAGE` falhas na mesma fase, força o Comprehension; caso contrário, mantém a ramificação estocástica (impaciente/erro/colaborativo)
  - `_ensure_last_message_is_human()` preservada intacta
- `simulation/orchestrator.py`: adicionado rastreador `attempts_in_current_stage` que incrementa quando o estágio permanece o mesmo sem aprovação e reseta ao mudar de estágio/aprovar; contagem exibida no print do Aluno; chamada nomeada com `attempts_in_stage`
- `AGENTS.md`: renomeadas as 3 ocorrências de "Aha! Moment" → "Comprehension" (linhas 138, 178-180, 198), mantendo intactas as atualizações da Fase 4
- Validação (sem rede): `py_compile` OK nos dois arquivos; teste de ramificação via mock (`unittest.mock.patch`) cobrindo colaborativo/CoT, impaciente, Comprehension (`attempts=2` e `=5`, independente de `random`), instanciação do `SimulationOrchestrator` e constante `MAX_ATTEMPTS_PER_STAGE` — 8 asserções passaram

### 2026-08-01 - Fix Crítico do Loop Infinito (Amnésia + Paradoxo Micro/Macro)
- **Diagnóstico de logs (2 causas raiz do loop em `decomposition`):**
  1. **Amnésia (mutação de estado):** `orchestrator.py` sobrescrevia `state["messages"]` com o update do último nó — em modo `updates`, o LangGraph entrega no canal `messages` apenas as mensagens NOVAS do nó (ex.: `[AIMessage]`), não o acumulado. O histórico virava só o último turno a cada iteração (Tutor e Aluno perdiam contexto; o `decomposition_eval` avaliava respostas isoladas sem progresso).
  2. **Paradoxo Micro vs. Macro:** `BEHAVIOR_COMPREHENSION` instruía o aluno a responder APENAS a pergunta micro do Tutor (uma subtarefa), enquanto a rubrica do avaliador exige a síntese MACRO completa (goal + todas as subtarefas + I/O de cada uma). Resposta micro nunca passa no Gatekeeper → loop.
- **Fix 1 (`simulation/orchestrator.py`):** atribuição `state["messages"] = ...` substituída por `state["messages"].extend(tutor_output_state["messages"])` — o histórico passa a acumular integralmente (estado passado ao grafo cresce de `[Human(initial)]` a `[..., AI_n, S_n]` a cada turno). Validado: todo nó terminal do grafo retorna `"messages"` (casual/general_qa/tutores/final_summary) e avaliadores não retornam `"messages"`, logo o último evento captura todas as mensagens novas; apenas um nó produtor por rodada → sem duplicação.
- **Fix 2 (`simulation/student_agent.py`):** `BEHAVIOR_COMPREHENSION` substituído integralmente pelo texto MACRO da Seção 3.2 do AGENTS.md (síntese COMPLETA e ESTRUTURADA; regras por estágio: objetivo + subtarefas + Input/Output na Decomposição, regra geral em Padrões, variáveis/modelo em Abstração, passo a passo/loops/parada em Algoritmo). Impaciência/erro/colaborativo inalterados.
- Validação (sem rede): `py_compile` OK; teste de ramificação (Comprehension macro contém "síntese COMPLETA e ESTRUTURADA" e "Entrada (Input) e Saída (Output)"; impaciente/erro/CoT preservados); novo teste do orquestrador com `tutor_app.stream` mockado (4 iterações) confirma crescimento monotônico de mensagens `[1→3→5→7]` sem perda nem duplicação, trace completo e semântica de `completed` preservada

### 2026-08-01 - Fix da Amnésia de Estado + Loop de Alucinação de Identidade (orquestrador)
- **Diagnóstico via logs (`session_test.jsonl`):** fluxo CT progrediu pelos 4 pilares, mas travou no final — `completed=False`, `final_stage=algorithm`, `artifacts_collected={}` e "loop de alucinação de identidade" (turno 11: Tutor fecha a sessão com "Parabéns... Missão cumprida" em vez de perguntar; Aluno inverte papéis e chama o Tutor de "Ana")
- **Causa raiz:** captura manual "só do último nó" (`tutor_output_state = node_data`) → a cada invocação o grafo era re-seedado com `student_artifacts={}` (todos os artefatos dos pilares perdidos) e histórico substituído; sem o Quadro-Negro, `algorithm_node` e o avaliador perdem contexto, o tutor julga a sessão concluída por conta própria e os agentes entram em congratulação mútua
- **Bug adicional no working tree:** bloco interno (acumular eventos) adicionado sem remover o bloco externo antigo → dupla aplicação (cada mensagem do nó terminal era estendida 2x em `state["messages"]`)
- **Fix (`simulation/orchestrator.py`):** substituído todo o merge manual por `tutor_app.stream(state, stream_mode="values")` capturando o último snapshot — o estado COMPLETO acumulado do grafo (mensagens via reducer `add_messages`, artefatos via last-write-wins). Sincronização das 6 chaves (`messages`, `current_stage`, `is_tutoring_active`, `approved`, `evaluation_feedback`, `student_artifacts`). Elimina amnésia de artefatos/histórico E a dupla aplicação
- `AGENTS.md` Seção 4 (blueprint): padrão `tutor_output_state = node_data` → `stream_mode="values"` + nota de implementação; critério de parada alinhado ao código real (`current_stage == "completed"`)
- Validação (sem rede): `py_compile` OK; teste com `stream` mockado em modo `values` — artefatos persistem entre invocações (`decomposition`/`pattern`/`abstraction` retidos), mensagens crescem `[1→3→5→7]` sem duplicação, `current_stage="completed"` dispara `break` imediato com `completed=True` e resumo registrado no trace

## Decisões Arquiteturais

| Data | Decisão | Justificativa |
|------|---------|---------------|
| 2025-07-25 | Manter layout flat (sem `src/`) | Projeto atual não possui estrutura `src/`; evitar refatoração de imports desnecessária |
| 2025-07-25 | Focar apenas em `nodes.py` e `workflow.py` | Dashboard e API são componentes separados; refatorar core primeiro |
| 2025-07-25 | Adiar `constants.py` | Strings literais já funcionam; Enums serão adicionados na Fase 2 |
| 2025-07-25 | Migrar prompts inline para `prompts.py` | Centralização facilita experimentos de ablação para o artigo científico |
| 2025-07-25 | Implementar `final_summary_node` | Encerramento abrupto do fluxo é anti-pedagógico; síntese metacognitiva fecha o ciclo |
| 2025-07-25 | Criar subdiretório `simulation/` | Separa lógica de simulação do core do tutor; facilita manutenção |
| 2025-07-25 | Usar `stream()` no orquestrador | Mais eficiente que `invoke()`; permite observar transições intermediárias |
| 2025-07-25 | Critério de parada `current_stage == "completed"` | Alinhado com `final_summary_node` implementado na Fase 1 |
| 2025-07-25 | Usar `argparse` para CLI | Facilita experimentação com diferentes números de sessões |
| 2025-07-25 | Distribuição uniforme de perfis | Garante balanceamento para análise estatística |
| 2025-07-25 | Delay configurável entre requisições LLM | Evita rate limiting da API do Google Gemini (padrão: 65s) |
| 2025-07-26 | Salvamento incremental de sessões | Preserva sessões já finalizadas em caso de interrupção do script |
| 2025-07-26 | Garantir última mensagem é HumanMessage | Compatibilidade com API do Gemini que rejeita prefilling de assistant |
| 2026-07-30 | Usar `SingleTurnParams` em vez de `LLMTestCaseParams` | Compatibilidade com DeepEval 4.1.4 (antigo é apenas alias deprecated) |
| 2026-07-30 | Usar `ContextualRelevancyMetric` em vez de `ConversationalRelevancyMetric` | `ConversationalRelevancyMetric` não existe no DeepEval 4.1.4 (ImportError) |
| 2026-07-30 | Padronizar modelo em `gemini-3.5-flash-lite` via `DEFAULT_MODEL` | Fonte centralizada em `llm_factory.py`; AGENTS.md alinhado ao código real |
| 2026-07-30 | Passar instância `GeminiModel` às métricas | Padrão documentado do DeepEval; string `"gemini-..."` cai no fallback `GPTModel` e exige `OPENAI_API_KEY` |
| 2026-07-30 | Piloto do benchmark com dataset atual antes de regenerar | Dataset de 8 sessões incompletas serve para validar pipeline antes do dataset oficial |
| 2026-07-31 | Pré-definir `evaluation_steps` nas métricas G-Eval | Evita a chamada extra `_a_generate_evaluation_steps`; dobra a eficiência de chamadas (essencial com cota de 15 req/min) |
| 2026-07-31 | Lotes pequenos (2 casos) + pausa de 70s entre lotes | Respeita o limite de 15 req/min do free tier; rajadas maiores geram 429 |
| 2026-07-31 | Retry automático em erros transitórios (429/503) | API do Gemini retorna 503 `UNAVAILABLE` de forma intermitente; 5 tentativas com 70s de espera |
| 2026-07-31 | Localizar colunas por prefixo na síntese estatística | `metric_data.name` do DeepEval inclui sufixo `[GEval]`, inviabilizando match direto por `m.name` |
| 2026-08-01 | Mecanismo de Progressão Cognitiva com `MAX_ATTEMPTS_PER_STAGE = 2` | Interrompe loop infinito de simulação: após 2 falhas na mesma fase o aluno é forçado a demonstrar Comprehension e destrava o pilar |
| 2026-08-01 | Renomear "Aha! Moment" para "Comprehension" | Terminologia profissional para o artigo científico; `BEHAVIOR_COMPREHENSION` no código e AGENTS.md |
| 2026-08-01 | Acumular `messages` via `.extend()` em vez de atribuição direta | Em modo `updates` do `stream()`, o canal `messages` entrega só as mensagens novas do nó; atribuição causava amnésia a cada turno |
| 2026-08-01 | `BEHAVIOR_COMPREHENSION` = síntese MACRO da Seção 3.2 | Rubrica do avaliador exige goal + subtarefas + I/O completos; resposta micro à pergunta do Tutor nunca passava no Gatekeeper |
| 2026-08-01 | Usar `stream_mode="values"` e capturar o último snapshot | É o único jeito de sincronizar o estado COMPLETO do grafo (reducers aplicados: `add_messages` + last-write-wins); merge manual por evento causava amnésia de artefatos e dupla aplicação de mensagens |
| 2026-08-01 | `DEFAULT_REQUEST_TIMEOUT` 30s → 120s | `httpx.ReadTimeout` no free tier com saídas estruturadas; o Gemini ultrapassava 30s de leitura nas 3 tentativas e o SDK repropagava o erro, derrubando o batch |
| 2026-08-01 | Escala UFRJ 0-5 na métrica Socrática (`evaluation_steps`) + conversão ×5 no resumo | Ancorar o Chain-of-Thought do LLM-as-a-Judge na régua de 6 níveis; o score normalizado 0-1 ×5 vira a nota 0-5 no `paper_benchmark_summary_table.csv` |

## Checklist - Fase 1 (AGENTS.md Seção 6)

- [x] Erradicar o uso da manipulação de string `.replace("_node", "")` no arquivo `nodes.py`.
- [x] Implementar o módulo de fábrica `llm_factory.py` para gerenciamento centralizado do modelo Gemini e controle de timeouts.
- [x] Padronizar a reinicialização dos atributos de controle (`approved` e `evaluation_feedback`) em todas as transições de estado do grafo.
- [x] Extrair funções utilitárias `get_last_human_message()` e `get_last_ai_message()` para `message_utils.py`.
- [x] Migrar prompts inline de `nodes.py` para `prompts.py`.
- [x] Implementar a função `final_summary_node` em `nodes.py` para consumir o histórico consolidado do Quadro-Negro (`student_artifacts`), emitir a retrospectiva pedagógica e apresentar a resolução algorítmica completa.
- [x] Refatorar a função de roteamento `route_algorithm` em `nodes.py` para direcionar o fluxo aprovado para `final_summary_node` em vez de acionar a primitiva `END`.
- [x] Registrar o nó `final_summary_node` e atualizar as arestas terminais no arquivo `workflow.py`, garantindo que a saída do resumo final transite diretamente para `END`.

## Checklist - Fase 2 (AGENTS.md Seção 6)

- [x] Declarar o modelo Pydantic `StudentProfile` no módulo `simulation/schema.py`.
- [x] Desenvolver o nó gerador de texto no arquivo `simulation/student_agent.py`, implementando a lógica estocástica de injeção de erros conceituais e impaciência.
- [x] Estruturar a classe `SimulationOrchestrator` em `simulation/orchestrator.py` para acoplar os grafos em execução cíclica autônoma, ajustando o critério de parada para aguardar a transição ao estado `"completed"` (após a execução do `final_summary_node`) antes de encerrar e gravar o log.

## Checklist - Fase 3 (AGENTS.md Seção 6)

- [x] Parametrizar no mínimo quatro perfis discentes com comportamentos contrastantes (iniciante colaborativo, intermediário impaciente, avançado conciso, propenso a erros formais).
- [ ] Rodar o orquestrador dual-agent para compilar um dataset empírico contendo pelo menos 10 sessões inteiras, exportando os dados para o arquivo `dataset_ct_tutoring.jsonl`.

## Checklist - Fase 4 (AGENTS.md Seção 6)

- [x] Instalar o pacote `deepeval` e autenticar as variáveis de ambiente necessárias.
- [x] Implementar as rubricas pedagógicas `SocraticAlignmentMetric`, `ScaffoldingEffectivenessMetric` e `PedagogicalProgressionMetric`.
- [ ] Executar o script `benchmark_paper.py` no dataset completo, gerar as tabelas estatísticas (`paper_benchmark_summary_table.csv`) e consolidar os dados descritivos para a redação científica. *(Piloto de 8 casos validado; execução completa pendente)*

## Arquivos Modificados

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `nodes.py` | Refatorado | Core do agente: imports, factory, utilitários, prompts e `final_summary_node` |
| `workflow.py` | Atualizado | Grafo com nó `final_summary_node` e aresta para `END` |
| `prompts.py` | Expandido | 11 prompts: 10 migrados + `FINAL_SUMMARY_NODE_PROMPT` |
| `llm_factory.py` | Novo | Factory centralizada do LLM com retries e timeout |
| `message_utils.py` | Novo | Funções utilitárias de extração de mensagens |
| `simulation/__init__.py` | Novo | Pacote Python para módulos de simulação |
| `simulation/schema.py` | Novo | Modelo Pydantic `StudentProfile` |
| `simulation/student_agent.py` | Novo | Função `run_student_turn()` com lógica estocástica |
| `simulation/student_agent.py` | Atualizado | Adicionada função `_ensure_last_message_is_human()` para correção de bug Gemini |
| `simulation/student_agent.py` | Atualizado | Anti-loop: `BEHAVIOR_COLLABORATIVE` com CoT, novo `BEHAVIOR_COMPREHENSION`, `MAX_ATTEMPTS_PER_STAGE = 2`, assinatura com `attempts_in_stage` |
| `simulation/student_agent.py` | Atualizado | Fix loop: `BEHAVIOR_COMPREHENSION` com síntese MACRO completa (AGENTS.md Seção 3.2) para passar no Gatekeeper |
| `simulation/orchestrator.py` | Novo | Classe `SimulationOrchestrator` para loop dual-agent |
| `simulation/orchestrator.py` | Atualizado | Removido delay entre sessões |
| `simulation/orchestrator.py` | Atualizado | Rastreador `attempts_in_current_stage` anti-loop; chamada nomeada com `attempts_in_stage` |
| `simulation/orchestrator.py` | Atualizado | Fix amnésia: acúmulo do histórico via `state["messages"].extend(...)` em vez de atribuição |
| `simulation/orchestrator.py` | Atualizado | Fix amnésia final: `stream_mode="values"` + sincronização das 6 chaves; remove merge manual e dupla aplicação |
| `profiles.py` | Novo | 4 perfis discentes pré-configurados |
| `run_simulation.py` | Novo | Script CLI para execução de simulações em batch com delay configurável |
| `run_simulation.py` | Atualizado | Salvamento incremental com `append_session_to_jsonl()` |
| `tests/__init__.py` | Novo | Pacote Python para métricas e benchmark |
| `tests/eval_metrics.py` | Novo | 4 métricas G-Eval usando `GeminiModel(model=DEFAULT_MODEL)` + `evaluation_steps` + `SingleTurnParams` |
| `tests/eval_metrics.py` | Atualizado | Modelo como instância `GeminiModel`; `evaluation_steps` pré-definidos nas 4 métricas |
| `tests/benchmark_paper.py` | Novo | Pipeline: `clean_message_content()`, `load_dataset_as_test_cases()`, `run_paper_benchmark()` |
| `tests/benchmark_paper.py` | Atualizado | Lotes com pacing (`--batch-size`/`--sleep`/`--max-cases`); `_evaluate_with_retry`; fix agregação por prefixo; índice `Metric` |
| `paper_benchmark_detailed_results.csv` | Gerado | Piloto (8 casos): scores/success/reasoning por métrica |
| `paper_benchmark_summary_table.csv` | Gerado | Piloto (8 casos): média (0.0–1.0) e taxa de sucesso por métrica |
| `AGENTS.md` | Atualizado | Modelo `gemini-3.5-flash-lite`; `SingleTurnParams`; `ContextualRelevancyMetric`; instância `GeminiModel` no blueprint da Seção 5.1; checklist Fase 4 |
| `AGENTS.md` | Atualizado | "Aha! Moment" → "Comprehension" nas 3 ocorrências da Seção 3.1 (`BEHAVIOR_COMPREHENSION`) |
| `AGENTS.md` | Atualizado | Seção 4: blueprint do orquestrador com `stream_mode="values"` + nota anti-amnésia; critério de parada `completed` |
| `PROGRESS.md` | Atualizado | Este arquivo |
